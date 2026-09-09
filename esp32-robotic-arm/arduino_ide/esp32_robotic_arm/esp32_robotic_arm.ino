// ============================================================================
// Controle de Braço Robótico 6 Eixos com ESP32 — versão MOTORES DE PASSO
// (sketch para Arduino IDE — veja o README na raiz do projeto)
//
// Este arquivo é uma cópia de src/main.cpp (projeto PlatformIO) pronta para
// abrir direto no Arduino IDE. Se editar a lógica de um lado, replique no
// outro para não desalinhar as duas versões.
//
// Cada junta é acionada por um motor de passo (NEMA17 ou similar) através de
// um driver externo (A4988, DRV8825 ou TMC2209) via sinais STEP/DIR. Isso é
// bem diferente de servo de hobby: o motor de passo não sabe sozinho "em que
// ângulo está" — por isso o firmware faz uma rotina de CALIBRAÇÃO (home via
// fim de curso/endstop) sempre que liga, e a partir daí conta passos.
//
// O ESP32 cria um servidor web + WebSocket e serve a interface de controle
// (pasta data/ deste sketch) pelo LittleFS. O protocolo com o navegador
// continua em GRAUS — a conversão grau <-> passo acontece toda aqui dentro,
// usando a relação de redução/micropasso de cada junta.
//
// Bibliotecas necessárias (Arduino IDE > Sketch > Incluir biblioteca >
// Gerenciar bibliotecas):
//   - ESPAsyncWebServer (por lacamera / ESP32Async)
//   - AsyncTCP (por dvarrel / ESP32Async)
//   - ArduinoJson (v7+, por Benoit Blanchon)
//   - AccelStepper (por Mike McCauley)
// ============================================================================

#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <AccelStepper.h>

// ---------------------------------------------------------------------------
// Configuração de rede
// ---------------------------------------------------------------------------
const char *WIFI_SSID = "SUA_REDE_WIFI";
const char *WIFI_PASSWORD = "SUA_SENHA_WIFI";

const char *AP_SSID = "ESP32-BracoRobotico";
const char *AP_PASSWORD = "robotica123"; // mínimo 8 caracteres

// Pino de ENABLE compartilhado entre todos os drivers (ative LOW é o padrão
// em A4988/DRV8825/TMC2209 — LOW energiza os motores).
const int ENABLE_PIN = 22;
const bool ENABLE_ACTIVE_LOW = true;

// ---------------------------------------------------------------------------
// Configuração das juntas — AJUSTE TUDO AQUI para bater com a sua mecânica
// ---------------------------------------------------------------------------
struct JointConfig {
  const char *id;
  const char *label;

  uint8_t stepPin;
  uint8_t dirPin;
  bool invertDir;

  int endstopPin;          // -1 = sem fim de curso (assume que já liga em homeAngle)
  int homeDir;             // +1 ou -1: sentido de giro para ir em direção ao fim de curso
  float homeSwitchAngle;   // ângulo (graus) que o fim de curso representa

  float motorStepsPerRev;  // 200 = motor de 1.8°, 400 = motor de 0.9°
  int microsteps;          // conforme os jumpers/config do driver (1,2,4,8,16,32...)
  float gearRatio;         // redução mecânica (polia/engrenagem). 1.0 = acoplado direto

  float minAngle, maxAngle, homeAngle;
  float maxSpeedDegPerSec;
  float accelDegPerSec2;
  float homingSpeedDegPerSec;
};

// Pinos pensados para não usar os pinos de boot/flash do ESP32
// (evita 0, 2, 5, 6-11, 12, 15). Ajuste conforme sua fiação real.
JointConfig joints[] = {
    // id           label                  STEP DIR  inv  endst homeDir switchAngle  steps/rev  µstep gear   min   max   home  velMax accel  velHome
    {"base",        "Base (giro)",           13,   4, false,  34,   -1,      0,          200,     16,  5.18,    0,  180,   90,   60,   90,     15},
    {"shoulder",    "Ombro",                 14,  16, false,  35,   -1,     15,          200,     16,  5.18,   15,  165,   90,   50,   80,     15},
    {"elbow",       "Cotovelo",              27,  17, false,  36,   -1,      0,          200,     16,  5.18,    0,  180,   90,   60,   90,     15},
    {"wristPitch",  "Pulso (cima/baixo)",    26,  18, false,  39,   -1,      0,          200,     16,  1.00,    0,  180,   90,   90,  140,     20},
    {"wristRoll",   "Pulso (giro)",          25,  19, false,  32,   -1,      0,          200,     16,  1.00,    0,  180,   90,   90,  140,     20},
    {"gripper",     "Garra",                 33,  21, false,  23,   -1,     10,          200,     16,  1.00,   10,   90,   10,   60,  100,     15},
};

