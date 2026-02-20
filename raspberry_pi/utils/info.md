# `raspberry_pi/utils` – detailný prehľad

Tento priečinok drží core runtime moduly backendu.

---

## 1) Scene execution stack

- `state_machine.py`
  - načítanie JSON scény
  - schema + logická validácia
  - držanie current state, scene timerov, state history

- `scene_parser.py`
  - koordinuje start/process/stop scény
  - registruje audio/video end eventy
  - posiela MQTT eventy do transition managera
  - dynamic preload audio (SFX cache)

- `state_executor.py`
  - vykonávanie akcií podľa typu (`mqtt`, `audio`, `video`)
  - obsluha `onEnter`, `timeline`, `onExit`

- `transition_manager.py`
  - vyhodnocuje transitions v stave
  - typy: `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always`

---

## 2) Media moduly

- `audio_handler.py`
  - `pygame` mixer init/retry
  - stream + SFX kanály
  - command parser (`PLAY`, `STOP`, `PAUSE`, `RESUME`, `VOLUME`)

- `video_handler.py`
  - mpv process + IPC commandy
  - monitoring zdravia procesu
  - restart mechanizmy pri timeoutoch/chybách

---

## 3) System/infra moduly

- `config_manager.py` – načítanie a normalizácia configu.
- `logging_setup.py` – central logging setup + per-module levely.
- `system_monitor.py` – periodické health checky.
- `button_handler.py` – HW tlačidlo (polling/interrupt podľa nastavenia).
- `service_container.py` – DI-like skladanie služieb.
- `bootstrap.py` – bootstrap logging a štart pipeline.
- `schema_validator.py` – JSON schema scény.

---

## 4) MQTT balík

MQTT detaily sú v:
- `utils/mqtt/info.md`
