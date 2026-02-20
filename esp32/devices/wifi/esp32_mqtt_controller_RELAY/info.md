# ESP32 MQTT Relay Controller (`esp32_mqtt_controller_RELAY`)

Firmware pre ovládanie relé zariadení a efektových skupín cez MQTT.

---

## 1) Hlavná funkcionalita

- ovládanie jednotlivých device výstupov podľa `DEVICES[]`,
- podpora `room1/effects/<group>` patternu,
- feedback publish na command feedback topic,
- status publish pre device registry,
- safety logika (STOP, inactivity timeout, reconnect).

---

## 2) MQTT topics

Subscribe:
- `room1/<device_name>` (odvodené z `DEVICES[]`)
- `room1/effects/#`
- `room1/STOP`

Status:
- `devices/Room1_Relays_Ctrl/status`

Feedback:
- `<command_topic>/feedback`

Payloady:
- zariadenia: `ON`/`OFF` (akceptované aj `1`/`0`)
- effects group: `ON`/`OFF` (príp. `START`/`STOP` aliasy)

---

## 3) Aktuálne device names (`config.cpp`)

- `power/smoke_ON`
- `light/fire`
- `light/1`
- `effect/smoke`
- `light/2`
- `light/3`
- `light/4`
- `light/5`

Príklad:
- `room1/light/4` -> `ON`
- `room1/effect/smoke` -> `OFF`

---

## 4) Effect groups (`effects_config.h`)

Aktuálne skupiny:
- `group1`
- `alone`

Použitie:
- `room1/effects/group1` -> `ON` / `OFF`
- `room1/effects/alone` -> `ON` / `OFF`

Pri `ON` sa spúšťa interná random/blink logika skupiny,
pri `OFF` sa efekt zastaví.

---

## 5) Hardware režimy

Firmware podporuje:
- Waveshare relay modul cez I2C,
- direct GPIO režim.

Voľba závisí od config premenných (`USE_RELAY_MODULE` a súvisiace piny/adresy).

---

## 6) Safety správanie

- `room1/STOP` -> vypnutie zariadení + efektov.
- pri dlhšej nečinnosti (timeout) môže nastať safety shutdown.
- watchdog/reconnect logika pomáha pri nestabilnej sieti.

---

## 7) Konfigurácia pred deployom

Skontroluj:
- WiFi credentials,
- MQTT server + prefix,
- `CLIENT_ID`,
- mapovanie zariadení v `DEVICES[]`,
- OTA hostname/password,
- effect groups podľa požiadaviek miestnosti.
