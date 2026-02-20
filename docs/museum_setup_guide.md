# Museum setup guide (Raspberry Pi)

## 1) Inštalácia

```bash
cd /workspace/museum-system/raspberry_pi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Konfigurácia

Skontroluj/naplň `raspberry_pi/config/config.ini`:
- `[MQTT]` broker IP/port
- `[Room] room_id` (napr. `room1`)
- `[Scenes] directory`
- `[Audio] directory`
- `[Video] directory`, `ipc_socket`, `iddle_image`
- `[System] web_dashboard_port`

Príklad defaultu je v `config.ini.example`.

## 3) Štruktúra dát

- Scény: `raspberry_pi/scenes/<room_id>/*.json`
- Audio: `<audio_dir>`
- Video: `<video_dir>`
- Logy: podľa `[Logging] log_directory`

## 4) Lokálne spustenie

```bash
cd /workspace/museum-system/raspberry_pi
python3 main.py
```

## 5) Systemd služby

Repo obsahuje templates:
- `raspberry_pi/services/museum.service.template`
- `raspberry_pi/services/museum-watchdog.service.template`

Použi ich ako základ pre produkčné jednotky (cesty uprav podľa deploymentu).

## 6) Watchdog

`watchdog.py` vie dohliadať na proces + logiku reštartu. Ak nasadzuješ watchdog service, uisti sa, že cesty v skripte zodpovedajú cieľovému systému.
