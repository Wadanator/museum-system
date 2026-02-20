# Architektúra (aktuálny stav)

## 1) Runtime topológia

1. `raspberry_pi/main.py` spustí všetky služby (MQTT, SceneParser, AudioHandler, VideoHandler, Web dashboard).
2. MQTT broker distribuuje príkazy medzi Pi a ESP32.
3. ESP32 zariadenia publikujú status (`devices/.../status`) a feedback (`.../feedback`).

## 2) Raspberry Pi moduly

- **State machine**
  - `utils/state_machine.py` – načítanie + validácia stavu scény.
  - `utils/scene_parser.py` – lifecycle scény, event forwarding.
  - `utils/state_executor.py` – vykonávanie `mqtt`, `audio`, `video` akcií.
  - `utils/transition_manager.py` – transitions: `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always`.

- **Media**
  - `utils/audio_handler.py` – `pygame`, preload `sfx_` súborov, callback pri dohraní.
  - `utils/video_handler.py` – `mpv` cez IPC socket.

- **MQTT vrstva**
  - `utils/mqtt/mqtt_client.py` – connect/reconnect, subscribe, publish.
  - `utils/mqtt/mqtt_message_handler.py` – routing správ.
  - `utils/mqtt/mqtt_feedback_tracker.py` – tracking command feedback.
  - `utils/mqtt/mqtt_device_registry.py` – registry online/offline zariadení.
  - `utils/mqtt/mqtt_contract.py` – validácia topic/payload pre publish.

- **Web UI**
  - `Web/dashboard.py`, `Web/routes/*` – dashboard + API pre scenes/commands/system.

## 3) MQTT subscriptions (Pi)

Backend sa subscribuje minimálne na:
- `devices/+/status`
- `roomX/+/feedback`
- `roomX/scene`
- `roomX/#`

(`roomX` je hodnota `room_id` z konfigurácie.)

## 4) ESP32 zariadenia v repozitári

- `esp32_mqtt_button` – tlačidlo publikuje trigger scény.
- `esp32_mqtt_controller_MOTORS` – ovládanie `motor1`/`motor2`.
- `esp32_mqtt_controller_RELAY` – relé + effect groups (`room1/effects/...`).

## 5) Formát scény

Scene JSON má root:
- `sceneId`, `initialState`, `states`
- voliteľne `version`, `description`, `globalEvents`

Akcie: `mqtt`, `audio`, `video`.
Transitions: `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always`.

Podrobnosti sú v `docs/mqtt_topics.md`, `docs/audio_playing_tutorial.md`, `docs/video_player_tutorial.md`.
