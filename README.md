# Museum Automation Platform

An end-to-end control platform for interactive museum rooms. A Raspberry Pi orchestrates MQTT-driven devices, synchronized audio/video playback, and a web dashboard while ESP32 boards actuate lights, motors, and other effects. The system is designed so new rooms or devices can be introduced by configuration rather than code changes.

---

## Core Capabilities

- **Scene-based experiences** – JSON scene files describe timed states that combine MQTT commands, local audio/video cues, button triggers, and conditional transitions.
- **Modular device control** – MQTT communication is encapsulated in reusable client, registry, and feedback components that make it straightforward to add new ESP32 peripherals or message patterns.
- **Operational visibility** – A Flask + Socket.IO dashboard streams logs, exposes manual controls, and can upload/download scene files at runtime.
- **Reliability tooling** – A watchdog service, structured logging, and rich health checks keep unattended installations resilient.
- **Config-driven deployments** – Room identity, broker credentials, GPIO pins, resource directories, and logging policy all live in `config/config.ini`, enabling per-room overrides without modifying the codebase.

---

## System Architecture Overview

| Layer | Purpose | Key Modules |
| --- | --- | --- |
| **Orchestration** | Bootstraps configuration, logging, MQTT, the state machine, and web dashboard; coordinates shutdown. | `raspberry_pi/main.py` (`MuseumController`)
| **Scene Engine** | Interprets JSON scenes into deterministic state transitions that schedule MQTT/audio/video work and handle feedback. | `utils/scene_parser.py`, `utils/state_machine.py`, `utils/state_executor.py`, `utils/transition_manager.py`
| **Media Services** | Provide local playback primitives for synchronized shows. | `utils/audio_handler.py`, `utils/video_handler.py`
| **MQTT Stack** | Handles broker connectivity, device presence, message routing, and acknowledgement tracking. | `utils/mqtt/` package
| **Inputs & Monitoring** | Polls exhibit buttons, records system metrics, and emits readiness/alert logs. | `utils/button_handler.py`, `utils/system_monitor.py`
| **Operator Interface** | Web UI served from Flask blueprint with Socket.IO updates. | `raspberry_pi/Web/`
| **Peripheral Firmware** | ESP32 sketches implementing topic handlers for actuators/sensors. | `esp32/`

The state machine runs on a dedicated thread, ensuring long-running device actions do not block other museum rooms. MQTT feedback is tracked per command, allowing scenes to branch or retry when devices report errors.

---

## Scene Lifecycle (Raspberry Pi)

1. **Trigger** – A GPIO button press or dashboard command asks the `MuseumController` to launch a scene file.
2. **Parse** – `SceneParser` loads the JSON, validates timelines, and converts entries into `State` objects.
3. **Execute** – `StateExecutor` schedules actions (MQTT publishes, audio/video cues, waits) and registers callbacks for asynchronous completions.
4. **Transition** – `TransitionManager` evaluates scene logic (timeouts, feedback, external signals) to determine the next state or exit.
5. **Monitor** – `SystemMonitor` and the dashboard stream live status, while the watchdog restarts services if health checks fail.

Adding new behaviors typically involves extending the scene JSON schema and the transition manager, without rewriting the controller.

---

## Repository Layout

```
README.md                 Project overview (this file)
SceneGen/                 GUI tool for authoring scene JSON files
createrepo.py             Helper for packaging deployments

raspberry_pi/
  Web/                    Flask dashboard (templates, static assets, blueprint)
  broker/                 Local Mosquitto broker assets
  config/                 `config.ini` plus environment-specific overrides
  scenes/                 Example room scene definitions
  service/                systemd unit/service helper scripts
  tools/                  Diagnostic utilities (log capture, topic replay, etc.)
  utils/                  Core orchestration modules (media, MQTT, state machine)
  videos/                 Placeholder media assets
  main.py                 Entry point launched by systemd
  watchdog.py             Standalone watchdog/auto-recovery loop

esp32/                    Firmware sketches for MQTT peripherals

docs/                     Architecture notes, tutorials, and operational guides
```

---

## Getting Started

1. **Install Raspberry Pi requirements**
   ```bash
   cd raspberry_pi
   pip install -r requirements.txt
   ```
2. **Configure the room**
   - Duplicate `raspberry_pi/config/config.example.ini` (if provided) and edit broker credentials, GPIO pins, media directories, and dashboard port.
   - Place audio in `audio/`, video in `videos/`, and scene JSON in `scenes/` (each entry references files by filename).
3. **Run the controller locally**
   ```bash
   python3 raspberry_pi/main.py
   ```
4. **Access the dashboard** – visit `http://<pi-address>:<web_dashboard_port>` for status, manual triggers, and log streaming.
5. **Enable auto-start** – follow [`docs/museum_setup_guide.md`](docs/museum_setup_guide.md) to install the systemd service.

---

## Extending the Platform

- **Add a device** – Register a new MQTT topic in your scene JSON. For more structured integrations, extend the registry or feedback tracker in `utils/mqtt/` to model device state.
- **Create new transitions** – Modify `transition_manager.py` to interpret additional scene directives (e.g., sensor-driven branching).
- **Customize the dashboard** – Update templates or Socket.IO channels under `raspberry_pi/Web/`.
- **Author new scenes** – Use the `SceneGen` tool or hand-edit JSON according to the schema documented in `docs/mqtt_topics.md` and related guides.

---

## Additional Documentation

- [`docs/architecture.md`](docs/architecture.md) – Deep dive into runtime components and message flow.
- [`docs/museum_setup_guide.md`](docs/museum_setup_guide.md) – Raspberry Pi service installation instructions.
- [`docs/audio_playing_tutorial.md`](docs/audio_playing_tutorial.md) & [`docs/video_player_tutorial.md`](docs/video_player_tutorial.md) – Media tooling notes.
- [`docs/mqtt_topics.md`](docs/mqtt_topics.md) – Canonical MQTT topic structure for rooms and devices.

For future work items and ideas, see `TODO.txt`.
