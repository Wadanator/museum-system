# Museum setup guide (Raspberry Pi)

Detailnejší checklist pre nasadenie backendu v miestnosti.

---

## 1) Prerekvizity

- Raspberry Pi OS (alebo kompatibilný Linux)
- Python 3
- MQTT broker dostupný z Pi
- audio/video stack podľa požiadaviek scén (`pygame`, `mpv`)

---

## 2) Inštalácia projektu

```bash
cd /workspace/museum-system/raspberry_pi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ak nasadzuješ bez venv, použi systémový Python podľa interných pravidiel deploymentu.

---

## 3) Konfigurácia (`config.ini`)

Súbor:
- `raspberry_pi/config/config.ini`

Referenčný príklad:
- `raspberry_pi/config/config.ini.example`

Dôležité sekcie:

## 3.1 MQTT
- `broker_ip`
- `port`
- `device_timeout`
- `feedback_timeout`

## 3.2 Room
- `room_id` (napr. `room1`)

## 3.3 Scenes/Audio/Video
- directories pre scény, audio, video
- video `ipc_socket`
- video `iddle_image`

## 3.4 System
- `web_dashboard_port`
- timing intervaly (`main_loop_sleep`, `scene_processing_sleep`, ...)

## 3.5 Logging
- level, file logging, rotácia, log directory

---

## 4) Príprava dát

- Scény: `raspberry_pi/scenes/<room_id>/...json`
- Audio súbory: adresár podľa configu
- Video súbory: adresár podľa configu

Skontroluj, že názvy súborov v scéne presne sedia.

---

## 5) Lokálne spustenie

```bash
cd /workspace/museum-system/raspberry_pi
source .venv/bin/activate
python3 main.py
```

Po štarte skontroluj:
- MQTT pripojenie,
- dashboard dostupnosť,
- že room reaguje na trigger `roomX/scene -> START`.

---

## 6) Systemd nasadenie

Templates v repozitári:
- `raspberry_pi/services/museum.service.template`
- `raspberry_pi/services/museum-watchdog.service.template`

Odporúčaný postup:
1. skopírovať template do `/etc/systemd/system/` (s vlastným názvom),
2. upraviť cesty (repo, python, user),
3. `systemctl daemon-reload`,
4. `systemctl enable --now <service>`.

---

## 7) Watchdog a diagnostika

- `raspberry_pi/watchdog.py`
- `raspberry_pi/tools/` (monitoring/diagnostics skripty)

Pozor: watchdog skript môže mať environment-dependent cesty – pred produkčným nasadením ich validuj.

---

## 8) Go-live test checklist

1. MQTT broker reachable z Pi.
2. ESP32 status topics sa objavia (`devices/.../status`).
3. Default scene štartuje cez:
   - fyzické tlačidlo,
   - dashboard,
   - MQTT (`roomX/scene` + `START`).
4. `STOP` vypne zariadenia (`roomX/STOP`).
5. Audio/video transitions fungujú podľa scény.
6. Logy sa zapisujú do očakávaného adresára.

---

## 9) Pri zmene room setupu

Pri zmene `room_id` alebo topic prefixov aktualizuj konzistentne:
- `config.ini` (Pi),
- ESP32 `config.cpp` (`BASE_TOPIC_PREFIX`, `CLIENT_ID`),
- scene JSON topicy,
- dokumentáciu v `docs/mqtt_topics.md`.
