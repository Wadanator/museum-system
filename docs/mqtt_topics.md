# MQTT topics – aktuálne podľa backendu + ESP32

## Trigger scény (Raspberry Pi)

### 1) Default scéna
- **Topic:** `roomX/scene`
- **Payload:** `START`
- Spracovanie: `mqtt_message_handler` rozpozná `.../scene` + `START` a volá callback na štart scény.

### 2) Spustenie konkrétnej scény
- **Topic:** `roomX/start_scene`
- **Payload:** `scene_file.json`
- Spracovanie: callback pre named scene.

## Device status

- **Topic:** `devices/<client_id>/status`
- **Payload:** typicky `online` / `offline`
- Retained message používaná na online/offline prehľad.

## Command feedback

- **Topic:** `<command_topic>/feedback`
- **Payload (motors/relay):** `OK` alebo `ERROR`
- **Payload (effects):** `ACTIVE` alebo `INACTIVE`

## Topics používané ESP32 firmware v repozitári

### A) `esp32_mqtt_button`
- Publish: `room1/scene` -> `START`
- Publish status: `devices/Room1_ESP_Trigger/status`

### B) `esp32_mqtt_controller_MOTORS`
- Subscribe:
  - `room1/motor1`
  - `room1/motor2`
  - `room1/STOP`
- Publish feedback: `<topic>/feedback`
- Publish status: `devices/Room1_ESP_Motory/status`

Podporované payloady motorov:
- `ON:<speed>:<direction>`
- `ON:<speed>:<direction>:<rampTime>`
- `OFF`
- `SPEED:<value>`
- `DIR:<L|R|...>`

### C) `esp32_mqtt_controller_RELAY`
- Subscribe:
  - `room1/<device_name>` (device name je z `config.cpp` po `BASE_TOPIC_PREFIX`)
  - `room1/effects/#`
  - `room1/STOP`
- Publish status: `devices/Room1_Relays_Ctrl/status`
- Publish feedback: `<topic>/feedback`

Príklady device topics (podľa aktuálneho `DEVICES[]`):
- `room1/light/1`
- `room1/light/2`
- `room1/light/3`
- `room1/light/4`
- `room1/light/5`
- `room1/light/fire`
- `room1/effect/smoke`
- `room1/power/smoke_ON`

Effect groups:
- `room1/effects/group1`
- `room1/effects/alone`

## Poznámka

Staré návrhy topicov (display, sensor, system/* atď.) boli odstránené z hlavnej dokumentácie, pretože nie sú implementované v aktuálnom backend/ESP32 kóde tohto repozitára.
