# Museum System Workspace Instructions

## Project Context

This repository contains three runtime layers connected through MQTT:

- Raspberry Pi backend in `raspberry_pi/` (scene orchestration, media playback, watchdog, web API)
- ESP32 firmware in `esp32/` (hardware control and feedback publishing)
- React tooling UIs in `museum-dashboard/` and `SceneGen/`

Use strict typing, fail-fast guard clauses, and deterministic behavior for all state transitions.

## Build and Test Commands

Run commands from the relevant project folder.

- `museum-dashboard/`: `npm install`, `npm run dev`, `npm run build`, `npm run lint`, `npm run preview`
- `SceneGen/`: `npm install`, `npm run dev`, `npm run build`, `npm run preview`
- `raspberry_pi/` production setup: `./install.sh`
- `raspberry_pi/` local run: `python3 -m venv venv`, `source venv/bin/activate`, `pip install -r requirements.txt`, `python3 main.py`
- `raspberry_pi/` tests (current baseline): `pytest tests/test_schema_validator.py`

ESP32 firmware is built and uploaded from Arduino IDE project folders under `esp32/devices/wifi/ArduinoIDE/`.

## Architecture Boundaries

- Keep transport/routing logic separate from business logic. MQTT and HTTP handlers call services only.
- Scene runtime boundary:
  - scene loading/validation in `raspberry_pi/utils/state_machine.py`
  - execution in `raspberry_pi/utils/state_executor.py`
  - transitions in `raspberry_pi/utils/transition_manager.py`
- Web/API boundary in `raspberry_pi/Web/`; hardware behavior boundary in `esp32/devices/wifi/`
- Do not bypass the transition manager lock model or access transition queues directly.

## Project Conventions

### Cross-project

- No magic values. Use constants, enums, or config.
- Prefer immutable updates instead of in-place mutation.
- Comments explain why, not what.

### Python (Raspberry Pi)

- Public methods must use complete type hints.
- Never use bare `except:`; catch specific exceptions and log with `exc_info=True`.
- Use `get_logger(...)` from `raspberry_pi/utils/logging_setup.py`; keep logger names in `museum.*` namespace.
- Use `pathlib.Path` and project-relative/config-derived paths, not hardcoded absolute paths.
- Keep files cohesive and generally around 300 lines when possible.

### React (museum-dashboard and SceneGen)

- One component per file; component filenames in PascalCase.
- Extract complex state and side effects into custom hooks.
- Include all dependencies in `useEffect` arrays.
- Use functional state updates and avoid direct mutation.
- Prefer early returns over deeply nested ternaries.

### C++ (ESP32)

- Never use `delay()` in `loop()`; use non-blocking `millis()`-driven state logic.
- Avoid Arduino `String`; prefer fixed-width types and safer string/buffer patterns.
- Ensure WiFi/MQTT reconnection is non-blocking.
- Every MQTT command must publish feedback (`OK` or error) to feedback topics.

## Security and Reliability

- Never commit secrets, credentials, tokens, or live `config.ini`.
- Validate all external inputs (HTTP, MQTT, file paths, payloads).
- Enforce MQTT topic allowlist for send endpoints (`room<n>/` and `devices/` prefixes only).
- Keep the main scene loop resilient; errors must be logged and handled without controller crash.

Known production risks to prioritize fixing:

- Hardcoded auth values in `raspberry_pi/Web/config.py`
- Hardcoded absolute paths in `raspberry_pi/watchdog.py`
- Basic auth over plain HTTP if exposed beyond localhost

## Testing Expectations

- Use TDD where practical: failing test, minimal implementation, refactor.
- Target strong coverage for critical runtime modules:
  - `raspberry_pi/utils/scene_parser.py`
  - `raspberry_pi/utils/state_machine.py`
  - `raspberry_pi/utils/transition_manager.py`
  - `raspberry_pi/utils/state_executor.py`
- Mock hardware and system integrations in tests (`RPi.GPIO`, `pygame`, `subprocess`, MQTT client, IPC sockets).
- Include transition-path tests for `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, and `always`.

## Critical Files

Treat these files as high-risk and review carefully before edits:

- `raspberry_pi/utils/transition_manager.py`
- `raspberry_pi/utils/state_machine.py`
- `raspberry_pi/utils/logging_setup.py`
- `raspberry_pi/Web/auth.py`
- `raspberry_pi/config/config.ini`

## Documentation Links (Link, Do Not Duplicate)

- Architecture: `docs/02_system_architecture.md`
- File map: `docs/03_file_structure.md`
- MQTT protocol: `docs/04_mqtt_protocol.md`
- Scene/state model: `docs/06_scene_state_machine.md`
- Audio/video behavior: `docs/07_audio_engine.md`, `docs/08_video_engine.md`
- Dashboard API: `docs/09_dashboard_api.md`
- Backend setup: `docs/10_museum_backend_setup.md`
- ESP32 setup and hardware reference: `docs/11_esp32_firmware_setup.md`, `docs/05_esp32_hardware_reference.md`
- Physical deployment: `docs/12_physical_installation.md`

## Related Instruction Files

Follow specialized instruction files instead of duplicating their content here:

- Generic review rules: `.github/instructions/code-review-generic.instructions.md`
- Debian administration guidance: `.github/instructions/debian-linux.instructions.md`
- C++ symbol tooling workflow: `.github/instructions/cpp-language-service-tools.instructions.md`
- Power Apps code apps guidance: `.github/instructions/power-apps-code-apps.instructions.md`
- Power BI custom visuals guidance: `.github/instructions/power-bi-custom-visuals-development.instructions.md`