# ESP32 LAN MQTT Relay Controller (`esp32_mqtt_controller_RELAY`)

LAN/W5500 verzia relay firmveru pre Waveshare ESP32-S3 PoE/LAN relay modul
s WiFi fallbackom.

Povodny WiFi projekt ostava v:

- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_RELAY/`

Tato LAN kopia je v:

- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/`

## Hlavna zmena oproti WiFi verzii

- `wifi_manager.cpp/.h` si nechava povodne nazvy funkcii kvoli kompatibilite so zvyskom kodu.
- LAN cez `ETH.h` + W5500 je primarny transport.
- WiFi sa pouzije ako fallback, ked LAN nema IP/link.
- Ked LAN znova ziska IP, MQTT sa odpoji z fallback WiFi a pripoji naspat cez LAN.
- MQTT, rele logika, efekty, OTA, status LED a device topics ostali z povodneho relay projektu.

## Failover spravanie

- Boot caka najprv na LAN.
- Po `LAN_PRIMARY_CONNECT_GRACE` ms sa spusti WiFi fallback.
- `wifiConnected`, `initializeWiFi()` a `isWiFiConnected()` znamenaju v tejto
  kopii "aspon jeden network transport je pripojeny".
- Aktivny transport je dostupny cez `getActiveNetworkName()`.
- Pri zmene transportu sa MQTT socket zavrie a pripoji nanovo na rovnakom
  client id `Room1_Relays_Ctrl`.
- Safety vypnutie pri strate MQTT ma `NETWORK_FAILOVER_GRACE` ms toleranciu,
  aby kratke prepnutie LAN/WiFi hned nevyplo rele.

WiFi fallback udaje su v `config.cpp`:

- SSID: `Museum-Room1`
- password: `88888888`

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
a `isWiFiConnected()`. V tejto LAN+WiFi kopii znamenaju "network connected",
teda LAN alebo fallback WiFi. Je to zamerne, aby sa nemuseli prepisovat vsetky
ostatne moduly.
