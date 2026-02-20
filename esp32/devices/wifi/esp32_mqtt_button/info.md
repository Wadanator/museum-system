# ESP32 MQTT Button (`esp32_mqtt_button`)

## Úloha

Bezdrôtové tlačidlo pre spustenie scény.

## MQTT správanie

- Publish trigger: `room1/scene` -> `START`
- Status topic: `devices/Room1_ESP_Trigger/status`
- Last Will: `offline`

## Hardware

- Button pin: `GPIO32`
- Debounce: `60ms`
- Cooldown medzi triggerom: `4000ms`

## Konfigurácia

Uprav v `config.cpp`:
- WiFi (`WIFI_SSID`, `WIFI_PASSWORD`)
- MQTT server/port
- `BASE_TOPIC_PREFIX`
- `SCENE_TOPIC_SUFFIX`, `SCENE_PAYLOAD`