const int NUM_JOINTS = sizeof(joints) / sizeof(joints[0]);

AccelStepper *steppers[NUM_JOINTS];
float stepsPerDegree[NUM_JOINTS];

// Velocidade global (1-10) aplicada como fração da velocidade máxima de
// cada junta — permite deixar tudo mais lento/suave direto pela interface.
int moveSpeed = 6;

bool calibrating = false;
volatile bool calibrationRequested = false;

AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

unsigned long lastBroadcast = 0;
const unsigned long BROADCAST_INTERVAL_MS = 60;

// ---------------------------------------------------------------------------
// Conversão grau <-> passo
// ---------------------------------------------------------------------------
long angleToSteps(int i, float angle) {
  return lround((angle - joints[i].homeAngle) * stepsPerDegree[i]);
}

float stepsToAngle(int i, long steps) {
  return joints[i].homeAngle + (float)steps / stepsPerDegree[i];
}

int findJointIndex(const char *id) {
  for (int i = 0; i < NUM_JOINTS; i++) {
    if (strcmp(joints[i].id, id) == 0) return i;
  }
  return -1;
}

// ---------------------------------------------------------------------------
// Estado / WebSocket
// ---------------------------------------------------------------------------
void broadcastState() {
  JsonDocument doc;
  doc["type"] = "state";
  doc["speed"] = moveSpeed;
  doc["calibrating"] = calibrating;
  JsonArray arr = doc["angles"].to<JsonArray>();
  for (int i = 0; i < NUM_JOINTS; i++) {
    JsonObject o = arr.add<JsonObject>();
    o["id"] = joints[i].id;
    o["angle"] = stepsToAngle(i, steppers[i]->currentPosition());
  }
  String out;
  serializeJson(doc, out);
  ws.textAll(out);
}

void applySpeed() {
  float frac = constrain(moveSpeed, 1, 10) / 10.0f;
  for (int i = 0; i < NUM_JOINTS; i++) {
    steppers[i]->setMaxSpeed(joints[i].maxSpeedDegPerSec * stepsPerDegree[i] * frac);
    steppers[i]->setAcceleration(joints[i].accelDegPerSec2 * stepsPerDegree[i] * frac);
  }
}

void setJointTarget(int index, float angle) {
  if (index < 0 || index >= NUM_JOINTS) return;
  angle = constrain(angle, joints[index].minAngle, joints[index].maxAngle);
  steppers[index]->moveTo(angleToSteps(index, angle));
}

void goHome() {
  for (int i = 0; i < NUM_JOINTS; i++) steppers[i]->moveTo(0); // 0 passos == homeAngle
}

// ---------------------------------------------------------------------------
// Calibração (home físico via fim de curso)
//
// Roda uma vez no boot e sempre que o comando {"cmd":"calibrate"} chega.
// É bloqueante de propósito (dura poucos segundos, uma junta de cada vez) —
// simples e previsível, às custas de travar o WebSocket durante a rotina.
// ---------------------------------------------------------------------------
void homeJoint(int i) {
  JointConfig &j = joints[i];

  if (j.endstopPin < 0) {
    // Sem fim de curso: assume que a junta já foi posicionada manualmente
    // em homeAngle antes de ligar o ESP32.
    steppers[i]->setCurrentPosition(0);
    return;
  }

  pinMode(j.endstopPin, INPUT_PULLUP);
  float homingSpeedSteps = j.homingSpeedDegPerSec * stepsPerDegree[i];

  // fase 1: aproxima do fim de curso (chave aberta = HIGH, com pull-up)
  steppers[i]->setSpeed(j.homeDir * homingSpeedSteps);
  while (digitalRead(j.endstopPin) == HIGH) {
    steppers[i]->runSpeed();
  }

  // fase 2: recua devagar até soltar a chave, para repetibilidade
  steppers[i]->setSpeed(-j.homeDir * (homingSpeedSteps / 3.0f));
  while (digitalRead(j.endstopPin) == LOW) {
    steppers[i]->runSpeed();
  }

  long stepsAtSwitch = lround((j.homeSwitchAngle - j.homeAngle) * stepsPerDegree[i]);
  steppers[i]->setCurrentPosition(stepsAtSwitch);

  // volta para a posição de descanso (homeAngle == 0 passos)
  steppers[i]->moveTo(0);
  while (steppers[i]->distanceToGo() != 0) {
    steppers[i]->run();
  }
}

