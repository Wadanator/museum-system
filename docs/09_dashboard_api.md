# Dashboard API & Socket.IO

Tento dokument popisuje presné HTTP a Socket.IO rozhranie, ktoré vystavuje backend v `raspberry_pi/Web/`.

Web runtime sa spúšťa z `raspberry_pi/Web/app.py`. Samotný dashboard objekt je v `raspberry_pi/Web/dashboard.py`.

---

## 1. Web runtime

`start_web_dashboard()` v `raspberry_pi/Web/app.py`:

- vytvorí Flask aplikáciu,
- nastaví `SECRET_KEY` z `raspberry_pi/Web/config.py`,
- vytvorí `SocketIO` s `async_mode='threading'`, `ping_timeout=60`, `ping_interval=25` a `transports=['websocket']`,
- zaregistruje `main_bp`, API blueprints a system blueprints,
- spustí server v daemon threade na `0.0.0.0`.

Ak `socketio.run(...)` spadne, wrapper ho vráti späť do slučky a skúsi znova po 10 sekundách.

---

## 2. Socket.IO

Socket.IO eventy sú definované v `raspberry_pi/Web/dashboard.py`.

### 2.1 Autentifikácia pripojenia

`connect` vyžaduje Basic Auth s údajmi z `raspberry_pi/Web/config.py`:

- `USERNAME = 'admin'`
- `PASSWORD = 'admin'`

Dashboard pri connecte skúša tieto formy v tomto poradí:

- `request.authorization`
- `auth` payload s poľom `token`, ak začína `Basic `
- HTTP hlavičku `Authorization: Basic ...`

Ak sa autentifikácia nepodarí, pripojenie sa odmietne.

### 2.2 Eventy zo servera ku klientovi

Server emituje tieto udalosti:

- `log_history` - posledných 50 logov pri connecte, alebo posledných 250 pri `request_logs`
- `new_log` - každý nový log entry z `WebLogHandler`
- `status_update` - aktuálny stav systému
- `stats_update` - štatistiky dashboardu
- `device_runtime_state_update` - priebežný snapshot runtime stavov aktorov
- `logs_cleared` - po vymazaní log buffera cez HTTP route
- `scene_progress` - priebežný stav aktívnej scény, emitovaný z `main.py` pri zmene stavu

### 2.3 Eventy od klienta na server

Klient môže poslať:

- `request_logs`
- `request_status`
- `request_stats`

### 2.4 Formát payloadov

`new_log` používa presne tento formát:

```json
{
  "timestamp": "2026-04-13 12:34:56.789",
  "level": "INFO",
  "module": "main",
  "message": "..."
}
```

Ak je prítomná výnimka, pridá sa aj pole `exception`.

`status_update` používa:

```json
{
  "room_id": "room1",
  "scene_running": true,
  "mqtt_connected": true,
  "uptime": 123.45,
  "log_count": 87
}
```

`stats_update` posiela celý `dashboard.stats` slovník:

- `total_scenes_played`
- `scene_play_counts`
- `total_uptime`
- `last_start_time`
- `connected_devices`

`device_runtime_state_update` je snapshot z `MQTTActuatorStateStore`.

---

## 3. HTTP routes

Všetky API routes používajú `@requires_auth` z `raspberry_pi/Web/auth.py`, teda Basic Auth s rovnakými credentials ako Socket.IO.

### 3.1 Main route

`raspberry_pi/Web/routes/main.py`:

- `GET /` - servíruje React SPA z `dist/`
- `GET /<path>` - fallback pre SPA routing, ak súbor existuje v `dist/`, servuje ho, inak vráti `index.html`

### 3.2 Status, logs a monitoring

`raspberry_pi/Web/routes/status.py`:

- `GET /api/status` - vracia `room_id`, `scene_running`, `mqtt_connected`, `uptime`, `log_count`
- `GET /api/scene/progress` - deprecated fallback route; ak je `scene_parser` dostupný, route sa pokúsi zavolať `controller.scene_parser.get_progress_info()`. Ak metóda neexistuje alebo zlyhá, route vráti `500`.
- `GET /api/stats` - vracia `dashboard.stats`
- `GET /api/logs` - vracia logy z buffera, s voliteľnými query parametrami `level` a `limit`
- `POST /api/logs/clear` - vymaže in-memory log buffer a broadcastne `logs_cleared`
- `GET /api/logs/export` - exportuje log buffer ako JSON download

`dashboard.log_buffer` sa plní cez `WebLogHandler` a pri connecte sa odosiela jeho časť ako `log_history`.

### 3.3 Scene routes

`raspberry_pi/Web/routes/scenes.py`:

