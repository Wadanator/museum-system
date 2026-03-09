# Dashboard API & WebSockets

Tento dokument sumarizuje komunikačné rozhranie medzi Raspberry Pi backendom (Flask + Socket.IO) a interaktívnym prezentačným webom múzea (React Dashboard).

---

## 1. WebSockets (Socket.IO)
WebSockets sa používajú na nepretržitý a okamžitý prenos stavu zariadení a logov.
Server beží pod hlavičkou aplikácie v `raspberry_pi/Web/dashboard.py`.

### A) Eventy vysielané zo SERVERA do KLIENTA (Emitters)

*   **`log_history`** 
    *   *Kedy:* Po úspešnom pripojení a autorizácii (alebo na vyžiadanie klientom).
    *   *Payload:* Pole objektov reprezentujúcich posledných 50 logov.
*   **`new_log`**
    *   *Kedy:* Pri každom novom zalogovanom zázname v backende (cez všetky subsystémy).
    *   *Payload:* `{ timestamp, level, module, message }`
*   **`status_update`**
    *   *Kedy:* Na úvod, na vyžiadanie, alebo pri zmene stavu izby (napr. zapnutie scény).
    *   *Payload:* `{ room_id, scene_running: bool, mqtt_connected: bool, uptime: float, log_count: int }`
*   **`stats_update`**
    *   *Kedy:* Na úvod alebo na vyžiadanie pri aktualizácii štatistík pripojení.
    *   *Payload:* Obsahuje dáta o uptime a štruktúru `connected_devices` pre vykreslenie zelenej/červenej guličky pri hardvéri.

### B) Eventy prijímané Klientom do SERVERA (Listeners)

*   **`connect`** - Vyžaduje Basic Auth (`auth.username`, `auth.password` zhodné s configom).
*   **`request_logs`** - Klient požiada o dumpnúte pola histórie logov.
*   **`request_status`** - Klient manuálne polluje aktuálny status systému.
*   **`request_stats`** - Klient si žiada zoznam pripojených hardware zariadení.

---

## 2. HTTP REST API (Flask Routes)

Dashboard okrem WebSocketov umožňuje exekutívne príkazy odosielať cez HTTP REST. 
Definované v `raspberry_pi/Web/routes/`.

*(Predpokladá sa Basic Auth hlavička formátu admin:admin alebo podľa nastavenia u všetkých POST volaní).*

### A) Main Routes
*   `GET /` - Slúži hlavne na overenie chodu servera (alebo render statickej stránky, ak existuje).

### B) System Action Routes (`/api/system/...`)
*   `POST /api/system/shutdown` - Fyzicky vypne Raspberry Pi (volá bash príkaz `sudo shutdown -h now`).
*   `POST /api/system/reboot` - Fyzicky reštartuje Raspberry Pi (volá `controller.system_restart()`).
*   `POST /api/system/restart_service` - Reštartuje SystemD museum službu (`sudo systemctl restart museum`).

### C) API Control Routes (`/api/...`)
*   `GET /api/status` - Vráti aktuálny globálny status systému (stav pripojenia atď.).
*   `GET /api/devices` - Vráti zoznam nakonfigurovaných/pripojených MQTT zariadení do UI.
*   `GET /api/scenes` - Vráti pole dostupných JSON scén ako jednoduché metadáta.
*   `GET /api/scene/<sceneName>` - Vráti kompletný JSON súbor požadovanej scény.
*   `POST /api/scene/<sceneName>` - Uloží (prepíše) údaje scény formátované ako JSON do súboru.
*   `POST /api/run_scene/<sceneName>` - Nasilu preruší aktuálnu scénu a začne prehrávať zvolenú.
*   `POST /api/stop_scene` - Nasilu zastaví aktuálne bežiacu scénu, vymaže audio/video bloky a vyšle MQTT STOP signály na zastavenie HW modulov.

### D) Commands API Routes
*   `GET /api/commands` - Vráti zoznam uložených manuálnych JSON príkazov.
*   `GET /api/command/<commandName>` - Vráti vybraný príkazový JSON konštrukt.
*   `POST /api/command/<commandName>` - Uloží novú/upravenú definíciu MQTT príkazu.
*   `POST /api/run_command/<commandName>` - Spustí definovaný abstraktný príkaz v systéme.
*   `POST /api/mqtt/send` - Manuálny publish MQTT správy (`{ "topic": "...", "message": "..." }`).

### E) Media API Routes (`/api/media/...`)
*   `GET /api/media/<type>` - Vráti všetky súbory daného mediálneho typu (audio/video).
*   `POST /api/media/<type>` - Nahranie (upload) média, kde `file` ide cez MultiPart Form.
*   `DELETE /api/media/<type>/<filename>` - Vymaže daný súbor z úložiska.
*   `POST /api/media/play/<type>` - Spustí prehrávanie zvoleného súboru (`{ "filename": "..." }`).
*   `POST /api/media/stop` - Celosystémovo vyžiada zastavenie všetkých prehrávaných klipov.

### F) System Logs (`/api/logs/...`)
*   `GET /api/logs` - Vráti aktuálny zoznam logov na základe filtrov (level, limit).
*   `POST /api/logs/clear` - Vymaže doterajšiu históriu logov pre zobrazenie v Dashboarde.
*   `GET /api/logs/export` - Exportuje logy vo formáte JSON ako stiahnuteľný súbor.
