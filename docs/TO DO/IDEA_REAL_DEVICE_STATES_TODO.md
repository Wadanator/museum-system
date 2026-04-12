# IDEA TODO: Realne stavy zariadeni (Relays/Motory) bez velkeho refaktoru

## Ciel

Dosiahnut, aby dashboard a live view zobrazovali realne HW stavy (ON/OFF/UNKNOWN) podla MQTT feedback/state topicov, nie podla simulacie zo scene timeline.

Kriticky poziadavok:
- 1 sekunda je neprijatelna latencia pre scene-critical kroky synchronizovane s audiom.
- Potvrdenie akcie (ack) musi fungovat v rade desiatok/stoviek milisekund.

## Scope (minimal invasive)

- Nerobit velky architektonicky refaktor scene engine.
- Zachovat existujuci flow start/stop scene.
- Zachovat citanie devices.json na RPi ako katalog zariadeni (id, name, topic, type).
- Doplnit maly runtime stavovy store pre actuator endpointy.
- Nahradit simulaciu v LiveView realnym stavom zo backendu.

## Zachovanie sucasnej vizualizacie (devices.json)

- devices.json zostava primarny zdroj toho, ake zariadenia sa maju vykreslit vo FE.
- Endpoint /api/devices zostava aktivny a bez breaking zmeny kontraktu.
- Nova cast /api/device_states + websocket event doplna iba runtime ON/OFF/UNKNOWN stav pre uz existujuce zariadenia.

## Co zmazat / vypnut

### [DELETE] Simulacny status v LiveView
- Zrusit local simulated mapu stavov zariadeni a timeline-based prepocet.
- Dotknuty subor:
  - museum-dashboard/src/components/Views/LiveView.jsx

### [DELETE] Label "Live Status (Simulacia)"
- Nahradit realnym status panelom via websocket/API.
- Dotknuty subor:
  - museum-dashboard/src/components/Views/LiveView.jsx

## Co pridat

### [ADD] Backend actuator state store (novy modul)
- Novy subor:
  - raspberry_pi/utils/mqtt/mqtt_actuator_state_store.py
- Udrziava:
  - endpoint_topic
  - desired_state
  - confirmed_state
  - state_source (feedback/state/manual)
  - last_update_ts
  - node_id
  - stale/offline flag

### [ADD] API endpoint pre runtime device states
- Pridat route:
  - GET /api/device_states
- Dotknuty subor:
  - raspberry_pi/Web/routes/status.py (alebo novy routes/device_states.py + registracia)

### [ADD] WebSocket event pre incremental update
- Event:
  - device_runtime_state_update
- Dotknute subory:
  - raspberry_pi/Web/dashboard.py
  - raspberry_pi/main.py (wiring callbackov)

### [ADD] Frontend hook na realne stavy
- Novy hook:
  - museum-dashboard/src/hooks/useDeviceRuntimeState.js
- Funkcie:
  - initial fetch /api/device_states
  - subscribe socket event device_runtime_state_update
  - reconnect refresh po F5/reconnect

## Co upravit

### [MODIFY] MQTT message routing
- Spracovat:
  - feedback topicy (<cmd>/feedback)
  - volitelne state topicy (<endpoint>/state)
  - node status topicy (devices/<node>/status)
- Dotknuty subor:
  - raspberry_pi/utils/mqtt/mqtt_message_handler.py

### [MODIFY] Feedback tracker
- Pri feedback OK/ERROR zapisat confirmed stav endpointu do actuator store.
- Dotknuty subor:
  - raspberry_pi/utils/mqtt/mqtt_feedback_tracker.py

### [MODIFY] Node offline policy
- Pri offline/timeout node resetnut jeho endpointy na OFF alebo UNKNOWN (podla safety policy).
- Dotknuty subor:
  - raspberry_pi/utils/mqtt/mqtt_device_registry.py
  - raspberry_pi/main.py (callback orchestration)

### [MODIFY] Frontend LiveView
- Pouzit real runtime states namiesto simulatedDeviceStatus.
- Dotknuty subor:
  - museum-dashboard/src/components/Views/LiveView.jsx

## Casovanie a latencia (nutne oddelit)

### [MODIFY] Config timeoutov
- Rozdelit timeouty na:
  - command_ack_timeout_ms (scene-critical)
  - node_offline_timeout_s (liveness)
- Dotknute subory:
  - raspberry_pi/config/config.ini
  - raspberry_pi/config/config.ini.example
  - raspberry_pi/utils/config_manager.py

Navrh start hodnot:
- command_ack_timeout_ms: 150-300 ms
- node_offline_timeout_s: 3-10 s

## Idealna implementacia bez velkeho refaktoru (kroky)

### Faza 1: Backend truth source
- [ ] Pridat mqtt_actuator_state_store.py.
- [ ] Napojit store na feedback handler.
- [ ] Pridat /api/device_states.
- [ ] Pridat websocket device_runtime_state_update.

### Faza 2: Frontend prechod zo simulacie
- [ ] Pridat useDeviceRuntimeState hook.
- [ ] Refactor LiveView na realne data.
- [ ] Odstranit simulatedDeviceStatus a timeline applyActions pre status panel.

### Faza 3: Offline fail-safe
- [ ] Mapovanie node -> endpoint topics.
- [ ] Pri node offline prepnut endpointy podla policy.
- [ ] Broadcast update do UI.

### Faza 4: Latency hardening
- [ ] Nastavit oddelene ack/offline timeouty.
- [ ] Pridat metriku ack latency (p50/p95/p99) do logu.

## Akceptacne kriteria

- [ ] Po F5 sa zobrazia realne stavy endpointov bez simulacie.
- [ ] Stav ON/OFF sa meni az po realnom feedback/state update.
- [ ] Pri offline node sa endpointy prepnú podla policy (OFF/UNKNOWN) a UI to hned vidi.
- [ ] LiveView uz nepouziva text "Simulacia".
- [ ] Scene-critical ack timeout je v ms, nie 1s globalne.

## Rizika

- Firmware nemusi publikovat per-endpoint state topicy pre vsetky zariadenia.
- Bez state topicov treba fallback logiku len z feedbacku + pending state.

## Rollback plan

- Zachovat feature-flag v backende:
  - USE_RUNTIME_DEVICE_STATE=true/false
- V pripade problemu prepnúť na povodny flow bez mazania novych suborov.
