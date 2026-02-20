# `raspberry_pi/utils` – stručný prehľad

## Core flow

1. `state_machine.py` načíta a drží aktuálny stav scény.
2. `scene_parser.py` riadi štart/loop/stop scény.
3. `state_executor.py` vykonáva akcie (`mqtt`, `audio`, `video`).
4. `transition_manager.py` vyhodnocuje prechody.

## Podporné moduly

- `audio_handler.py` – prehrávanie zvuku cez pygame.
- `video_handler.py` – MPV IPC prehrávanie videa.
- `button_handler.py` – fyzické tlačidlo.
- `config_manager.py` – načítanie `config.ini`.
- `system_monitor.py` – health check logika.
- `schema_validator.py` – JSON schema validácia scén.
- `logging_setup.py` – centralizované logovanie.

## MQTT

Detail je v `utils/mqtt/info.md`.
