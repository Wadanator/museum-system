# ESP32 LAN MQTT Relay Controller (`esp32_mqtt_controller_RELAY`)

LAN/W5500 verzia relay firmveru pre Waveshare ESP32-S3 PoE/LAN relay modul.

Povodny WiFi projekt ostava v:

- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_RELAY/`

Tato LAN kopia je v:

- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/`

## Hlavna zmena oproti WiFi verzii

- `wifi_manager.cpp/.h` si nechava povodne nazvy funkcii kvoli kompatibilite so zvyskom kodu.
- Vnutri vsak nepouziva WiFi, ale `ETH.h` + W5500 cez SPI.
- MQTT, rele logika, efekty, OTA, status LED a device topics ostali z povodneho relay projektu.

## Ethernet hardware

Waveshare modul ma W5500 Ethernet chip cez SPI.

Pouzite piny:

- `GPIO12` - ETH_INT
- `GPIO13` - ETH_MOSI
- `GPIO14` - ETH_MISO
- `GPIO15` - ETH_SCLK
- `GPIO16` - ETH_CS
- `GPIO39` - ETH_RST

Konfiguracia je v `config.cpp`.

## Arduino IDE poziadavky

Pouzi ESP32 Arduino core 3.x alebo novsi, pretoze W5500 cez `ETH.h`
je v tejto podobe podporovany tam.

Board v Arduino IDE:

- `ESP32S3 Dev Module`
- USB CDC podla aktualneho upload/debug nastavenia dosky

## MQTT

Bez zmeny oproti WiFi relay verzii:

- MQTT broker: `192.168.0.127`
- base topic: `room1/`
- client id/status device: `Room1_Relays_Ctrl`

Subscribe:

- `room1/<device_name>`
- `room1/effects/#`
- `room1/STOP`

Status:

- `devices/Room1_Relays_Ctrl/status`

Feedback:

- `<command_topic>/feedback`

## Device names

- `power/smoke_ON`
- `light/fire`
- `light/1`
- `effect/smoke`
- `light/2`
- `light/3`
- `light/4`
- `light/5`

## Effects

- `room1/effects/group1`
- `room1/effects/alone`

Payloady:

- zariadenia: `ON`, `OFF`, `1`, `0`
- effects: `ON`, `OFF`, `START`, `STOP`, `1`, `0`

## Poznamka k nazvom

V kode ostavaju identifikatory ako `wifiConnected`, `initializeWiFi()`
a `isWiFiConnected()`. V LAN projekte znamenaju "network/Ethernet connected".
Je to zamerne, aby sa nemuseli prepisovat vsetky ostatne moduly.
