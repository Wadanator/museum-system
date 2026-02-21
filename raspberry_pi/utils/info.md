# `raspberry_pi/utils` – Detailed Overview

This folder contains the core runtime modules for the backend.

1. `state_machine.py` loads and holds the current scene state.
2. `scene_parser.py` manages scene start/loop/stop.
3. `state_executor.py` executes actions (`mqtt`, `audio`, `video`).
4. `transition_manager.py` evaluates state transitions.

## 1) Scene Execution Stack

- `state_machine.py`
  - Loading the JSON scene file
  - Schema and logical validation
  - Holding current state, scene timers, and state history

- `scene_parser.py`
  - Coordinates scene start/process/stop
  - Registers audio/video end events
  - Forwards MQTT events to the transition manager
  - Dynamic audio preloading (SFX RAM cache)

- `state_executor.py`
  - Executes actions by type (`mqtt`, `audio`, `video`)
  - Handles `onEnter`, `timeline`, and `onExit`

- `transition_manager.py`
  - Evaluates transitions within a state
  - Supported types: `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always`

---

## 2) Media Modules

- `audio_handler.py`
  - pygame mixer initialization and retry logic
  - Music streaming and multi-channel SFX playback
  - Command parser (`PLAY`, `STOP`, `PAUSE`, `RESUME`, `VOLUME`)

- `video_handler.py`
  - mpv process management and IPC commands
  - Process health monitoring
  - Restart mechanisms on timeouts and errors

---

## 3) System / Infrastructure Modules

- `config_manager.py` – Configuration loading and normalization.
- `logging_setup.py` – Centralized logging setup with per-module level overrides.
- `system_monitor.py` – Periodic system health checks.
- `button_handler.py` – Hardware button input (polling or interrupt mode).
- `service_container.py` – Dependency injection style service assembly.
- `bootstrap.py` – Bootstrap logging and startup pipeline.
- `schema_validator.py` – JSON schema validation for scene files.

---

## 4) MQTT Package

MQTT details are documented in:
- `utils/mqtt/info.md`