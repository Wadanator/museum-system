# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Museum automation system running on a Raspberry Pi 4. It orchestrates multi-room interactive experiences via MQTT, audio (pygame), video (mpv), and GPIO buttons. A Flask/SocketIO web dashboard provides live monitoring and control. ESP32 devices receive commands over MQTT and report back via feedback topics.

## Running the System

The system runs as a systemd service on the Pi. For development/testing:

```bash
cd raspberry_pi
source venv/bin/activate
python3 main.py
```

## Installation (on Raspberry Pi)

```bash
cd raspberry_pi
bash install.sh        # Online install — creates venv, installs systemd services
sudo reboot            # Required after first install to apply group permissions
```

## Running Tests

```bash
cd raspberry_pi
source venv/bin/activate
pytest tests/
pytest tests/test_schema_validator.py   # single file
```

## Service Management (on Pi)

```bash
sudo systemctl status museum-system
sudo systemctl restart museum-system
sudo journalctl -u museum-system -f
```

## Configuration

Copy `raspberry_pi/config/config.ini.example` to `raspberry_pi/config/config.ini`. Key sections:

- `[MQTT]` — broker IP/port and timeouts
- `[Room]` — `room_id` (e.g. `room1`) used as the MQTT topic namespace
- `[Json]` — default scene file triggered by button press
- `[Scenes]` — scenes directory (relative to `raspberry_pi/`)
- `[Audio]` / `[Video]` — media directories and mpv IPC socket path (`/tmp/mpv_socket`)
- `[System]` — loop timings, web dashboard port (default 5000)
- `[Logging]` / `[LogLevels]` — global level and per-component overrides

## Architecture

### Entry Points

- `raspberry_pi/main.py` — `MuseumController`: boots all services via `ServiceContainer`, owns the main loop, manages scene lifecycle (thread-safe state transitions via `_SCENE_STATE_FILE = /tmp/museum_scene_state`), wires all service callbacks.
- `raspberry_pi/watchdog.py` — `MuseumWatchdog`: monitors `museum-system.service`; reads `/tmp/museum_scene_state` and waits for a scene to finish before restarting to avoid interrupting presentations.

### Service Initialization (`utils/service_container.py`)

`ServiceContainer` initializes all components in strict dependency order:
AudioHandler → VideoHandler → MQTTDeviceRegistry → MQTTFeedbackTracker → MQTTMessageHandler → MQTTClient → SystemMonitor → ButtonHandler

Components that fail to initialize (audio, video, button) are set to `None`. All callers must guard with `if self.component:`.

### Scene Execution Stack (`utils/`)

Scenes are JSON state machines located in `raspberry_pi/scenes/<room_id>/`. Four classes coordinate execution:

| Class | Role |
|---|---|
| `state_machine.py` | Loads/validates JSON scene, holds current state and timers |
| `scene_parser.py` | Orchestrates start/process/stop; preloads `sfx_*` files into RAM before start |
| `state_executor.py` | Dispatches `mqtt`, `audio`, `video` actions for `onEnter`, `onExit`, `timeline` |
| `transition_manager.py` | Thread-safe evaluation of `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always` transitions |

Schema validation uses `jsonschema` via `utils/schema_validator.py`.

### MQTT Layer (`utils/mqtt/`)

- `mqtt_client.py` — paho wrapper, connect/reconnect retry, subscribe/publish
- `mqtt_message_handler.py` — routes incoming messages in priority order: device status → registry; feedback → tracker; `scene` topic + `START` → button callback; `start_scene` → named scene callback; everything else → scene parser (for `mqttMessage` transitions)
- `mqtt_feedback_tracker.py` — pairs published commands with `/feedback` acknowledgements
- `mqtt_device_registry.py` — tracks device online/offline from `devices/<id>/status`
- `topic_rules.py` — centralized topic patterns

Subscriptions on connect: `devices/+/status`, `<room_id>/+/feedback`, `<room_id>/scene`, `<room_id>/#`.

### Media Handlers

- `audio_handler.py` — pygame mixer with fallback init configs. Two playback paths: streaming (music) and RAM-cached SFX (`sfx_` prefix). Commands: `PLAY`, `STOP`, `STOP:<file>`, `PAUSE`, `RESUME`, `VOLUME`.
- `video_handler.py` — mpv process managed via Unix IPC socket. Shows idle image when stopped. Auto-restarts on crash with configurable attempt limit and cooldown.

### Web Dashboard (`Web/`)

Flask + Flask-SocketIO started in a daemon thread from `Web/app.py`. `WebDashboard` (`Web/dashboard.py`) holds in-memory log buffer and stats. Routes split across blueprints in `Web/routes/`. Built frontend assets served from `Web/dist/`.

## Session Habits

- **After every `.py` file change**: run `/python-review` before finishing the session. A hook reminder fires automatically.
- **At end of every session**: update `~/.claude/projects/C--Users-Wajdy-Documents-Kodovanie-museum-system/memory/project_state.md` with what was done and what's next, so the next session picks up instantly.

## Key Conventions

- All modules use `get_logger('name')` from `utils/logging_setup.py` — never `print()`.
- The Python venv lives at `raspberry_pi/venv/`. The systemd service sets `PYTHONPATH` to `raspberry_pi/` so all imports resolve from there.
- Named scenes are triggered via MQTT topic `<room_id>/start_scene` with the filename as payload.
- The scene state file `/tmp/museum_scene_state` is written `running`/`idle` by main.py and read by watchdog.py.
