# Utils Package Overview

The `utils` package contains the reusable building blocks that power the museum room controller. Each module encapsulates a distinct responsibility—media playback, MQTT connectivity, state-machine execution, monitoring, or configuration—so rooms can be customized without rewriting core logic.

---

## Module Reference

### `config_manager.py`
Loads `config/config.ini`, merges defaults with per-room overrides, and exposes helpers to fetch structured configuration dictionaries. It also validates critical paths (scene directory, media directories) during startup.

### `logging_setup.py`
Constructs the logging policy used by the controller. It supports console output, rotating log files split by severity, JSON formatting, and per-component log level overrides. Uncaught exceptions are captured and routed through the logging framework.

### `mqtt/` Package
- `mqtt_client.py` – Handles broker connectivity with retry logic, keep-alives, and thread-safe publish/subscribe helpers.
- `mqtt_message_handler.py` – Routes inbound messages (button topics, device feedback, controller RPCs) to callbacks registered by the scene parser and controller.
- `mqtt_feedback_tracker.py` – Tracks acknowledgements for published commands so transitions can react to success/failure within configurable timeouts.
- `mqtt_device_registry.py` – Maintains a registry of known devices, including last-seen timestamps and health heuristics.

### `scene_parser.py`
Parses JSON scene files into `State` objects backed by the state machine. Validates schema, resolves resource references, and binds handlers for audio/video/MQTT actions. Also surfaces helpful diagnostics for malformed scenes.

### `state_machine.py`
Defines the state, action, and transition data structures. Provides serialization helpers, runtime metadata, and utility methods used by executors and the dashboard to report current progress.

### `state_executor.py`
Executes state actions with millisecond precision using worker threads and timers. Integrates with the feedback tracker to pause, retry, or branch based on acknowledgements from devices.

### `transition_manager.py`
Implements transition policies (e.g., `on_complete`, `on_timeout`, `on_feedback`, `goto`, `loop`). New directives can be added here to expand the scene vocabulary without altering the controller.

### `audio_handler.py`
Wraps Pygame mixer initialization, playback, and teardown. Supports command strings (`PLAY:`, `STOP`, `VOLUME:`) that scenes use to control audio assets stored in the configured directory.

### `video_handler.py`
Manages an MPV subprocess via IPC, exposing operations such as play, stop, fade-to-black, and idle screen management. Automatically recreates the player if the process exits unexpectedly.

### `button_handler.py`
Configures the GPIO pin for the room’s start button, applying debounce logic and running a background thread to detect presses. Exposes a callback hook consumed by `MuseumController`.

### `system_monitor.py`
Collects system metrics (CPU load, memory usage, disk space) and writes periodic heartbeat logs. It can also notify systemd of readiness and record MQTT connection status for diagnostics.

---

These utilities are composed by `MuseumController` in `main.py`. Because each responsibility is isolated, you can extend the system by modifying or subclassing individual modules—such as creating a custom feedback tracker—without touching unrelated functionality.
