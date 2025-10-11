# Museum Automation System Architecture

## Runtime Topology

The museum deployment consists of a single MQTT broker that coordinates multiple Raspberry Pi room controllers and ESP32 device nodes. Each room controller is responsible for executing show scenes for its room:

- **MQTT Broker** – Typically Mosquitto, can run locally on the Raspberry Pi or centrally. All room controllers and ESP32 devices connect here.
- **Raspberry Pi Room Controller** – Runs `raspberry_pi/main.py` as a systemd service. Hosts the scene engine, media handlers, and the operator dashboard.
- **ESP32 Peripherals** – Subscribe to room-scoped MQTT topics and drive actuators (lighting, motors, relays, fog machines, etc.). Many sketches live under `esp32/`.

Controllers communicate only through MQTT topics; no direct socket calls are required between rooms.

## Controller Internals

```
+---------------------------+      +----------------------------+
| MuseumController          |      | SystemMonitor              |
|  - ConfigManager          |<---->|  health + metrics logging  |
|  - Logging setup          |      +----------------------------+
|  - MQTTClient             |
|  - SceneParser            |      +----------------------------+
|  - AudioHandler           |----->| Audio subsystem (pygame)   |
|  - VideoHandler           |----->| Video subsystem (mpv IPC)  |
|  - ButtonHandler          |      +----------------------------+
|  - Web dashboard thread   |
+-------------|-------------+
              |
              v
        +-----------+
        | State      |
        | Machine    |
        | (Scene     |
        | Executor)  |
        +-----------+
```

### Configuration & Logging
- `ConfigManager` reads `config/config.ini`, exposing sections for MQTT connection details, file paths, timings, GPIO pins, and dashboard configuration.
- `logging_setup` builds a multi-handler logging configuration (console, daily rotating files, severity-based files) used across modules. Per-component log levels can be overridden from the config file.

### Scene Engine
- `SceneParser` loads JSON scenes, validates structure, and builds state machine objects.
- `state_machine.py` models states, actions, and transitions. Each state can fire MQTT messages, local media commands, or waits.
- `state_executor.py` schedules actions with precise timing, invoking asynchronous callbacks when MQTT feedback arrives.
- `transition_manager.py` evaluates transition rules such as `on_complete`, `on_feedback`, or explicit `goto`, enabling loops, branching, and conditional exits.

### MQTT Stack
- `mqtt_client.py` manages broker connectivity with retry/backoff strategies, heartbeat pings, and connection event callbacks.
- `mqtt_device_registry.py` keeps track of ESP32 device presence and last-seen timestamps.
- `mqtt_feedback_tracker.py` matches published commands with acknowledgements, expiring stale requests.
- `mqtt_message_handler.py` routes incoming MQTT payloads to the scene engine (button presses, device feedback, state overrides).

### Media & Inputs
- `audio_handler.py` wraps Pygame mixer for low-latency playback, supporting start/stop/pause and volume adjustments.
- `video_handler.py` uses an MPV subprocess over IPC, keeping a black frame ready as idle state and restarting the player if it fails.
- `button_handler.py` polls or interrupts a configured GPIO pin with debounce logic to convert physical button presses into scene triggers.

### Observability & Safety
- `system_monitor.py` periodically measures CPU, memory, and disk usage, writes heartbeat logs, and can notify `systemd` once ready.
- `watchdog.py` runs as a companion process to restart the controller if the MQTT connection is lost or health checks fail.
- The Flask + Socket.IO dashboard (under `Web/`) exposes manual controls, scene uploads, and live log streaming.

## MQTT Topic Strategy

Topics follow a `room/device/action` pattern so multiple rooms can coexist without conflicts. Example structure:

```
room_1/
  button
  controller/heartbeat
  devices/
    lights/set
    fogger/set
    motor/set
  feedback/
    lights
    fogger
    motor
```

Scenes publish to `devices/.../set` topics with structured JSON payloads (e.g., `{ "command": "on", "duration": 5000 }`). ESP32 firmware publishes status to `feedback/...`, which the feedback tracker consumes to advance transitions.

## Adding New Capabilities

1. **Extend a scene** – Add new state definitions or transition rules in JSON; `SceneParser` will surface schema errors during load.
2. **Introduce new hardware** – Program an ESP32 sketch that subscribes to a new topic (e.g., `devices/laser/set`) and add actions in your scenes. Register additional validation in `mqtt_device_registry.py` if the device needs custom heartbeat handling.
3. **New transition logic** – Implement logic in `transition_manager.py` (e.g., `wait_for_sensor`) and allow scenes to reference it.
4. **Dashboard tooling** – Modify the Flask blueprint or Socket.IO event handlers under `Web/` to expose new controls or telemetry.

By keeping configuration, MQTT integration, and scene execution modular, new devices or room behaviors can be added with minimal changes to the controller core.
