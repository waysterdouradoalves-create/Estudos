# Braço Robótico 6 Eixos com ESP32 (motores de passo)

Controle via navegador (celular, tablet ou PC) para um braço robótico de
6 graus de liberdade (base giratória, ombro, cotovelo, pulso com 2 eixos
e garra), acionado por **motores de passo** (NEMA17 + driver A4988/DRV8825/
TMC2209) via ESP32. O ESP32 hospeda o site de controle e move os motores
em Wi-Fi, sem precisar de app nem de computador conectado por USB durante
o uso.

```
esp32-robotic-arm/
├── platformio.ini                                # projeto PlatformIO (VSCode)
├── src/main.cpp                                   # firmware do ESP32 (PlatformIO)
├── data/index.html                                # site de controle (servido pelo próprio ESP32)
├── arduino_ide/esp32_robotic_arm/
│   ├── esp32_robotic_arm.ino                      # mesmo firmware, pronto pro Arduino IDE
│   └── data/index.html                            # cópia do site, para o upload de LittleFS do IDE
└── README.md
```

## Como funciona

1. O ESP32 conecta na sua rede Wi-Fi (ou cria um ponto de acesso próprio
   se não conseguir).
2. Ele serve o arquivo `data/index.html` por HTTP e abre um WebSocket em
   `/ws`.
3. A página tem um slider (em **graus**) para cada uma das 6 juntas. Ao
   mover um slider, o navegador manda
   `{"cmd":"move","id":"shoulder","pos":120}` pelo WebSocket; o ESP32
   converte o ângulo em passos (usando a relação de micropasso/redução de
   cada junta) e comanda o motor com aceleração/desaceleração suave via
   `AccelStepper`.
4. A página também desenha um "gêmeo visual" 3D do braço (Three.js/WebGL)
   que se move junto com os sliders — dá pra arrastar para girar a câmera
   e usar o scroll para dar zoom, para conferir a pose antes/durante o
   movimento real.

### Motor de passo x servo: por que tem uma calibração

Diferente de um servo de hobby (que sempre "sabe" seu ângulo pelo próprio
sinal PWM), um motor de passo só sabe **quantos passos deu desde algum
ponto de referência** — ele não tem ideia de onde está fisicamente quando
o ESP32 liga. Por isso o firmware faz, a cada boot, uma rotina de
**calibração**: cada junta gira devagar em direção a um **fim de curso**
(microswitch) até acioná-lo, e a partir daí o ESP32 sabe exatamente onde
está cada eixo. Você também pode disparar essa rotina a qualquer momento
pelo botão **"Calibrar eixos"** na página (por exemplo, se mexeu no braço
manualmente com o motor desenergizado).

Se alguma junta não tiver fim de curso cadastrado (`endstopPin: -1`), o
firmware assume que você posicionou o braço manualmente na posição
"home" **antes de ligar**, e conta os passos a partir daí — sem fim de
curso não há como saber se essa suposição está certa, então prefira
sempre instalar os microswitches.

### Sobre a visualização 3D e internet

A biblioteca 3D (Three.js) é carregada de um CDN (`cdnjs.cloudflare.com`)
diretamente pelo navegador que abre a página — **não** passa pelo ESP32.
Isso funciona sem problema no caso mais comum: ESP32 conectado na sua rede
Wi-Fi normal (modo estação), com o celular/PC na mesma rede e com acesso à
internet. Se o ESP32 cair no modo ponto de acesso próprio (sem roteador
por perto, portanto sem internet), a biblioteca não carrega e a página cai
automaticamente em um modo de texto (lista de ângulos) — os sliders e o
movimento real continuam funcionando normalmente, só a prévia 3D fica
indisponível.

Para eliminar essa dependência (funcionar 100% offline mesmo no modo AP),
baixe estes dois arquivos e salve em `data/lib/`:
- `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`
- `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/examples/js/controls/OrbitControls.js`

E troque as duas tags `<script src="https://cdnjs...">` no topo do
`data/index.html` para apontar para `lib/three.min.js` e
`lib/OrbitControls.js`. Isso aumenta o espaço usado no LittleFS em ~650 KB
— confira se a sua placa/partição comporta antes de gravar.

## Hardware sugerido

