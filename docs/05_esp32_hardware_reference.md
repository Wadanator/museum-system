# ESP32 Hardware & Pin Reference

Tento dokument je kritický pre AI a vývojárov, pretože obsahuje presné hardvérové mapovanie (piny, PWM frekvencie atď.) pre všetky ESP32 moduly zapojené v systéme. Konfiguračné súbory sú rozdelené medzi `esp32/devices/wifi/ArduinoIDE/` a `esp32/devices/wifi/EspHome/`.

---

## 1. ESP32 Motors (`esp32_mqtt_controller_MOTORS`)
Riadi 2 jednosmerné (DC) motory. 
Modul používa hardvérové PWM so smooth nábehom (postupné zvyšovanie/znižovanie rýchlosti).

MQTT správanie:

- subscribe: `room1/motor1`, `room1/motor2`, `room1/STOP`
- feedback: `room1/motor1/feedback`, `room1/motor2/feedback`
- status: `devices/Room1_ESP_Motory/status`
- payloady: `ON:<speed>:<direction>[:<rampTime>]`, `OFF`, `SPEED:<value>`, `DIR:<value>`
- `room1/STOP` vykoná okamžité vypnutie motorov
- signalizácia: v aktuálnom motornom firmvéri nie je samostatná status LED

- **PWM Nastavenia:**
  - `PWM_FREQUENCY = 20000` (20 kHz)
  - `PWM_RESOLUTION = 8` (0-255)
  - `SMOOTH_STEP = 2`
  - `SMOOTH_DELAY = 100` (ms)

- **Prevádzkové parametre:**
  - `CLIENT_ID = Room1_ESP_Motory`
  - `STATUS_PUBLISH_INTERVAL = 15000` (ms)
  - `WDT_TIMEOUT = 60` (s)
  - `OTA_HOSTNAME = ESP32-Museum-Room1`

- **Mapovanie pinov (výkonový H-mostík BTS7960B):**
  - **MOTOR1 (BTS7960B):**
    - `MOTOR1_LEFT_PIN = 18`
    - `MOTOR1_RIGHT_PIN = 19`
    - `MOTOR1_ENABLE_PIN = 21`
  - **MOTOR2 (BTS7960B):**
    - `MOTOR2_LEFT_PIN = 27`
    - `MOTOR2_RIGHT_PIN = 26`
    - `MOTOR2_ENABLE_PIN = 25`

---

## 2. ESP32 Relays (`esp32_mqtt_controller_RELAY`)
Ovláda relé modul a voliteľné doplnky (napr. vizuálna stavová kontrolka - RGB LED, aj keď aktuálne kód mapuje len jeden pin `RGB_LED_PIN`).
Podporuje priame GPIO alebo I2C Expander (napr. PCF8574).

MQTT správanie:

- subscribe: `room1/<device_name>`, `room1/effects/#`, `room1/STOP`
- feedback: `<command_topic>/feedback`
- status: `devices/Room1_Relays_Ctrl/status`
- device payloady: `ON`, `OFF`, `1`, `0`
- effects payloady: `ON`, `OFF`, `START`, `STOP`, `1`, `0`
- `room1/STOP` vypne zariadenia aj efekty

- **I2C Konfigurácia (ak `USE_RELAY_MODULE = true`):**
  - `I2C_SDA_PIN = 42`
  - `I2C_SCL_PIN = 41`
  - `I2C_EXPANDER_ADDR = 0x20`

- **Ostatné Piny:**
  - `RGB_LED_PIN = 38` (Využívané na vizualizáciu MQTT/WiFi stavu)

- **Prevádzkové parametre:**
  - `USE_RELAY_MODULE = true` (aktuálne zapnutý I2C režim)
  - `CLIENT_ID = Room1_Relays_Ctrl`
  - `STATUS_PUBLISH_INTERVAL = 15000` (ms)
  - `NO_COMMAND_TIMEOUT = 180000` (ms)
  - `WDT_TIMEOUT = 30` (s)
  - `OTA_HOSTNAME = ESP32-RelayModule-Room1`

- **Status LED signalizácia:**
  - ArduinoIDE (`status_led.cpp`, GPIO38 / NeoPixel): pri štarte krátke modré bliknutie, bez WiFi rýchle červené blikanie, WiFi OK ale MQTT offline oranžové blikanie, všetko OK zelené breathing svietenie, počas OTA tyrkysová/modrá signalizácia
  - ESPHome (`esp32_mqtt_controller_RELAY_v2.yaml`, GPIO38 / NeoPixel): červená pre WiFi fail, oranžová pre MQTT fail, zelená pre all OK breathing, OTA prepne LED na modrú/tyrkysovú

- **Namapované Zariadenia (`DEVICES[]` indexy):**
  - Bit 0: `power/smoke_ON`
  - Bit 1: `light/fire`
  - Bit 2: `light/1`
  - Bit 3: `effect/smoke` (Auto-off po 12000 ms)
  - Bit 4: `light/2`
  - Bit 5: `light/3`
  - Bit 6: `light/4`
  - Bit 7: `light/5`

---

## 3. ESP32 Button (`esp32_mqtt_button`)
Slúži ako trigger modul pre fyzické tlačidlá umiestnené v miestnosti. Existuje vo verzii pre Arduino IDE aj ESPHome.

MQTT správanie:

- publish trigger: `room1/scene` s payloadom `START`
- status: `devices/Room1_ESP_Trigger/status`
- interval heartbeat: 15s

- **Mapovanie Pinov:**
  - `BUTTON_PIN = 32` (Zabezpečuje zachytávanie hardvérového tlačidla. Oproti slabým interným odporom využíva **externý pull-up rezistor** pre vyššiu spoľahlivosť a odolnosť voči rušeniu, LOW = stlačené)

- **Debounce & Cooldown:**
  - `DEBOUNCE_DELAY` = 60 ms (Arduino) alebo 100 ms (ESPHome)
  - `BUTTON_COOLDOWN = 4000` (ms) (Zabraňuje viacnásobnému poslaniu `START` signálu za sebou počas 4 sekúnd)

- **Prevádzkové parametre:**
  - `CLIENT_ID = Room1_ESP_Trigger`
  - `STATUS_PUBLISH_INTERVAL = 15000` (ms)
  - `WDT_TIMEOUT = 30` (s)
  - `OTA_HOSTNAME = ESP32-Room1-Trigger`

- **ESPHome LED varianta (`esp32_mqtt_button_led.yaml`):**
  - toto je samostatná ESPHome verzia, nie ArduinoIDE button firmware
  - LED výstup: `GPIO25`
  - `led_mode = 0`: WiFi fail, pulzovanie
  - `led_mode = 1`: MQTT fail, dvojité blikanie
  - `led_mode = 2`: všetko OK, steady ON
  - `led_mode = 3`: potvrdenie stlačenia, trojité bliknutie
  - po úspešnom stlačení sa pošle `room1/scene` = `START` a LED sa vráti do stavu podľa WiFi/MQTT

---
