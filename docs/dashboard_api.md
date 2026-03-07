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
*   `POST /api/system/restart` - Fyzicky reštartuje Raspberry Pi.
*   `POST /api/system/restart_service` - Reštartuje SystemD museum službu (`sudo systemctl restart museum`).

### C) API Control Routes (`/api/...`)
*   `GET /api/status` - Vráti aktuálny globálny status systému vo formáte JSON.
*   `GET /api/scenes` - Vráti pole dostupných JSON scén zo zložky scenes zosumarizovaných do metadát.
*   `POST /api/scene/start`
    *   *Payload:* `{ "scene_id": "mojascena.json" }`
    *   *Akcia:* Nasilu preruší aktuálnu scénu a začne prehrávať zvolenú.
*   `POST /api/scene/stop` - Nasilu zastaví aktuálne bežiacu scénu, vymaže audio/video bloky a vyšle MQTT STOP signály na zastavenie HW modulov.