| Item | Observação |
|---|---|
| ESP32 DevKit (30 ou 38 pinos) | Qualquer variante com Wi-Fi |
| 6x motor de passo NEMA17 (ou NEMA14/23 nas juntas de mais carga) | Dimensione o torque pelo peso real do seu braço |
| 6x driver A4988, DRV8825 ou TMC2209 | TMC2209 é mais silencioso e permite mais microsteps |
| 6x microswitch (fim de curso) | Um por junta, para a calibração automática |
| Fonte externa dedicada aos drivers (tipicamente 12–24 V, corrente somada dos 6 motores) | **Nunca alimente os motores pelo 5V do ESP32** — confira a corrente de cada driver (potenciômetro/Vref) antes de ligar, senão o motor esquenta |
| Capacitor eletrolítico de alta tensão (ex.: 100 µF/35V+) | Entre + e − da alimentação dos drivers, perto dos módulos |
| Fios/jumpers, terminal de parafuso | Para a fiação de força |

### Ligação dos pinos (padrão do firmware)

| Junta | STEP | DIR | Fim de curso | Faixa sugerida |
|---|---|---|---|---|
| Base (giro) | 13 | 4 | 34 | 0°–180° |
| Ombro | 14 | 16 | 35 | 15°–165° |
| Cotovelo | 27 | 17 | 36 | 0°–180° |
| Pulso (cima/baixo) | 26 | 18 | 39 | 0°–180° |
| Pulso (giro) | 25 | 19 | 32 | 0°–180° |
| Garra | 33 | 21 | 23 | 10°–90° |
| ENABLE (compartilhado entre os 6 drivers) | 22 | — | — | ativo em LOW |

Os pinos 34, 35, 36 e 39 são **somente entrada** e não têm resistor de
pull-up interno — ligue cada fim de curso entre o GPIO e o GND, com um
resistor de pull-up externo de ~10 kΩ do GPIO até 3,3 V (assim ele lê HIGH
em repouso e LOW quando a chave é acionada). Use a mesma lógica nos
demais fins de curso para manter tudo consistente.

Ajuste no array `joints[]` (`src/main.cpp`) para bater com a sua
montagem real:
- `stepPin`/`dirPin`/`endstopPin`: pinos usados.
- `homeDir`: sentido de giro (+1 ou -1) para ir em direção ao fim de curso.
- `homeSwitchAngle`: ângulo que o fim de curso representa fisicamente.
- `motorStepsPerRev`, `microsteps`, `gearRatio`: definem quantos passos
  correspondem a 1 grau daquela junta — **você precisa calibrar isso**
  (veja abaixo).
- `minAngle`/`maxAngle`/`homeAngle`: limites mecânicos e posição de
  descanso.
- `maxSpeedDegPerSec`/`accelDegPerSec2`/`homingSpeedDegPerSec`: velocidade
  de operação normal e velocidade (bem mais lenta) da busca pelo fim de
  curso.

**Como calibrar `gearRatio`:** comande a junta para girar um ângulo
conhecido (ex.: 90°) pela interface, meça o quanto o eixo de saída
realmente girou com um transferidor, e ajuste `gearRatio` proporcionalmente
(`gearRatio_novo = gearRatio_atual × ângulo_comandado / ângulo_real`). Em
juntas com polia/correia, você também pode calcular direto contando os
dentes das duas polias (`gearRatio = dentes_polia_grande / dentes_polia_motor`).

**Fiação de força (importante):**
- A alimentação dos drivers (VMOT) vem de uma fonte externa dedicada — a
  tensão e corrente dependem do motor/driver escolhidos, confira o
  datasheet.
- O `GND` da fonte externa precisa estar ligado ao `GND` do ESP32
  (referência comum).
- **Regule a corrente (Vref) de cada driver antes de conectar o motor.**
  Sem isso o motor pode superaquecer ou perder passos.
- Evite os pinos 0, 2, 5, 6–11, 12 e 15 do ESP32 (usados no boot/flash).

## Firmware (ESP32)

### Opção A — PlatformIO (recomendado)

1. Abra a pasta `esp32-robotic-arm/` no VSCode com a extensão PlatformIO.
2. Edite `src/main.cpp` e preencha `WIFI_SSID`/`WIFI_PASSWORD`, além dos
   pinos/relação de redução de cada junta no array `joints[]`.
3. Grave o firmware: `pio run --target upload`.
4. Envie a interface web para o sistema de arquivos:
   `pio run --target uploadfs`.
5. Abra o Monitor Serial (`pio device monitor`) para acompanhar a
   calibração inicial e ver o IP atribuído.

### Opção B — Arduino IDE

Use a pasta `arduino_ide/esp32_robotic_arm/` — já está no formato que o
Arduino IDE espera (pasta com o mesmo nome do arquivo `.ino`, e uma
subpasta `data/` com o site).

1. **Suporte à placa ESP32**: em `Arquivo > Preferências`, adicione em
   "URLs Adicionais para Gerenciadores de Placas":
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   Depois, em `Ferramentas > Placa > Gerenciador de Placas`, instale
   "esp32 by Espressif Systems".
