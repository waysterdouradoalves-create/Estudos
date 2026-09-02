# Braço Robótico 6 Eixos com ESP32

Controle via navegador (celular, tablet ou PC) para um braço robótico de
6 graus de liberdade no estilo "desktop cobot" (base giratória, ombro,
cotovelo, pulso com 2 eixos e garra) como o da foto de referência. O ESP32
hospeda o site de controle e move os servos em Wi-Fi, sem precisar de app
nem de computador conectado por USB durante o uso.

```
esp32-robotic-arm/
├── platformio.ini      # projeto PlatformIO (VSCode)
├── src/main.cpp        # firmware do ESP32
├── data/index.html     # site de controle (servido pelo próprio ESP32)
└── README.md
```

## Como funciona

1. O ESP32 conecta na sua rede Wi-Fi (ou cria um ponto de acesso próprio
   se não conseguir).
2. Ele serve o arquivo `data/index.html` por HTTP e abre um WebSocket em
   `/ws`.
3. A página tem um slider para cada uma das 6 juntas. Ao mover um slider,
   o navegador manda `{"cmd":"move","id":"shoulder","pos":120}` pelo
   WebSocket; o ESP32 aplica a rampa de movimento e escreve no servo.
4. A página também desenha um "gêmeo visual" do braço (SVG) que se move
   junto com os sliders, para você conferir a pose antes/durante o
   movimento real.

## Hardware sugerido

| Item | Observação |
|---|---|
| ESP32 DevKit (30 ou 38 pinos) | Qualquer variante com Wi-Fi |
| 6x servo padrão (ex.: MG996R/DS3218 nas juntas base/ombro/cotovelo, SG90/MG90S no pulso/garra) | Dimensione o torque pelo peso real do seu braço |
| Fonte externa 5–6 V, 5 A ou mais | **Não alimente os servos pelo pino 5V do ESP32** |
| Capacitor eletrolítico 470–1000 µF | Entre + e − da fonte dos servos, reduz picos de corrente |
| Fios/jumpers, terminal de parafuso | Para a fiação de força |

### Ligação dos pinos (padrão do firmware)

| Junta | Pino GPIO | Faixa de segurança sugerida |
|---|---|---|
| Base (giro) | 13 | 0°–180° |
| Ombro | 14 | 15°–165° |
| Cotovelo | 27 | 0°–180° |
| Pulso (cima/baixo) | 26 | 0°–180° |
| Pulso (giro) | 25 | 0°–180° |
| Garra | 33 | 10°–90° |

Ajuste os pinos e os limites de ângulo (`minAngle`/`maxAngle`/`homeAngle`)
em `src/main.cpp`, no array `joints[]`, para bater com a montagem mecânica
real — os limites evitam que um servo force contra o batente e queime.

**Fiação de força (importante):**
- Uma fonte externa de 5–6 V alimenta os `+`/`−` de todos os servos.
- O `GND` da fonte externa precisa estar ligado ao `GND` do ESP32
  (referência comum) — sem isso o sinal PWM não funciona direito.
- O sinal de cada servo vai direto no GPIO correspondente da tabela acima.
- Evite os pinos 0, 2, 5, 6–11, 12 e 15 do ESP32 (usados no boot/flash).

## Firmware (ESP32)

### Opção A — PlatformIO (recomendado)

1. Abra a pasta `esp32-robotic-arm/` no VSCode com a extensão PlatformIO.
2. Edite `src/main.cpp` e preencha `WIFI_SSID`/`WIFI_PASSWORD`.
3. Grave o firmware: `pio run --target upload`.
4. Envie a interface web para o sistema de arquivos:
   `pio run --target uploadfs`.
5. Abra o Monitor Serial (`pio device monitor`) para ver o IP atribuído.

### Opção B — Arduino IDE

1. Instale o suporte a placas ESP32 (Board Manager) e, no Library
   Manager, instale: `ESPAsyncWebServer`, `AsyncTCP`, `ArduinoJson`
   (v7+) e `ESP32Servo`.
2. Instale o plugin "ESP32 Sketch Data Upload" para gravar a pasta
   `data/` no LittleFS.
3. Abra `src/main.cpp` como um sketch (renomeie a pasta para
   `esp32_robotic_arm/esp32_robotic_arm.ino` se preferir a extensão
   `.ino`), preencha o Wi-Fi, grave o firmware e depois use
   "ESP32 Sketch Data Upload" para enviar `data/index.html`.

## Usando o site

1. Depois de gravar, veja o IP no Monitor Serial (ex.: `192.168.0.42`)
   ou, se caiu no modo ponto de acesso, conecte no Wi-Fi
   **ESP32-BracoRobotico** (senha `robotica123`) e acesse `192.168.4.1`.
2. Abra esse endereço no navegador do celular ou PC — a página já
   carrega os sliders e o desenho do braço.
3. Botões:
   - **Home** — leva todas as juntas para a posição inicial.
   - **Velocidade** — controla o quão rápido o braço reage ao slider
     (rampa suave, evita puxar corrente demais de uma vez).
   - **Salvar posição / Reproduzir sequência** — grava poses no
     navegador (localStorage) e reproduz em sequência, como uma rotina
     simples de pick-and-place.

## Segurança e boas práticas

- Sempre ligue a fonte dos servos por último e desligue primeiro,
  segurando o braço se ele não estiver na posição "home".
- Ajuste `minAngle`/`maxAngle` de cada junta assim que montar o braço,
  testando movimento livre antes de prender a garra/carga.
- Comece com `moveSpeed` baixo (1–3) até garantir que os limites
  mecânicos e a fonte de alimentação estão corretos.

## Próximos passos (ideias de evolução)

- Cinemática inversa (mover por coordenadas X/Y/Z em vez de ângulo por
  ângulo).
- Controle por joystick/gamepad via WebSocket.
- Autenticação simples na página para uso fora da rede local.
