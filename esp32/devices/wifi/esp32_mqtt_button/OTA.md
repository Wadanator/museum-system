# OTA – esp32_mqtt_button

## Predpoklady

- Firmware s OTA je už nahraný.
- ESP32 a PC sú v rovnakej sieti.
- V `config.cpp` je `OTA_ENABLED = true`.

## Upload

1. Otvor projekt v Arduino IDE.
2. Tools -> Port -> vyber **network port** podľa hostname (`OTA_HOSTNAME`).
3. Upload.

## Aktuálne defaulty v kóde

- `OTA_HOSTNAME = "ESP32-Room1-Trigger"`
- `OTA_PASSWORD = "room1"`
