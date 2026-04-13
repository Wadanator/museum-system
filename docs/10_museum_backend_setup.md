# Museum setup guide (Raspberry Pi)

Detailnejší checklist pre nasadenie backendu v miestnosti.

---

## 1) Prerekvizity

- Raspberry Pi OS (alebo kompatibilný Linux, odporúča sa boot do konzoly bez GUI).
- Python 3.
- MQTT broker dostupný z Pi (alebo lokálne inštalovaný `mosquitto`).
- audio/video stack podľa požiadaviek scén (`pygame`, `mpv`, `libasound2-dev`, `alsa-utils`).
- **Systémové práva:** Užívateľ musí byť pridaný v skupinách `gpio, audio, video, render, dialout, plugdev` (kritické pre prehrávanie videa bez X11 a prístup k hardvéru).

---

## 2) Inštalácia projektu

### A. Odporúčaný spôsob (Automatická produkčná inštalácia)

V repozitári sa nachádzajú pripravené skripty, ktoré automaticky nastavia OS, nainštalujú závislosti, vytvoria virtuálne prostredie a pripravia `systemd` služby. Skripty si dynamicky odvodia cestu k repozitáru.

```bash
cd cesta/k/museum-system/raspberry_pi
chmod +x install.sh
./install.sh
```

> Poznámka: K dispozícii je aj `./install_offline.sh` pre nasadenie bez prístupu k internetu, ak je OS už predpripravený.

### B. Manuálny spôsob (Len pre lokálny vývoj)

Ak nasadzuješ manuálne, je potrebné vytvoriť Python prostredie s názvom `venv` (bez bodky):

```bash
cd cesta/k/museum-system/raspberry_pi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3) Konfigurácia (config.ini)

- Súbor: `raspberry_pi/config/config.ini`
- Referenčný príklad: `raspberry_pi/config/config.ini.example`

Dôležité sekcie:

**3.1 MQTT**
- `broker_ip`
- `port`
- `device_timeout`
- `feedback_timeout`

**3.2 Room**
- `room_id` (napr. `room1`)

**3.3 Scenes/Audio/Video**
- directories pre scény, audio, video
- `video ipc_socket`
- `video iddle_image`

**3.4 System**
- `web_dashboard_port`
- timing intervaly (`main_loop_sleep`, `scene_processing_sleep`, ...)

**3.5 Logging**
- `log_level`
- `log_directory`
- `max_file_size_mb`
- `backup_count`
- `daily_backup_days`
- `console_colors`
- `file_logging`
- `console_logging`
- `log_format`

---

## 4) Príprava dát

- Scény: `raspberry_pi/scenes/<room_id>/...json`
- Audio súbory: adresár podľa configu
- Video súbory: adresár podľa configu

Skontroluj, že názvy súborov v scéne presne sedia.

---

## 5) Lokálne spustenie (vývoj/testovanie)

```bash
cd cesta/k/museum-system/raspberry_pi
source venv/bin/activate
python3 main.py
```

Po štarte skontroluj:
- MQTT pripojenie
- dashboard dostupnosť (port špecifikovaný v configu)
- že room reaguje na trigger `roomX/scene` -> `START`

---

## 6) Systemd nasadenie (Produkcia)

Ak si v kroku 2 použil skript `install.sh`, služby sa nainštalovali a spustili automaticky.

Ak ich potrebuješ spravovať, volajú sa:
- `museum-system.service`
- `museum-watchdog.service`

Ovládanie:

```bash
sudo systemctl restart museum-system
sudo systemctl status museum-system
```

> Manuálny setup vyžaduje prekopírovanie z `raspberry_pi/services/*.template`, prepísanie premenných `{{PATH}}` a `{{USER}}` a reload systemd daemona.

---

## 7) Watchdog a diagnostika

- `raspberry_pi/watchdog.py`
- `raspberry_pi/tools/` (monitoring/diagnostics skripty)

Hardware watchdog setup (OS level):
- Pozri `docs/13_rpi_hardware_watchdog_setup.md`.

> Pozor: watchdog skript môže mať environment-dependent cesty – pred produkčným nasadením ich validuj.

---

## 8) Stabilization test scripts (P0-2 / P0-3)

Tieto skripty sú určené na runtime validáciu bez internetu na RPi:

- `raspberry_pi/tests/test_main_scene_state.py`
	- Offline P0-2 kontrola (bez pytest): centralizované transitions + idempotentný STOP.
- `raspberry_pi/tests/manual_scene_service_stress.py`
	- API stress pre štart/stop scény.
- `raspberry_pi/tests/run_scene_stress_scenev01.sh`
	- Preset launcher pre `SceneV01.json`.
- `raspberry_pi/tests/manual_web_retry_p03_test.sh`
	- P0-3 runtime test: vynútený bind conflict na porte 5000 + overenie recovery.

Overené (2026-04-01):
- P0-2 CLOSED + validated.
- P0-3 CLOSED + validated.

---

## 9) Go-live test checklist

- MQTT broker reachable z Pi.
- ESP32 status topics sa objavia (`devices/.../status`).
- Default scene štartuje cez: fyzické tlačidlo, dashboard, MQTT (`roomX/scene` + `START`).
- `STOP` vypne zariadenia (`roomX/STOP`).
- Audio/video transitions fungujú podľa scény.
- Logy sa zapisujú do očakávaného adresára.

---

## 10) Pri zmene room setupu

Pri zmene `room_id` alebo topic prefixov aktualizuj konzistentne:
- `config.ini` (Pi)
- ESP32 `config.cpp` (`BASE_TOPIC_PREFIX`, `CLIENT_ID`)
- scene JSON topicy
- dokumentáciu v [docs/04_mqtt_protocol.md](docs/04_mqtt_protocol.md)