- `GET /api/scenes` - zoznam `.json` scén v `scenes/<room_id>/`
- `GET /api/scene/<scene_name>` - načíta konkrétnu scénu
- `POST /api/scene/<scene_name>` - uloží scénu ako JSON
- `POST /api/run_scene/<scene_name>` - spustí scénu cez `controller.start_scene_by_name(...)`
- `POST /api/stop_scene` - zastaví bežiacu scénu cez `controller.stop_scene()`
- `GET /api/config/main_scene` - vráti `controller.json_file_name`

`run_scene` vracia `400`, ak controller štart scény odmietne, typicky keď už scéna beží.

`stop_scene` po zastavení vždy broadcastne nový `status_update`.

### 3.4 Commands routes

`raspberry_pi/Web/routes/commands.py`:

- `GET /api/devices` - načíta room devices config z `config/rooms/<room_id>/devices.json`
- `POST /api/devices` - uloží room devices config
- `POST /api/mqtt/send` - okamžitý MQTT publish z JSON payloadu `{ "topic": "...", "message": "..." }`
- `GET /api/commands` - zoznam command súborov v `scenes/<room_id>/commands/`
- `GET /api/command/<command_name>` - načíta konkrétny command JSON
- `POST /api/command/<command_name>` - uloží command JSON ako zoznam akcií
- `POST /api/run_command/<command_name>` - vykoná command súbor a publikuje jeho akcie do MQTT

`POST /api/devices` očakáva objekt a vyžaduje aspoň jednu z kľúčových skupín `motors`, `relays` alebo `lights`.

`GET /api/devices` má legacy fallback: ak nový room config chýba, pokúsi sa migráciu zo starého `scenes/<room_id>/devices.json`.

### 3.5 Device runtime states

`raspberry_pi/Web/routes/device_states.py`:

- `GET /api/device_states` - vracia runtime ON/OFF/UNKNOWN stav všetkých tracked actuator endpointov z `MQTTActuatorStateStore`

Ak store ešte nie je inicializovaný, route vráti prázdne pole.

### 3.6 Media routes

`raspberry_pi/Web/routes/media.py`:

- `GET /api/media/audio` - zoznam audio súborov
- `POST /api/media/audio` - upload audio súboru cez multipart `file`
- `DELETE /api/media/audio/<filename>` - zmaže audio súbor
- `GET /api/media/video` - zoznam video súborov
- `POST /api/media/video` - upload video súboru cez multipart `file`
- `DELETE /api/media/video/<filename>` - zmaže video súbor
- `POST /api/media/play/audio` - okamžite prehrá audio súbor cez `controller.audio_handler.play_audio(...)`
- `POST /api/media/play/video` - okamžite prehrá video súbor cez `controller.video_handler.play_video(...)`
- `POST /api/media/stop` - zastaví audio aj video prehrávanie

Povolené prípony sú:

- audio: `.mp3`, `.wav`, `.ogg`, `.flac`
- video: `.mp4`, `.avi`, `.mov`, `.mkv`, `.png`, `.jpg`, `.jpeg`

Ukladanie a čítanie médií ide do `scenes/<room_id>/<audio_dir|video_dir>/` podľa `config.ini`.

### 3.7 System routes

`raspberry_pi/Web/routes/system.py`:

- `POST /api/system/restart_service` - reštartuje Python službu, ak controller má `service_restart`
- `POST /api/system/reboot` - reštartuje celé zariadenie, ak controller má `system_restart`
- `POST /api/system/shutdown` - vypne celé zariadenie, ak controller má `system_shutdown`

Ak controller nemá podporovaný handler, route vráti `500` s `Not supported`.

---

## 4. Typické tokové sekvencie

### 4.1 Pripojenie dashboardu

1. Klient sa pripojí cez Socket.IO.
2. Server skontroluje Basic Auth.
3. Server odošle `log_history`, `stats_update` a `status_update` pre konkrétne `sid`.

### 4.2 Štart scény z webu

1. Klient zavolá `POST /api/run_scene/<scene_name>`.
2. Route zavolá `controller.start_scene_by_name(...)`.
3. Ak je štart úspešný, controller prepne stav scény a dashboard znovu pošle `status_update`.

### 4.3 Zastavenie scény z webu

1. Klient zavolá `POST /api/stop_scene`.
2. Route zavolá `controller.stop_scene()`.
3. Dashboard broadcastne nový `status_update`.
4. Controller odošle stop signály na audio/video a ďalšie naviazané runtime komponenty.

---

## 5. Poznámky k presnosti

- `main.py` spúšťa dashboard v daemon threade, nie ako samostatný proces.
- `WebLogHandler` generuje log entry s `timestamp`, `level`, `module`, `message` a voliteľným `exception`.
- `scene/progress` je v kóde ponechaný ako fallback route, ale dokumentácia by ho mala považovať za deprecated.
- `status_update` a `stats_update` majú dve cesty: Socket.IO emit pri connecte a broadcast pri runtime zmenách.
