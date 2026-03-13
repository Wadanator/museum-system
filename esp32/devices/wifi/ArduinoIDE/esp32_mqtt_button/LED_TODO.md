# LED Indikátor – TODO & Zapojenie

## Čo chcem dosiahnuť

Tlačidlo má vstavanú LED (3–6V). Chcem vizuálnu spätnú väzbu:

| Stav systému | LED správanie |
|---|---|
| WiFi + MQTT OK | Trvalo svieti |
| WiFi alebo MQTT FAIL | Pomalé pulzovanie (~1s cyklus) |
| Tlačidlo stlačené (trigger odoslaný) | 2x rýchle bliknutie |

---

## Hardvér – zapojenie

### Čo mám
- LED vstavaná v tlačidle, napájanie 3–6V, má vlastný odpor
- PWM malý riadiaci obvod
- ESP32 DEVKIT V1

### Ako zapojiť

```
ESP32 GPIO (napr. IO25)
        │
        ▼
  PWM obvod (IN)
        │
        ▼ (5V výstup)
  LED v tlačidle (vstavaná, má vlastný R)
        │
        ▼
       GND
```

**Napájanie PWM obvodu:** 5V z tej istej linky ako ESP32 (KF301 DC_5V_IN)

**Prečo PWM obvod a nie priamo 3V3:**
- 3V3 pin DEVKITu má limitovaný prúd (~40mA zdieľaný)
- LED je 3–6V → na 5V cez PWM obvod je to spoľahlivejšie
- PWM obvod izoluje ESP32 GPIO od záťaže

---

## Softvér – TODO

### 1. Nový súbor `led_manager.h` + `led_manager.cpp`

- [ ] Definovať GPIO pin pre LED (napr. `LED_PIN = 25`)
- [ ] Definovať konštanty pre časovanie:
  - `LED_PULSE_INTERVAL = 1000ms` (pulzovanie pri chybe)
  - `LED_BLINK_FAST = 100ms` (rýchle bliknutie po stlačení)
  - `LED_BLINK_COUNT = 2` (počet bliknutí po stlačení)
- [ ] Implementovať stavový automat: `LED_OK`, `LED_PULSE`, `LED_BLINK`
- [ ] Všetko cez `millis()` – **žiadne `delay()`!**
- [ ] Použiť `ledcSetup` / `ledcWrite` pre PWM (plynulé pulzovanie)

### 2. Upraviť `config.cpp` / `config.h`

- [ ] Pridať `LED_PIN = 25` (alebo iný voľný GPIO)
- [ ] Pridať časovacie konštanty

### 3. Upraviť `esp32_mqtt_button.ino`

- [ ] `#include "led_manager.h"`
- [ ] V `setup()`: zavolať `initializeLED()`
- [ ] V `loop()`: zavolať `updateLED()` každý cyklus
- [ ] Po `publishSceneTrigger()`: zavolať `triggerLEDBlink()`

### 4. Logika stavov v `led_manager.cpp`

- [ ] `updateLED()` číta `isMqttConnected()` a `isWiFiConnected()`
- [ ] Ak oboje OK → `LED_OK` → `digitalWrite HIGH`
- [ ] Ak niečo FAIL → `LED_PULSE` → sínusové alebo on/off pulzovanie cez `millis()`
- [ ] Ak `triggerLEDBlink()` zavolaný → `LED_BLINK` → 2x bliknutie, potom späť do predchádzajúceho stavu

---

## Voľné GPIO piny na DEVKITu (vhodné pre LED)

| Pin | Poznámka |
|---|---|
| IO25 | ✅ odporúčaný, bez špeciálnych funkcií |
| IO26 | ✅ OK |
| IO27 | ✅ OK |
| IO33 | ✅ OK, len input-capable ale PWM funguje |

**Nepoužívaj:** IO34, IO35 (len vstup), IO0, IO2 (boot piny)

---

## Schéma – čo pridať do KiCadu

- [ ] Nový GPIO pin (napr. IO25) → do PWM obvodu (IN)
- [ ] PWM obvod napájať z +5V a GND
- [ ] Výstup PWM obvodu → LED v tlačidle (cez KF301 ak je vzdialená)
- [ ] Pridať poznámku: "LED vstavaná v tlačidle, má vlastný R"