void runCalibration() {
  calibrating = true;
  broadcastState();
  for (int i = 0; i < NUM_JOINTS; i++) {
    homeJoint(i);
  }
  calibrating = false;
  broadcastState();
}

// ---------------------------------------------------------------------------
// WebSocket: recebe comandos da interface web
// ---------------------------------------------------------------------------
// Protocolo (JSON) — igual ao da versão servo, a interface web não precisa mudar:
//   {"cmd":"move",      "id":"base", "pos":90}
//   {"cmd":"home"}
//   {"cmd":"calibrate"}
//   {"cmd":"speed",     "value":6}
void handleWsMessage(uint8_t *data, size_t len) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, data, len);
  if (err) return;

  const char *cmd = doc["cmd"] | "";

  if (calibrating) return; // ignora comandos de movimento durante a calibração

  if (strcmp(cmd, "move") == 0) {
    const char *id = doc["id"] | "";
    float pos = doc["pos"] | -1000.0f;
    int idx = findJointIndex(id);
    if (idx >= 0 && pos > -999.0f) setJointTarget(idx, pos);
  } else if (strcmp(cmd, "home") == 0) {
    goHome();
  } else if (strcmp(cmd, "calibrate") == 0) {
    calibrationRequested = true;
  } else if (strcmp(cmd, "speed") == 0) {
    moveSpeed = constrain((int)(doc["value"] | 6), 1, 10);
    applySpeed();
  }
}

void onWsEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
               AwsEventType type, void *arg, uint8_t *data, size_t len) {
  if (type == WS_EVT_CONNECT) {
    broadcastState();
  } else if (type == WS_EVT_DATA) {
    handleWsMessage(data, len);
  }
}

// ---------------------------------------------------------------------------
// Wi-Fi
// ---------------------------------------------------------------------------
void setupWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Conectando ao WiFi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(300);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("Conectado! Acesse: http://");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("Nao foi possivel conectar. Criando ponto de acesso...");
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASSWORD);
    Serial.print("Conecte-se a rede '");
    Serial.print(AP_SSID);
    Serial.print("' e acesse: http://");
    Serial.println(WiFi.softAPIP());
  }
}

// ---------------------------------------------------------------------------
// Setup / Loop
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);

  if (!LittleFS.begin(true)) {
    Serial.println("Erro ao montar LittleFS (envie a pasta data/ com uploadfs)");
  }

  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, ENABLE_ACTIVE_LOW ? LOW : HIGH); // energiza os drivers

  for (int i = 0; i < NUM_JOINTS; i++) {
    stepsPerDegree[i] = (joints[i].motorStepsPerRev * joints[i].microsteps * joints[i].gearRatio) / 360.0f;

    steppers[i] = new AccelStepper(AccelStepper::DRIVER, joints[i].stepPin, joints[i].dirPin);
    steppers[i]->setPinsInverted(joints[i].invertDir, false, false);
    steppers[i]->setCurrentPosition(0);
  }
  applySpeed();

  Serial.println("Calibrando juntas (buscando fins de curso)...");
  runCalibration();
  Serial.println("Calibracao concluida.");

  setupWifi();

  ws.onEvent(onWsEvent);
  server.addHandler(&ws);

  server.serveStatic("/", LittleFS, "/").setDefaultFile("index.html");

  server.on("/api/state", HTTP_GET, [](AsyncWebServerRequest *request) {
    JsonDocument doc;
    JsonArray arr = doc["angles"].to<JsonArray>();
    for (int i = 0; i < NUM_JOINTS; i++) {
      JsonObject o = arr.add<JsonObject>();
      o["id"] = joints[i].id;
      o["label"] = joints[i].label;
      o["min"] = joints[i].minAngle;
      o["max"] = joints[i].maxAngle;
      o["angle"] = stepsToAngle(i, steppers[i]->currentPosition());
    }
    String out;
    serializeJson(doc, out);
    request->send(200, "application/json", out);
  });

  server.begin();
}

void loop() {
  ws.cleanupClients();

  if (calibrationRequested) {
    calibrationRequested = false;
    Serial.println("Recalibrando por comando da interface...");
    runCalibration();
  }

  bool anyMoving = false;
  for (int i = 0; i < NUM_JOINTS; i++) {
    if (steppers[i]->run()) anyMoving = true;
  }

  unsigned long now = millis();
  if (anyMoving && now - lastBroadcast >= BROADCAST_INTERVAL_MS) {
    lastBroadcast = now;
    broadcastState();
  }
}
