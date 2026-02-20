# Museum System

Repo obsahuje kompletný systém pre 1+ miestností v múzeu:
- **Raspberry Pi controller** (Python) spúšťa scény, audio/video a dashboard.
- **ESP32 zariadenia** vykonávajú príkazy cez MQTT (button trigger, motory, relé/effects).
- **SceneGen** je editor scén.

## Aktuálne komponenty

- `raspberry_pi/main.py` – hlavný orchestrátor (`MuseumController`).
- `raspberry_pi/utils/` – state machine, audio/video handlery, MQTT vrstva, monitoring.
- `raspberry_pi/Web/` – Flask dashboard + API routes.
- `esp32/devices/wifi/` – 3 produkčné firmware varianty:
  - `esp32_mqtt_button`
  - `esp32_mqtt_controller_MOTORS`
  - `esp32_mqtt_controller_RELAY`
- `raspberry_pi/scenes/` – scény podľa `room_id` (`room1`, `room2`).
- `docs/` – technická dokumentácia aktualizovaná podľa aktuálneho kódu.

## MQTT model (realita v kóde)

### Trigger scény
- `roomX/scene` + payload `START` → spustí default scénu.
- `roomX/start_scene` + payload `nazov_suboru.json` → spustí konkrétnu scénu.

### Kontrola zariadení (Room 1)
- Motory: `room1/motor1`, `room1/motor2`, `room1/STOP`
- Relé/effects: `room1/<device_name>`, `room1/effects/<group>`, `room1/STOP`
- Feedback: `<command_topic>/feedback` (`OK` / `ERROR` / `ACTIVE` / `INACTIVE`)
- Device status: `devices/<client_id>/status` (`online` / `offline` retained)

## Spustenie Raspberry Pi controllera

```bash
cd raspberry_pi
pip install -r requirements.txt
python3 main.py
```

Konfigurácia je v `raspberry_pi/config/config.ini` (alebo `.example`).

## Poznámka

Tento README zámerne neobsahuje staré/plánované časti, ktoré nie sú implementované v aktuálnom backende alebo ESP32 firmware.
