# ESP32 Hardware & Pin Reference

Tento dokument je kritický pre AI a vývojárov, pretože obsahuje presné hardvérové mapovanie (piny, PWM frekvencie atď.) pre všetky ESP32 moduly zapojené v systéme. Všetky konfiguračné súbory sa nachádzajú v `esp32/devices/wifi/ArduinoIDE/`.

---

## 1. ESP32 Motors (`esp32_mqtt_controller_MOTORS`)
Riadi 2 jednosmerné (DC) motory. 
Modul používa hardvérové PWM so smooth nábehom (postupné zvyšovanie/znižovanie rýchlosti).

- **PWM Nastavenia:**
  - `PWM_FREQUENCY = 20000` (20 kHz)
  - `PWM_RESOLUTION = 8` (0-255)
  - `SMOOTH_STEP = 2`
  - `SMOOTH_DELAY = 100` (ms)

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

- **I2C Konfigurácia (ak `USE_RELAY_MODULE = true`):**
  - `I2C_SDA_PIN = 42`
  - `I2C_SCL_PIN = 41`
  - `I2C_EXPANDER_ADDR = 0x20`

- **Ostatné Piny:**
  - `RGB_LED_PIN = 38` (Využívané na vizualizáciu MQTT/WiFi stavu)

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

- **Mapovanie Pinov:**
  - `BUTTON_PIN = 32` (Zabezpečuje zachytávanie hardvérového tlačidla. Oproti slabým interným odporom využíva **externý pull-up rezistor** pre vyššiu spoľahlivosť a odolnosť voči rušeniu, LOW = stlačené)
  - `STATUS_LED_PIN = 25` (Voliteľný výstup vyhradený pre verziu `esp32_mqtt_button_led.yaml` v ESPHome)

- **Debounce & Cooldown:**
  - `DEBOUNCE_DELAY` = 60 ms (Arduino) alebo 100 ms (ESPHome)
  - `BUTTON_COOLDOWN = 4000` (ms) (Zabraňuje viacnásobnému poslaniu `START` signálu za sebou počas 4 sekúnd)

- **Vizuálna odozva (ESPHome verzia s LED):**
  - **Trvalé svietenie:** Všetko OK (WiFi aj MQTT pripojené).
  - **Pulzovanie:** Čakanie/Výpadok WiFi spojenia.
  - **Dvojité blikanie:** WiFi pripojené, ale výpadok MQTT.
  - **Rýchle trojité bliknutie:** Úspešné odobratie a odoslanie stlačenia.

---
*Tip pre AI bota: Ak programujete novú funkciu pre konkrétny ESP32 modul, vždy overte existujúce piny primárne podľa tohto dokumentu alebo podľa súborov `config.cpp` v samotnom firmvéri.*
