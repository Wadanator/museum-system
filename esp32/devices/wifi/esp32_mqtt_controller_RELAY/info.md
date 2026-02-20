# ESP32 MQTT Relay Controller (`esp32_mqtt_controller_RELAY`)

## Úloha

MQTT ovládanie relé zariadení + efektových skupín.

## Subscribe topics

- `room1/<device_name>` (name podľa `DEVICES[]` v `config.cpp`)
- `room1/effects/#`
- `room1/STOP`

## Aktuálne device names (`DEVICES[]`)

- `power/smoke_ON`
- `light/fire`
- `light/1`
- `effect/smoke`
- `light/2`
- `light/3`
- `light/4`
- `light/5`

## Effect groups (`effects_config.h`)

- `group1`
- `alone`

Použitie:
- `room1/effects/group1` -> `ON` / `OFF`
- `room1/effects/alone` -> `ON` / `OFF`

## Feedback + status

- Feedback: `<command_topic>/feedback` (`OK`/`ERROR` alebo `ACTIVE`/`INACTIVE` pre efekty)
- Status: `devices/Room1_Relays_Ctrl/status`

## Poznámka

Tento firmware podporuje Waveshare relay modul (I2C) aj direct GPIO režim podľa configu.