2. **Bibliotecas**: em `Sketch > Incluir Biblioteca > Gerenciar
   Bibliotecas`, instale:
   - `ESPAsyncWebServer` (procure a versão mantida por ESP32Async/lacamera)
   - `AsyncTCP` (idem, mesma organização)
   - `ArduinoJson` (Benoit Blanchon, versão 7.x)
   - `AccelStepper` (Mike McCauley)
3. **Plugin de upload do LittleFS**: o Arduino IDE não grava a pasta
   `data/` sozinho — precisa de um plugin separado. Procure por "arduino
   littlefs upload" (ou "ESP32 Sketch Data Upload" nas versões mais
   antigas do IDE) e instale a versão compatível com a sua versão do
   Arduino IDE — o nome exato e o processo de instalação mudam entre
   versões do IDE, então confira a documentação atual do plugin escolhido.
4. Abra `arduino_ide/esp32_robotic_arm/esp32_robotic_arm.ino` no Arduino
   IDE (ele carrega a pasta inteira como sketch).
5. Em `Ferramentas`, selecione a placa "ESP32 Dev Module" e um
   **Partition Scheme** com espaço para LittleFS (ex.: "Default 4MB with
   spiffs (1.2MB APP/1.5MB SPIFFS)" — o nome varia conforme a placa/pacote).
6. Preencha `WIFI_SSID`/`WIFI_PASSWORD` e os pinos/relação de redução de
   cada junta no array `joints[]`, no topo do `.ino`.
7. Grave o firmware (`Sketch > Carregar`).
8. Use o plugin de upload do LittleFS para enviar a pasta `data/` deste
   mesmo sketch (não a `data/` da raiz do projeto).
9. Abra o Monitor Serial (115200 baud) para acompanhar a calibração
   inicial e ver o IP atribuído.

> Se você editar `src/main.cpp` (versão PlatformIO) depois, copie as
> mudanças também para `arduino_ide/esp32_robotic_arm/esp32_robotic_arm.ino`
> — são o mesmo firmware, mantidos como dois arquivos por conveniência.
> O mesmo vale para `data/index.html`: mantenha as duas cópias iguais.

## Usando o site

1. Ao ligar, o ESP32 primeiro calibra todas as juntas (busca os fins de
   curso) — acompanhe pelo Monitor Serial na primeira vez para confirmar
   que cada junta gira no sentido certo. Depois disso ele conecta no
   Wi-Fi e sobe o site.
2. Veja o IP no Monitor Serial (ex.: `192.168.0.42`) ou, se caiu no modo
   ponto de acesso, conecte no Wi-Fi **ESP32-BracoRobotico** (senha
   `robotica123`) e acesse `192.168.4.1`.
3. Abra esse endereço no navegador do celular ou PC — a página já
   carrega os sliders e o gêmeo visual 3D do braço.
4. Botões:
   - **Posição inicial (Home)** — leva todas as juntas ao ângulo de
     descanso (`homeAngle`), assumindo que a calibração já rodou.
   - **Calibrar eixos** — refaz a busca pelos fins de curso a qualquer
     momento (pede confirmação, porque o braço se move sozinho).
   - **Velocidade** — escala a velocidade/aceleração de todas as juntas.
   - **Salvar posição / Reproduzir sequência** — grava poses no
     navegador (localStorage) e reproduz em sequência, como uma rotina
     simples de pick-and-place.

## Segurança e boas práticas

- **Regule a corrente de cada driver (Vref) antes de conectar os
  motores** — é a causa nº 1 de motor de passo superaquecendo.
- Instale os 6 fins de curso antes de confiar na calibração automática;
  sem eles, o braço pode ir contra o próprio limite mecânico achando que
  ainda tem curso.
- Ao testar pela primeira vez, solte a garra/carga e deixe o braço se
  mover livremente para conferir se `homeDir`, `minAngle`/`maxAngle` e
  `gearRatio` de cada junta estão corretos.
- Comece com velocidade baixa (2–4) até confirmar a calibração e os
  limites mecânicos.
- Sempre ligue a fonte dos drivers por último e desligue primeiro.

## Próximos passos (ideias de evolução)

- Cinemática inversa (mover por coordenadas X/Y/Z em vez de ângulo por
  ângulo).
- Controle por joystick/gamepad via WebSocket.
- Autenticação simples na página para uso fora da rede local.
- Detecção de perda de passo (stall) com drivers TMC2209 em modo
  StallGuard, para recalibrar sozinho se travar.
