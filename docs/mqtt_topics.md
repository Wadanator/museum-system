# MQTT Topics & payloady (kanonická verzia)

Toto je **hlavný referenčný dokument** pre MQTT v tomto repozitári.
Obsah je zosúladený s:

- `raspberry_pi/utils/mqtt/*`
- `esp32/devices/wifi/*`

---

## 1) Triggerovanie scén (Raspberry Pi backend)

## 1.1 Default scéna

- **Topic:** `roomX/scene`
- **Payload:** `START`
- **Efekt:** `MQTTMessageHandler` zavolá `button_callback` (`MuseumController.on_button_press`).

## 1.2 Named scéna

- **Topic:** `roomX/start_scene`
- **Payload:** `<scene_file>.json`
- **Efekt:** backend zavolá callback `start_scene_by_name(...)`.

---

## 2) Device status topics

- **Topic pattern:** `devices/<client_id>/status`
- **Typický payload:** `online` / `offline`
- **Poznámka:** ESP32 používajú retained status + LWT `offline`.

Príklady z aktuálneho firmvéru:

- `devices/Room1_ESP_Trigger/status`
- `devices/Room1_ESP_Motory/status`
- `devices/Room1_Relays_Ctrl/status`

---

## 3) Feedback topics

- **Topic pattern:** `<command_topic>/feedback`
- **Použitie:** backend feedback tracker páruje command publish s odpoveďou zariadenia.

Typické payloady:

- motory/relé command: `OK` / `ERROR`
- relay effect group: `ACTIVE` / `INACTIVE`

---

## 4) Topics pre ESP32 zariadenia v tomto repo

## 4.1 `esp32_mqtt_button`

Publish:

- `room1/scene` -> `START`

Status:

- `devices/Room1_ESP_Trigger/status`

---

## 4.2 `esp32_mqtt_controller_MOTORS`

Subscribe:

- `room1/motor1`
- `room1/motor2`
- `room1/STOP`

Feedback:

- `room1/motor1/feedback`
- `room1/motor2/feedback`
- `room1/STOP/feedback`

Status:

- `devices/Room1_ESP_Motory/status`

Podporované payloady (firmware parser):

- `ON:<speed>:<direction>`
- `ON:<speed>:<direction>:<rampTime>`
- `OFF`
- `SPEED:<value>`
- `DIR:<value>`

Príklady:

- `room1/motor1` -> `ON:120:L`
- `room1/motor2` -> `ON:80:R:5000`
- `room1/motor1` -> `OFF`

---

## 4.3 `esp32_mqtt_controller_RELAY`

Subscribe:

- `room1/<device_name>`
- `room1/effects/#`
- `room1/STOP`

Status:

- `devices/Room1_Relays_Ctrl/status`

### Device names (aktuálne `DEVICES[]`)

- `power/smoke_ON`
- `light/fire`
- `light/1`
- `effect/smoke`
- `light/2`
- `light/3`
- `light/4`
- `light/5`

Mapovanie na command topic teda vyzerá napr.:

- `room1/light/1` -> `ON` / `OFF`
- `room1/effect/smoke` -> `ON` / `OFF`

### Effects groups (`effects_config.h`)

- `group1`
- `alone`

Príklady:

- `room1/effects/group1` -> `ON`
- `room1/effects/group1` -> `OFF`

---

## 5) Room STOP semantics

`roomX/STOP` je globálny kill signal pre zariadenia v miestnosti.

Backend ho posiela:

- pri `stop_scene()`,
- po prirodzenom ukončení scény,
- po niektorých chybových/cleanup vetvách.

ESP32 firmware ho má subscribnutý a vykoná okamžité vypnutie výstupov.

---

## 6) Poznámky k kompatibilite

- Scene action payload môže byť string/number/bool (schema + executor).
- Ak pridáš nový topic/payload, aktualizuj:
  1. firmware/backend logiku,
  2. test scénu,
  3. tento dokument.
