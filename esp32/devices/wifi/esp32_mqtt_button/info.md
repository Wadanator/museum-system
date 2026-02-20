# ESP32 MQTT Button (`esp32_mqtt_button`)

Firmware pre bezdrôtové tlačidlo, ktoré spúšťa scénu cez MQTT.

## MQTT správanie

## 1) Funkcia zariadenia

- číta fyzické tlačidlo,
- aplikuje debounce + cooldown,
- pri validnom stlačení publikuje trigger scény,
- priebežne publikuje status do `devices/.../status`.

- Button pin: `GPIO32`
- Debounce: `60ms`
- Cooldown medzi triggerom: `4000ms`

## 2) MQTT správanie

Publish trigger:
- topic: `room1/scene`
- payload: `START`

Status + LWT:
- status topic: `devices/Room1_ESP_Trigger/status`
- pri connecte: `online` (retained)
- LWT: `offline`

Firmware neposlúcha command topics (callback je prázdny), je to čisto publish trigger node.

---

## 3) Hardware nastavenie (aktuálne defaulty)

- `BUTTON_PIN = 32`
- `DEBOUNCE_DELAY = 60 ms`
- `BUTTON_COOLDOWN = 4000 ms`

---

## 4) Konfigurácia (`config.cpp`)

Pred deployom uprav:
- WiFi (`WIFI_SSID`, `WIFI_PASSWORD`)
- MQTT (`MQTT_SERVER`, `MQTT_PORT`)
- room prefix (`BASE_TOPIC_PREFIX`)
- scene topic suffix (`SCENE_TOPIC_SUFFIX`)
- OTA (`OTA_HOSTNAME`, `OTA_PASSWORD`, `OTA_ENABLED`)

---

## 5) Prevádzková poznámka

Ak meníš room prefix (napr. `room2/`), musí sedieť s backend `room_id`, inak trigger nespustí scénu.
