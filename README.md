# Museum System

A complete control system for interactive museum rooms.

The system is divided into:
- **Raspberry Pi backend** (`raspberry_pi/`) – orchestrates scenes, audio/video, dashboard API, and health monitoring.
- **ESP32 firmware** (`esp32/devices/wifi/`) – executes physical commands via MQTT.
- **UI/editor projects** (`museum-dashboard/`) – dashboard interface.

---

## 1) Currently Used Production Components

### Raspberry Pi Controller

- **Entry point:** `raspberry_pi/main.py` (`MuseumController`).
- **Core runtime:** `raspberry_pi/utils/`.
- **Web dashboard server:** `raspberry_pi/Web/`.

### ESP32 Devices (WiFi)

- `esp32_mqtt_button` – wireless scene trigger.
- `esp32_mqtt_controller_MOTORS` – controls 2 motors.
- `esp32_mqtt_controller_RELAY` – relay outputs + effects groups.

### Data & Configuration

- **Scenes:** `raspberry_pi/scenes/<room_id>/*.json`
- **Room config:** `raspberry_pi/config/config.ini`

---

## 2) Quick Runtime Flow

1. `MuseumController` loads the configuration and starts standalone services via the `ServiceContainer`.
2. The MQTT client connects to the broker and subscribes to required room topics.
3. A trigger (physical `button`, MQTT message, or the web dashboard) starts a scene.
4. The trio of `SceneParser` + `StateMachine` + `StateExecutor` execute the `onEnter/timeline/onExit` actions defined in the scene file.
5. `TransitionManager` decides state transitions based on triggers (`timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always`).
6. Once the scene naturally ends (or is forcefully stopped), the backend publishes a `roomX/STOP` signal to kill all devices.

---

## 3) MQTT Data Model (Current Implementation)

### Scenes

- `roomX/scene` + `START` → Starts the default scene (defined by `json_file_name` in config).
- `roomX/start_scene` + `<scene_name.json>` → Loads and starts a specific named scene file.

### Device Status

- `devices/<device_id>/status` (Retained payload, typically `online`/`offline`).

### Command Feedback

- `<device_id>/feedback` (Responses depend on the device firmware: `OK`, `ERROR`, `ACTIVE`, `INACTIVE`).

### Command Topics (As used by repo's ESP32 nodes)

- **Motors**: `room1/motor1`, `room1/motor2`, `room1/STOP`
- **Relays/Effects**: `room1/<relay_name>`, `room1/effects/<group>`, `room1/STOP`
- **Trigger Button Publish**: `room1/scene` -> `START`

---

## 4) Running the Backend

**Production Deployment (Automated):**

The repository contains an installation bash script that automatically adjusts OS permissions (required for hardware audio/video without X11), creates `systemd` services, and sets up a Python virtual environment.

```bash
cd raspberry_pi
./install.sh
```

**Local Development / Manual Start:**

```bash
cd raspberry_pi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

After startup, the web dashboard runs locally on the port configured in `config.ini` under `[System]` → `web_dashboard_port`.

---

## 5) Documentation Reference

- `docs/architecture.md` – Complete system topology, component breakdown, and runtime bindings.
- `docs/mqtt_topics.md` – Reference sheet for all fully supported/implemented MQTT topics and payloads.
- `docs/audio_playing_tutorial.md` – Guide to audio capabilities and commands within scene JSON files.
- `docs/video_player_tutorial.md` – Guide to video capabilities and commands within scene JSON files.
- `docs/museum_setup_guide.md` – Advanced setup checklist (including instructions for the new automatic `install.sh`).

---

## 6) Important Note on Docs Maintenance

All documentation reflects the **actual current codebase implementation**, not outdated design plans.

If you add a new MQTT command, hardware topic, or scene action, please adhere to the following checklist:
1. Update the implementation code (Raspberry Pi backend + ESP32 firmware).
2. Adjust test scenes to reflect new functionality.
3. Keep the corresponding guides in the `docs/` folder accurately synced.