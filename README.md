# Museum System

Kompletný riadiaci systém pre interaktívne miestnosti v múzeu.

Systém je rozdelený na:
- **Raspberry Pi backend** (`raspberry_pi/`) – orchestrácia scén, audio/video, dashboard API, health monitoring.
- **ESP32 firmware** (`esp32/devices/wifi/`) – vykonávanie fyzických príkazov cez MQTT.
- **UI/editor projekty** (`museum-dashboard/`, `SceneGen/`) – vývoj dashboardu a autoring scén.

---

## 1) Čo je v repozitári aktuálne produkčne použité

### Raspberry Pi controller
- Entry point: `raspberry_pi/main.py` (`MuseumController`).
- Core runtime: `raspberry_pi/utils/`.
- Web dashboard server: `raspberry_pi/Web/`.

### ESP32 zariadenia (wifi)
- `esp32_mqtt_button` – bezdrôtový trigger scény.
- `esp32_mqtt_controller_MOTORS` – ovládanie 2 motorov.
- `esp32_mqtt_controller_RELAY` – relé výstupy + efektové skupiny.

### Dáta/scény
- Scény: `raspberry_pi/scenes/<room_id>/*.json`
- Room config: `raspberry_pi/config/config.ini`

---

## 2) Rýchly runtime flow

1. `MuseumController` načíta config, spustí služby cez `ServiceContainer`.
2. MQTT klient sa pripojí na broker a subscribne room topics.
3. Trigger (`button`/MQTT/dashboard) spustí scénu.
4. `SceneParser` + `StateMachine` + `StateExecutor` vykonávajú `onEnter/timeline/onExit` akcie.
5. `TransitionManager` rozhoduje o prechodoch (`timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always`).
6. Po dohraní scény backend pošle `roomX/STOP`.

---

## 3) MQTT model (aktuálny podľa kódu)

### Scény
- `roomX/scene` + `START` → default scéna (`json_file_name` z configu).
- `roomX/start_scene` + `scene_name.json` → spustenie konkrétneho súboru.

### Device status
- `devices/<client_id>/status` (retained, typicky `online`/`offline`).

### Feedback
- `<command_topic>/feedback` (podľa zariadenia: `OK`, `ERROR`, `ACTIVE`, `INACTIVE`).

### Room1 príkazy (reálne používané ESP32 firmvérmi v repozitári)
- Motory: `room1/motor1`, `room1/motor2`, `room1/STOP`
- Relé/effects: `room1/<device_name>`, `room1/effects/<group>`, `room1/STOP`
- Trigger button publish: `room1/scene` -> `START`

---

## 4) Spustenie backendu (lokálne)

```bash
cd raspberry_pi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Dashboard je na porte z `[System] web_dashboard_port`.

---

## 5) Dokumentácia

- `docs/architecture.md` – komponenty + runtime väzby.
- `docs/mqtt_topics.md` – MQTT topics/payloady podľa implementácie.
- `docs/audio_playing_tutorial.md` – audio commandy v scénach.
- `docs/video_player_tutorial.md` – video commandy v scénach.
- `docs/museum_setup_guide.md` – setup/deploy check-list.

---

## 6) Dôležitá poznámka k dokumentácii

Dokumentácia je písaná **podľa aktuálneho kódu**, nie podľa starých návrhov.
Ak pridáš nový topic alebo command, uprav:
1. implementáciu,
2. testovaciu scénu,
3. príslušný markdown v `docs/`.
