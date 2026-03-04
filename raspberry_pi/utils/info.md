# `raspberry_pi/utils` – Detailed Overview

This folder contains the core runtime modules for the backend.

1. `state_machine.py` loads and validates the scene, holds current state.
2. `scene_parser.py` manages scene start/process/stop and audio preloading.
3. `state_executor.py` executes actions (`mqtt`, `audio`, `video`).
4. `transition_manager.py` evaluates state transitions (thread-safe).

## 1) Scene Execution Stack

- `state_machine.py`
  - Loading and parsing the JSON scene file
  - Schema validation (via `schema_validator.py`) + logical validation (state targets)
  - Holding current state, scene/state timers, and state history
  - Optional `on_state_change` callback for dashboard integration

- `scene_parser.py`
  - Coordinates scene start/process/stop
  - Scans scene JSON and preloads SFX files into RAM before starting
  - Registers audio/video end callbacks and forwards them to the transition manager
  - Forwards incoming MQTT events to the transition manager
  - Handles state changes: onExit → goto → onEnter

- `state_executor.py`
  - Executes actions by type (`mqtt`, `audio`, `video`) via a dispatch table
  - Handles `onEnter`, `onExit`, and `timeline` (time-triggered actions)
  - Tracks executed timeline actions per state to prevent re-firing

- `transition_manager.py`
  - Evaluates transitions within a state using thread-safe event queues
  - Supported types: `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always`
  - Events are consumed (removed) when matched

---

## 2) Media Modules

- `audio_handler.py`
  - pygame mixer initialization with multiple fallback configs and retry logic
  - Two playback paths: music streaming from disk, SFX playback from RAM cache
  - SFX files (prefixed `sfx_`) are preloaded into RAM before scene start
  - Multi-channel polyphonic SFX support (32 mixer channels)
  - Command parser (`PLAY`, `STOP`, `STOP:<file>`, `PAUSE`, `RESUME`, `VOLUME`)
  - End-of-track detection for `audioEnd` transitions

- `video_handler.py`
  - mpv process management with Unix IPC socket communication
  - Displays a black idle image when no video is playing
  - Process health monitoring at a configurable interval
  - Automatic restart on process crash or IPC timeout (with attempt/cooldown limits)
  - End-of-video detection for `videoEnd` transitions

---

## 3) System / Infrastructure Modules

- `config_manager.py` – Loads `config.ini` (auto-creates from `config.ini.example` if missing), exposes all settings as structured dictionaries.
- `logging_setup.py` – Sets up the `museum` logger: color console output, async SQLite log history, rotating error log file, and per-component level overrides.
- `bootstrap.py` – Minimal logging available before full config is loaded; writes critical startup errors to a rotating file.
- `schema_validator.py` – JSON schema validation for scene files using `jsonschema`.
- `service_container.py` – Initializes all services in dependency order (audio, video, MQTT, system monitor, button) and handles graceful cleanup.
- `system_monitor.py` – Periodic health checks (MQTT, CPU, memory, disk) and startup info logging.
- `button_handler.py` – Hardware button input via GPIO polling with debounce logic and a configurable callback.

---

## 4) MQTT Package

MQTT details are documented in:
- `utils/mqtt/info.md`