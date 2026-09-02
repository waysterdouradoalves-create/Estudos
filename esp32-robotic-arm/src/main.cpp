// ============================================================================
// Controle de Braço Robótico 6 Eixos com ESP32
//
// O ESP32 cria um servidor web + WebSocket e serve a interface de controle
// (pasta data/) diretamente do sistema de arquivos LittleFS. O navegador
// (celular, tablet ou PC) se conecta ao ESP32 pela rede Wi-Fi e envia os
// ângulos de cada junta em tempo real via WebSocket.
//
// Bibliotecas necessárias (Arduino Library Manager ou platformio.ini):
//   - ESPAsyncWebServer
//   - AsyncTCP
//   - ArduinoJson (v7)
//   - ESP32Servo
// ============================================================================

#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>

// ---------------------------------------------------------------------------
// Configuração de rede
// ---------------------------------------------------------------------------
// Preencha com os dados da sua rede Wi-Fi. Se a conexão falhar em 10s,
// o ESP32 sobe um ponto de acesso próprio (modo AP) para você controlar o
// braço mesmo sem roteador por perto.
const char *WIFI_SSID = "SUA_REDE_WIFI";
const char *WIFI_PASSWORD = "SUA_SENHA_WIFI";

const char *AP_SSID = "ESP32-BracoRobotico";
const char *AP_PASSWORD = "robotica123"; // mínimo 8 caracteres

// ---------------------------------------------------------------------------
// Configuração das juntas (ajuste os pinos e limites conforme sua montagem)
// ---------------------------------------------------------------------------
struct JointConfig {
  const char *id;     // identificador usado pela interface web
  const char *label;  // nome amigável (exibido na UI)
  uint8_t pin;         // pino GPIO ligado ao sinal do servo
  int minAngle;        // limite mecânico mínimo (graus)
  int maxAngle;        // limite mecânico máximo (graus)
  int homeAngle;        // posição de "descanso"/inicial
};

// Pinos escolhidos por serem saídas seguras no ESP32 DevKit (evitam pinos de
// boot/flash: 0, 2, 5, 6-11, 12, 15). Ajuste se sua pinagem for diferente.
JointConfig joints[] = {
    {"base",     "Base (giro)",       13, 0,   180, 90},
    {"shoulder", "Ombro",             14, 15,  165, 90},
    {"elbow",    "Cotovelo",          27, 0,   180, 90},
    {"wristPitch","Pulso (cima/baixo)",26, 0,   180, 90},
    {"wristRoll","Pulso (giro)",      25, 0,   180, 90},
    {"gripper",  "Garra",             33, 10,  90,  10},
};

const int NUM_JOINTS = sizeof(joints) / sizeof(joints[0]);

Servo servoMotors[NUM_JOINTS];
float currentAngle[NUM_JOINTS];
float targetAngle[NUM_JOINTS];

// Velocidade do movimento: graus adicionados a cada passo de rampa.
// 1 = bem suave/lento, 10 = resposta quase imediata.
int moveSpeed = 3;

AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

unsigned long lastRampUpdate = 0;
const unsigned long RAMP_INTERVAL_MS = 15; // ~66 atualizações/segundo

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------
int findJointIndex(const char *id) {
  for (int i = 0; i < NUM_JOINTS; i++) {
    if (strcmp(joints[i].id, id) == 0) return i;
  }
  return -1;
}

void broadcastState() {
  JsonDocument doc;
  doc["type"] = "state";
  doc["speed"] = moveSpeed;
  JsonArray arr = doc["angles"].to<JsonArray>();
  for (int i = 0; i < NUM_JOINTS; i++) {
    JsonObject o = arr.add<JsonObject>();
    o["id"] = joints[i].id;
    o["angle"] = (int)round(currentAngle[i]);
  }
  String out;
  serializeJson(doc, out);
  ws.textAll(out);
}

void setJointTarget(int index, int angle) {
  if (index < 0 || index >= NUM_JOINTS) return;
  angle = constrain(angle, joints[index].minAngle, joints[index].maxAngle);
  targetAngle[index] = angle;
}

void goHome() {
  for (int i = 0; i < NUM_JOINTS; i++) setJointTarget(i, joints[i].homeAngle);
}

// ---------------------------------------------------------------------------
// WebSocket: recebe comandos da interface web
// ---------------------------------------------------------------------------
// Protocolo (JSON):
//   {"cmd":"move",  "id":"base", "pos":90}
//   {"cmd":"home"}
//   {"cmd":"speed", "value":5}
void handleWsMessage(uint8_t *data, size_t len) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, data, len);
  if (err) return;

  const char *cmd = doc["cmd"] | "";

  if (strcmp(cmd, "move") == 0) {
    const char *id = doc["id"] | "";
    int pos = doc["pos"] | -1;
    int idx = findJointIndex(id);
    if (idx >= 0 && pos >= 0) setJointTarget(idx, pos);
  } else if (strcmp(cmd, "home") == 0) {
    goHome();
  } else if (strcmp(cmd, "speed") == 0) {
    moveSpeed = constrain((int)(doc["value"] | 3), 1, 10);
  }
}

void onWsEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
               AwsEventType type, void *arg, uint8_t *data, size_t len) {
  if (type == WS_EVT_CONNECT) {
    broadcastState(); // envia o estado atual assim que alguém conecta
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

  // Aloca os timers do LEDC entre os 6 servos automaticamente.
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  for (int i = 0; i < NUM_JOINTS; i++) {
    servoMotors[i].setPeriodHertz(50);
    servoMotors[i].attach(joints[i].pin, 500, 2400);
    currentAngle[i] = joints[i].homeAngle;
    targetAngle[i] = joints[i].homeAngle;
    servoMotors[i].write((int)currentAngle[i]);
  }

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
      o["angle"] = (int)round(currentAngle[i]);
    }
    String out;
    serializeJson(doc, out);
    request->send(200, "application/json", out);
  });

  server.begin();
}

void loop() {
  ws.cleanupClients();

  unsigned long now = millis();
  if (now - lastRampUpdate >= RAMP_INTERVAL_MS) {
    lastRampUpdate = now;
    bool changed = false;
    for (int i = 0; i < NUM_JOINTS; i++) {
      float diff = targetAngle[i] - currentAngle[i];
      if (fabs(diff) > 0.5f) {
        float step = (float)moveSpeed * (diff > 0 ? 1.0f : -1.0f);
        if (fabs(step) > fabs(diff)) step = diff;
        currentAngle[i] += step;
        servoMotors[i].write((int)round(currentAngle[i]));
        changed = true;
      }
    }
    if (changed) broadcastState();
  }
}
