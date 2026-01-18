# ESP32 MQTT Controller - Dokumentácia

## Prehľad projektu

Tento projekt implementuje modulárny MQTT kontrolér pre ESP32, navrhnutý primárne pre **Waveshare ESP32 Relay Module (I2C)**, ale s podporou pre klasické ESP32 (priame GPIO).

Systém ovláda sadu relé (svetlá, efekty) cez MQTT príkazy, obsahuje bezpečnostné prvky (Watchdog, Auto-off), statusovú LED signalizáciu a podporu pre OTA aktualizácie.

## Štruktúra súborov
```text
esp32_mqtt_controller/
├── esp32_mqtt_controller.ino    # Hlavný program (Setup & Loop)
├── config.h / .cpp              # Konfigurácia (Wifi, MQTT, definícia zariadení)
├── hardware.h / .cpp            # Abstrakcia hardvéru (I2C expandér alebo GPIO)
├── wifi_manager.h / .cpp        # Správa WiFi pripojenia (reconnect logika)
├── mqtt_manager.h / .cpp        # MQTT klient, callbacky a statusy
├── status_led.h / .cpp          # Ovládanie RGB LED (statusy, chyby, OTA)
├── ota_manager.h / .cpp         # Správa bezdrôtovej aktualizácie (OTA)
├── connection_monitor.h / .cpp  # Monitorovanie stavu siete
└── debug.h / .cpp               # Pomocné debug výpisy
```

## Kľúčové vlastnosti a konfigurácia

### 1. Hardvérové režimy (config.cpp)

Systém podporuje dva režimy fungovania, prepínané konštantou `USE_RELAY_MODULE`:

**Režim Waveshare Relay (TRUE):**
- Komunikácia cez I2C (piny 41/42 pre ESP32-S3)
- Ovládanie relé pomocou I2C expandéra (adresa 0x20)
- Využíva RGB LED na doske pre status signalizáciu

**Režim Direct GPIO (FALSE):**
- Priame ovládanie GPIO pinov
- Status LED je deaktivovaná (aby neblokovala piny)

### 2. Definícia zariadení

Zariadenia sú definované v poli `DEVICES` v súbore `config.cpp`. Každé zariadenie má:

- **MQTT Topic**: (napr. `room1/effect/smoke`)
- **Pin/Bit**: Bit na expandéri alebo číslo GPIO pinu
- **Inverted**: Logika spínania (NC/NO)
- **AutoOffMs**: Čas v milisekundách pre automatické vypnutie (0 = trvalo zapnuté)

**Aktuálna konfigurácia:**
- Dymostroj (`effect/smoke`): Auto-off po 5 sekundách
- Svetlá 1-6 (`light/1` - `light/6`): Trvalé spínanie (Auto-off = 0)

## Detailný popis modulov

### esp32_mqtt_controller.ino
- Hlavný vstupný bod
- Inicializuje Watchdog (WDT) s timeoutom 60s
- Spúšťa hardvér, WiFi a OTA
- V hlavnej slučke `loop()` obsluhuje OTA, LED, MQTT a časovače

### hardware.cpp - Správa relé
- Zabezpečuje fyzické ovládanie výstupov
- **I2C vs GPIO**: Podľa konfigurácie posiela dáta do expandéra alebo priamo na piny
- **Auto-off logika**: Funkcia `handleAutoOff()` sleduje čas zapnutia každého zariadenia (ak má nastavený limit) a automaticky ho vypne
- **Bezpečnosť**: Funkcia `turnOffAllDevices()` okamžite vypne všetko (volané pri strate spojenia alebo štarte OTA)

### status_led.cpp - Vizuálna signalizácia
Ovláda RGB LED (iba v režime Waveshare Relay):

- 🔴 **Červená** (rýchle blikanie): Chyba WiFi
- 🟠 **Oranžová** (stredné blikanie): WiFi OK, ale chyba MQTT
- 🟢 **Zelená** (pomalé dýchanie): Všetko OK (Online)
- 🔵 **Modrá** (svieti): Prebieha OTA aktualizácia

### ota_manager.cpp - Aktualizácie
- Umožňuje nahrať nový firmvér cez WiFi
- **Bezpečnosť**: Pred začatím aktualizácie automaticky vypne všetky relé a dočasne deaktivuje Watchdog
- Signalizuje proces modrou LED
- **Hostname**: `ESP32-RelayModule-Room1`

### mqtt_manager.cpp
Pripája sa k brokerovi a počúva príkazy.

**Topics:**
- **Príkazy**: `room1/[nazov_zariadenia]` (Payload: `ON`/`OFF` alebo `1`/`0`)
- **Stop všetkému**: `room1/STOP`
- **Status**: `devices/esp32_relay_controller/status` (správy `online`/`offline`)

Pri každom príkaze resetuje časovač nečinnosti (`NO_COMMAND_TIMEOUT`), aby sa zabránilo bezpečnostnému vypnutiu.

## Bezpečnostné mechanizmy

- **Watchdog Timer**: Reštartuje ESP32, ak systém zamrzne na viac ako 60 sekúnd
- **Safety Shutdown**:
  - Pri strate MQTT spojenia sa všetko vypne
  - Pri dlhej nečinnosti (žiadny príkaz > 10 minút) sa všetko vypne
  - Pri štarte OTA update sa všetko vypne
- **Reconnect Logika**: Exponenciálne predlžovanie intervalov pri výpadku WiFi/MQTT (šetrí sieť a CPU)

## Rozšírenie systému

Pre pridanie nového relé stačí upraviť pole `DEVICES` v `config.cpp`:
```cpp
// Príklad: Pridanie ventilátora na bit 7 s časovačom 10 minút
{"fan/cooling", 7, false, 600000},
```