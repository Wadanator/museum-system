# TODO: Autoritatívne MQTT stavové hlásenia pre Live view

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short date or note if useful, and do not leave completed work only in chat or
git history.

Whole-file completion rule: when every active item in this file is either
`DONE`, `SKIPPED`, or `SUPERSEDED`, rename the file with `_DONE` before `.md`
so the folder clearly shows that this plan is closed.

## Scope decision - 2026-06-07

External review accepted: for this museum-scale system, the high-value part is
authoritative retained state reporting plus offline/stale handling. Implement
only Phase 1 and Phase 2 for the current feature scope.

Keep these as out of current scope unless production evidence proves they are
needed:

- Phase 3 `command_id` matching,
- Phase 4 QoS 1 changes,
- Phase 5 new `/set` / `/ack` topic schema,
- `seq`, `boot_id`, or `session_id` in normal state payloads.

The critical rule stays mandatory: retained state is only the last known output
state. If the owning ESP32 node is offline, Live view must show the output as
`STALE/UNKNOWN`, not as the retained `ON` / `OFF` value.

## Final implementation decision - 2026-06-12

The system is still in development, so this does not need a production-style
live migration path. Even so, do not redesign the whole MQTT namespace. The
ideal low-complexity solution is:

- keep the existing command topics, for example `room1/light/1 = ON`,
- keep `<command_topic>/feedback` as command ACK/logging,
- add retained `<command_topic>/state` as the authoritative Live view source,
- implement Phase 1 and Phase 2 as one clean development rework if convenient,
- keep Phase 3-5 deferred unless real production evidence proves they are
  needed.

Keeping the current command topics is not mainly about live compatibility; it
is about avoiding churn with no useful payoff. Scenes, dashboard controls, and
ESP32 firmware already understand those topics. Adding `/state` gives the
missing truth channel without introducing `/set`, `/ack`, `command_id`, QoS 1,
`seq`, `boot_id`, or `session_id`.

`node_id` must be explicit. Use the same stable identifier the ESP32 publishes
in `devices/<node_id>/status`, for example:

```cpp
#define CLIENT_ID "Room1_Relays_Ctrl"
```

That same value belongs in `devices.json` and, when JSON payloads are used, in
the state payload. If a state payload is plain text (`ON`, `OFF`, `ACTIVE`,
`INACTIVE`) or omits `node_id`, the backend should derive `node_id` from the
`topic -> node_id` mapping loaded from `devices.json`.

For Live view simplicity, keep the frontend-facing `confirmed_state` field, but
make state reports its authoritative source. Backend should accept
`ACTIVE`/`INACTIVE` for effect state topics and normalize them to ON-like /
OFF-like values for the existing dashboard state model. Feedback `OK` can clear
or explain pending command status, but it should not be the final truth after
state reporting exists.

Config timeout mapping:

- `command_ack_timeout_ms` is the feedback/ACK budget after a backend command.
  Current code wires this into `MQTTFeedbackTracker` by converting milliseconds
  to seconds. It controls how long a command can stay pending before the backend
  logs a feedback timeout.
- Legacy `feedback_timeout` may still exist in example docs/configs, but the
  current `ServiceContainer` uses `command_ack_timeout_ms` for feedback
  tracking. Do not build the new state-reporting logic around
  `feedback_timeout`.
- `device_timeout` is the current runtime threshold used by
  `MQTTDeviceRegistry` to mark `devices/<node_id>/status` offline when a device
  has not refreshed status recently.
- `node_offline_timeout_s` is currently parsed from config but is not wired into
  runtime behavior. For this rework, prefer one node-availability source unless
  there is a real need for a separate, faster actuator-stale threshold. If kept,
  document and wire it explicitly; otherwise treat `device_timeout` as the
  source that drives offline -> `STALE/UNKNOWN`.

## Current code compatibility guardrails - 2026-06-12

These points are mandatory for compatibility with the current backend and
dashboard code:

- Frontend device lookup is keyed by the original command topic from
  `devices.json`, for example `room1/light/1`. Backend must strip `/state` and
  emit/store the snapshot under `topic = "room1/light/1"`, not under
  `topic = "room1/light/1/state"`.
- `MQTTMessageHandler` must route `/state` reports before forwarding unmatched
  MQTT messages to `scene_parser.register_mqtt_event(...)`. State reports are
  runtime telemetry, not scene transition events.
- `MQTTActuatorStateStore` must be bootstrapped from
  `config/rooms/<room_id>/devices.json` before retained MQTT replay is trusted.
  Runtime snapshot and `runtimeSummary` only know about entries that exist in
  the store.
- Every configured actuator should start as `stale=true`,
  `confirmed_state=UNKNOWN`, with `node_id` loaded from `devices.json`.
- `update_desired(...)` must not clear `stale`. A backend command only means
  "wanted state", not "hardware is fresh/online".
- Feedback `OK` / `ACTIVE` / `INACTIVE` must not be allowed to clear `stale`
  once retained `/state` reporting exists. Feedback may resolve pending/logging;
  only a valid state report from an online node should make the Live view fresh.
- `force_all_off(...)` must not mark offline nodes as fresh. For an offline
  node it may set `desired_state=OFF`, but the displayed state should stay
  `STALE/UNKNOWN` until the node returns online and reports state.
- Current React code already handles `entry.stale` as `UNKNOWN`/`STALE`. Do not
  redesign the frontend state model unless there is a concrete UI bug. The main
  frontend requirement is receiving snapshots under the original device topics.
- The dashboard devices config editor is raw JSON and will preserve added
  `node_id` fields. If a device has no `node_id`, backend may still update that
  topic from `/state`, but offline-to-stale mapping for that device is not
  reliable and should log a warning.

## Cieľ

Live view má v budúcnosti zobrazovať stav podľa toho, čo hlási ESP32 po nastavení
vlastného GPIO/runtime stavu, nie iba podľa toho, čo backend naposledy odoslal a spároval
cez feedback.

Za "pravdu" sa v tomto pláne považuje stav, ktorý si ESP32 nastavilo vo firmvéri
po vykonaní príkazu. Hardvérové senzory, spätný kontakt relé alebo fyzické overenie
motora sa tu neriešia.

## Aktuálny stav

Backend dnes používa tieto vrstvy:

- `mqtt_client.publish(...)` odošle príkaz.
- `MQTTFeedbackTracker` očakáva odpoveď na `<command_topic>/feedback`.
- `MQTTActuatorStateStore` ukladá `desired_state` a `confirmed_state`.
- Web dashboard cez `device_runtime_state_update` zobrazuje `confirmed_state`.
- ESP32 publikuje `OK` / `ERROR` pre bežné príkazy a `ACTIVE` / `INACTIVE` pre efekty.
- ESP32 publikuje `devices/<client_id>/status = online/offline`.

Toto je dobré na potvrdenie príkazu odoslaného backendom, ale nie je to úplný zdroj
pravdy pre Live view.

## Problémy aktuálneho modelu

1. Feedback je viazaný na príkaz, ktorý backend očakáva.
   Ak ESP32 pošle feedback na príkaz, ktorý backend neodoslal, tracker ho berie ako
   nespárovaný.

2. Pri vypnutí ESP32 existuje `status = offline`, ale výstupy nemusia byť spoľahlivo
   označené ako `UNKNOWN`, ak nie sú previazané na `node_id`.

3. `confirmed_state` je odvodený z feedbacku, nie zo samostatného stavového reportu
   zariadenia.

4. Pri škálovaní na ďalšie relé/topicy treba zachovať jednoduchý proces:
   doplniť `DEVICES[]` vo firmvéri, doplniť `devices.json` na RPi a ostatné sa má
   odvodiť automaticky.

## Cieľová architektúra

Oddeliť tri typy MQTT správ:

```text
command  = príkaz smerom z backendu na ESP32
ack      = odpoveď ESP32 na konkrétny príkaz
state    = aktuálny stav výstupu hlásený ESP32
```

Feedback tracker zostáva, ale Live view sa má primárne opierať o `state` správy.

## MQTT kontrakt

Zachovať existujúce command topicy kvôli spätnej kompatibilite:

```text
room1/light/1 = ON
room1/motor1 = ON:70:L:1000
room1/effects/group1 = ON
```

Zachovať existujúci feedback topic ako ACK príkazu:

```text
room1/light/1/feedback = OK
room1/light/1/feedback = ERROR
room1/effects/group1/feedback = ACTIVE
room1/effects/group1/feedback = INACTIVE
```

Doplniť nový stavový topic:

```text
room1/light/1/state
room1/motor1/state
room1/effects/group1/state
```

Stavové správy majú byť `retain=true`, aby backend po reštarte okamžite získal posledný
známy stav. Command a feedback správy nemajú byť retained.

Odporúčaný payload pre state:

```json
{
  "state": "ON",
  "node_id": "Room1_Relays_Ctrl",
  "source": "command",
  "ts_ms": 123456
}
```

`seq`, `boot_id` a `session_id` nie sú súčasťou MVP. Doplniť ich až vtedy, ak sa v
praxi ukáže reálny problém s duplicitnými správami alebo starým retained stavom po
reštarte zariadení.

Pre jednoduché výstupy je možné podporovať aj spätnú kompatibilitu s plain payloadom:

```text
ON
OFF
ACTIVE
INACTIVE
```

Backend by mal vedieť spracovať oba tvary.

### Dôležité pravidlá kontraktu

- Command topicy a feedback topicy nesmú byť retained.
- State topicy majú byť retained, ale iba ako posledný známy stav. Ak je uzol offline,
  backend ich nesmie zobrazovať ako aktuálnu pravdu.
- Sufix `/state` je rezervovaný iba pre stavové hlásenia. ESP32 callback musí ignorovať
  topic-y obsahujúce `/state`, rovnako ako dnes ignoruje `/feedback` a `/status`.
- Ignorovanie `/state` má byť v ESP32 callbacku ešte pred kopírovaním/parsingom payloadu,
  pretože JSON state payload môže byť dlhší ako krátke command payloady.
- Toto je dôležité hlavne pri relé efektoch, lebo relé firmware subscribe-uje
  `room1/effects/#`. Bez ignorovania `/state` by mohlo ESP32 prijať aj vlastný publish
  `room1/effects/group1/state` a zbytočne ho spracúvať ako command.

## ESP32 zmeny

### Relé firmware

Ak sa budú používať obe vetvy firmvéru, rovnakú logiku treba aplikovať na Wi-Fi aj LAN
relé variant, aby sa backend nesprával rozdielne podľa typu pripojenia.

Doplniť funkcie:

```cpp
publishDeviceState(deviceIndex, source, force)
publishAllDeviceStates(source)
publishEffectState(groupName, state, source)
```

Použitie:

- po `setDevice(...)` publikovať `<topic>/state` iba pri normálnom command-e, auto-off,
  `STOP` alebo ručnej zmene, nie pri každom internom prepnutí efektu,
- po `turnOffAllDevices()` publikovať `OFF` pre všetky výstupy,
- po auto-off udalosti publikovať `OFF`,
- po MQTT reconnecte publikovať všetky aktuálne stavy,
- state publikovať retained,
- feedback publikovať non-retained.

Pri efektoch:

- `room1/effects/group1/state = ACTIVE` po spustení efektu,
- `room1/effects/group1/state = INACTIVE` po zastavení efektu,
- ak Live view nemá zobrazovať každý interný blink, nepulzovať state pre každý toggle,
  ale ukazovať logický stav efektu ako `ACTIVE`.
- Backend má pre existujúci dashboard model interpretovať `ACTIVE` ako ON-like
  a `INACTIVE` ako OFF-like. Netreba kvôli tomu zavádzať nový frontend stavový
  model; dôležitý je logický stav efektu, nie fyzický blink každého relé.

### Ochrana pred zahltením systému

Toto je najdôležitejšia poistka proti "zasekaniu" systému.

V aktuálnom relé firmware `handleEffects()` volá `setDevice(...)` pri každom bliknutí.
Keby `setDevice(...)` automaticky publishovalo MQTT state pri každom volaní, rýchle efekty
by mohli vytvoriť veľa MQTT správ a následne veľa WebSocket update-ov do frontendu.

Preto:

- `setDevice(...)` nemá natvrdo publishovať vždy. Lepšie je použiť parameter alebo wrapper,
  napríklad `setDeviceState(deviceIndex, state, source, publishState)`.
- Pri bežnom ON/OFF príkaze sa state publikuje hneď.
- Pri auto-off a `STOP` sa state publikuje hneď.
- Pri internom blikaní efektu sa nepublikuje každý fyzický toggle, ak Live view nemá
  zobrazovať samotné pulzovanie.
- Stav efektu sa publikuje logicky ako `ACTIVE` alebo `INACTIVE`.
- State publisher má preskočiť duplicitný stav, ak sa hodnota nezmenila. Výnimka je
  `force=true` pri boote alebo reconnecte.
- Pri `publishAllDeviceStates(...)` po boote, reconnecte alebo `STOP` je vhodné správy
  poslať sekvenčne a bez blokujúceho čakania. Ak publish zlyhá, systém nesmie ostať
  v retry slučke; ďalší pravidelný snapshot alebo reconnect stav opraví.
- Pri väčšom počte výstupov je možné doplniť krátke coalescing okno v backende, napríklad
  50-100 ms, aby frontend nedostal 20 samostatných render update-ov naraz.
- JSON payloady držať kompaktné. Ak by payload spolu s topicom presiahol limit knižnice
  PubSubClient, treba zvýšiť MQTT buffer alebo použiť plain state payload s `node_id`
  odvodeným z `devices.json`.

Takto state reporting nezvyšuje riziko zaseknutia. Pridáva len malé množstvo správ pri
reálnych zmenách, nie pri každom behu loopu alebo každom bliknutí efektu.

### Motor firmware

Doplniť stavový report pre motor:

```json
{
  "state": "ON",
  "direction": "LEFT",
  "speed": 70,
  "node_id": "Room1_ESP_Motory",
  "source": "command",
  "ts_ms": 123456
}
```

Použitie:

- po `ON` publikovať `ON` + smer/rýchlosť,
- po `OFF` alebo `STOP` publikovať `OFF`,
- po zmene `SPEED` alebo `DIR` publikovať aktualizovaný stav,
- po reconnecte publikovať aktuálny stav oboch motorov.

## Backend zmeny

### Topic rules

Doplniť do `utils/mqtt/topic_rules.py`:

- rozpoznanie topicu končiaceho na `/state`,
- odvodenie command topicu zo state topicu,
- odvodenie state topicu z command topicu.

Príklad:

```text
room1/light/1/state -> room1/light/1
room1/light/1       -> room1/light/1/state
```

### Subscribe behavior

Current backend subscriptions already include the room wildcard:

```python
f'{room_id}/#'
```

Therefore the backend does not need a new MQTT subscription for `/state` topics
in the current codebase. The implementation task is to extend routing in
`MQTTMessageHandler`, not to add another subscribe call.

If the wildcard subscription is removed in a future cleanup, then state topics
must be subscribed dynamically from `devices.json` by deriving
`<topic>/state` for each configured actuator.

### Message handler

Implementation detail for the current codebase:

- Add a topic helper such as `MQTTTopicRules.is_state_topic(topic)`.
- Add a topic helper such as
  `MQTTTopicRules.original_topic_from_state("room1/light/1/state")`.
- Add a dedicated state handler dependency to `MQTTMessageHandler`, or pass in
  the actuator state store through a small runtime service. Keep the routing
  centralized in `mqtt_message_handler.py`.
- State routing must receive `msg.retain` so the store can preserve the
  difference between retained replay and a fresh report if that is useful for
  logging/diagnostics. The freshness decision still depends on
  `online + state report`, not on `retain`.

V `MQTTMessageHandler` pridať prioritu:

1. device status,
2. feedback,
3. state report,
4. scene/button/start_scene,
5. MQTT udalosti pre scénu.

State reporty musia byť odchytené pred tým, než sa pošlú do `scene_parser.register_mqtt_event(...)`.

### State store

`MQTTActuatorStateStore` rozšíriť tak, aby podporoval:

- `desired_state` = čo backend chcel odoslať,
- `confirmed_state` alebo `reported_state` = čo hlási ESP32,
- `node_id`,
- `state_source`,
- `last_state_ts`,
- `stale`,

Nepridávať zatiaľ `seq`, `boot_id` ani `session_id`. Pre 10-20 zariadení je to
zbytočná komplexita; nechať iba ako budúcu diagnostiku, ak sa objaví konkrétny
problém so starými retained správami alebo s duplicitami.

Kvôli kompatibilite s frontendom je možné ponechať názov `confirmed_state`, ale jeho
autoritatívnym zdrojom by mali byť nové `state` topic-y. Feedback `OK` môže rušiť pending
stav, ale fyzický/live stav by mal potvrdiť až `state` report.

Current-code changes needed in `mqtt_actuator_state_store.py`:

- Add an initialization method that accepts configured devices and creates all
  configured topics before any command is sent.
- Add a state-report method separate from feedback confirmation, for example
  `update_reported_state(topic, payload, node_id=None, node_online=False,
  retained=False)`.
- `update_reported_state(...)` may update the stored last reported value even
  while the node is not online, but it must only set `stale=false` when the
  owning node is online.
- Keep `desired_state` from outgoing commands independent from reported state.
  If the new reported state equals `desired_state`, pending is resolved.
- `mark_node_offline(node_id)` must work for topics created from `devices.json`,
  not only for topics that previously received a command.
- When `mark_node_offline(...)` runs, set `confirmed_state=UNKNOWN` and
  `stale=true`, but keep enough last-report metadata for diagnostics if useful.

### Device config mapping

Rozšíriť `raspberry_pi/config/rooms/<room_id>/devices.json` o `node_id`.

Rozhodnutie 2026-06-12: `node_id` je explicitný stabilný ESP32 client/status
identifier, nie dynamicky odvodený názov. Musí sa zhodovať s MQTT status
topicom `devices/<node_id>/status`, napríklad `Room1_Relays_Ctrl`.

Príklad:

```json
{
  "id": "light_1",
  "name": "Edizonka",
  "topic": "room1/light/1",
  "node_id": "Room1_Relays_Ctrl"
}
```

`state_topic` netreba povinne ukladať, dá sa odvodiť ako `<topic>/state`.

Backend má pri štarte načítať `devices.json` a zaregistrovať, ktoré topicy patria ku
ktorému `node_id`. Potom pri `devices/<node_id>/status = offline` vie označiť všetky
výstupy daného uzla ako `UNKNOWN` alebo `STALE`.

Ak príde JSON state payload s `node_id`, backend môže overiť, že sedí s mappingom.
Ak príde plain payload bez `node_id`, backend používa mapping podľa command topicu.
Nesúlad `node_id` v payloade s `devices.json` má byť logovaný ako warning a stav sa
má radšej priradiť podľa lokálnej konfigurácie.

Compatibility note:

- Existing frontend `useDevices()` passes through unknown fields from
  `/api/devices`, so adding `node_id` to each device object is compatible.
- Backend save/load routes for `/api/devices` operate on raw JSON and do not
  reject extra fields, so `node_id` can be added without a form rewrite.
- Do not require `state_topic` in config unless a real non-standard topic is
  needed. Derive it from `topic + "/state"` for normal devices.

### Offline správanie

Ak uzol prejde offline:

```text
devices/Room1_Relays_Ctrl/status = offline
```

backend označí všetky jeho výstupy:

```text
stale = true
confirmed_state = UNKNOWN
```

Frontend potom nemá zobrazovať staré `ON` ako aktuálnu pravdu, ale `UNKNOWN / STALE`.

Po reconnecte ESP32 znovu publikuje všetky state správy a backend ich obnoví.

Retained state je dobrý na rýchle obnovenie po reštarte backendu, ale sám o sebe nestačí.
Backend musí vždy kombinovať:

```text
availability/status uzla + posledný state report výstupu
```

Príklad:

- retained `room1/light/1/state = ON`,
- ale `devices/Room1_Relays_Ctrl/status = offline`,
- frontend zobrazí `UNKNOWN / STALE`, nie `ON`.

Po boote ESP32 je bezpečný postup:

1. inicializovať GPIO/runtime stav,
2. pripojiť sa na MQTT,
3. publikovať aktuálny snapshot všetkých výstupov,
4. publikovať alebo obnoviť `devices/<node_id>/status = online`.

Ak by status `online` prišiel skôr ako snapshot, backend môže uzol dočasne označiť ako
`syncing` alebo ponechať staré hodnoty ako `STALE`, kým nepríde prvý state report.

Ak snapshot príde skôr ako `online`, backend ho nemá zahodiť. Má ho uložiť ako posledný
reportovaný stav, ale frontend ho má stále zobrazovať ako `STALE`, kým availability stav
uzla nepotvrdí `online`. Tým sa predíde race condition pri reconnecte.

Backend startup / retained replay rule:

- MQTT broker môže po subscribe doručiť retained `<topic>/state` a retained
  `devices/<node_id>/status` v poradí, na ktoré sa backend nesmie spoliehať.
- Pri štarte backendu preto najprv všetky výstupy z `devices.json` založiť ako
  `stale=true`, `confirmed_state=UNKNOWN`.
- Retained `/state` správa môže uložiť posledný reportovaný stav, ale nesmie sama
  odblokovať Live view na aktuálny `ON` / `OFF`.
- Výstup sa považuje za aktuálny až keď backend vie, že jeho `node_id` je online
  a má pre daný topic state report. Prakticky: `online + state report` odblokuje
  `stale=false`; `offline` vždy vráti výstupy daného uzla na `STALE/UNKNOWN`.

### Poradie feedback vs state

Feedback a state môžu prísť v rôznom poradí:

- feedback príde prvý, state až o chvíľu,
- state príde prvý, feedback až o chvíľu,
- feedback je `ERROR`, ale neskorší state report ukáže, že runtime stav sa zmenil.

Backend preto nemá byť závislý od pevného poradia správ. Praktické pravidlo:

- feedback rieši výsledok konkrétneho command-u a log/pending stav,
- state report rieši autoritatívny Live view stav,
- ak state report zodpovedá `desired_state`, pending sa môže zrušiť aj vtedy, keď feedback
  ešte neprišiel,
- ak príde `ERROR`, nezmeniť live stav na úspešný; ale neskorší validný state report z ESP32
  má stále prednosť ako pravda o runtime stave.

## Frontend zmeny

`RuntimeContext` už vie prijímať `device_runtime_state_update`. Zmeny majú byť hlavne
v interpretácii dát:

- Live view zobrazuje primárne stav hlásený ESP32.
- `PENDING` znamená, že `desired_state` sa líši od posledného hláseného stavu.
- `STALE` znamená, že node je offline alebo stav je neaktuálny.
- Pri `stale=true` zobrazovať `UNKNOWN`, nie posledný starý `ON`.
- Zobraziť `last_update_ts` alebo relatívny vek stavu ako doplnkovú diagnostiku.

Pri pridávaní zariadení v `devices.json` musí Live view automaticky používať:

```text
topic -> state_topic = topic + "/state"
node_id -> offline/stale väzba
```

Current frontend compatibility:

- `RuntimeContext` uses `deviceStates[device.topic]`, so backend snapshots must
  keep `topic` equal to the command topic from `devices.json`.
- `getStateForDevice(...)` already returns `UNKNOWN` when `entry.stale` is
  true. Keep `STALE` higher priority than `PENDING`.
- `runtimeSummary` counts only entries returned by `/api/runtime` /
  `/api/device_states`. If the backend does not bootstrap all configured
  devices into the store, Live view can under-count `UNKNOWN` and `STALE`.
- A frontend rebuild is only needed if source files in `museum-dashboard/src`
  change. This rework should be mostly backend/ESP32/config unless UI labels or
  diagnostics are improved.

## Testovací plán

### Backend unit testy

- Store bootstrap z `devices.json` vytvori zaznamy pre vsetky rele/svetla/motory
  este pred prvym command feedbackom.
- `room1/light/1/state` sa rozpozná ako state topic.
- `room1/light/1/state` sa ulozi/emituje ako `topic = room1/light/1`, nie ako
  `topic = room1/light/1/state`.
- Incoming `/state` report sa nezaregistruje ako scene MQTT transition event.
- JSON payload `{"state":"ON","node_id":"Room1_Relays_Ctrl"}` nastaví stav na `ON`.
- Plain payload `OFF` nastaví stav na `OFF`.
- Retained state po starte ulozi posledny report, ale bez `online` statusu
  necha vystup `STALE/UNKNOWN`.
- `online + state report` nastavi `stale=false`.
- `update_desired(...)` pri offline/stale node nevycisti `stale`.
- Feedback `OK` pri offline/stale node nevycisti `stale`.
- `devices/<node_id>/status = offline` označí všetky mapované topicy ako `STALE`.
- `force_all_off(...)` neoznaci offline node ako fresh `OFF`.
- `ERROR` feedback nezmení stav na úspešne potvrdený.
- State report prepise stary feedback-derived stav.
- Efekt `ACTIVE` / `INACTIVE` nemeni stav pri kazdom internom bliku.

### ESP32 manuálne testy

- Po boot/reconnect ESP32 publikuje všetky aktuálne state topic-y.
- `ON` na relé publikuje `feedback=OK` a `state=ON`.
- `OFF` na relé publikuje `feedback=OK` a `state=OFF`.
- Neznámy príkaz `BLINK` publikuje `feedback=ERROR` a nemení `state`.
- Auto-off publikuje `state=OFF`.
- `STOP` publikuje `OFF` pre všetky výstupy.
- Pri aktívnom efekte sa nepublikuje per-output state pri každom bliknutí, iba logický
  stav efektu `ACTIVE/INACTIVE`, pokiaľ sa zámerne nezapne throttlované fyzické hlásenie.
- ESP32 ignoruje vlastné `/state` topic-y, hlavne pri subscribovaní `room1/effects/#`.

### End-to-end testy

1. Backend pošle `room1/light/1 = ON`.
2. Frontend ukáže `PENDING`.
3. ESP32 pošle `feedback=OK`.
4. ESP32 pošle `state=ON`.
5. Frontend ukáže `ON`.

Ďalšie scenáre:

- ESP32 sa vypne -> frontend ukáže `STALE/UNKNOWN`.
- ESP32 sa zapne -> publikuje state -> frontend obnoví hodnoty.
- Externý MQTT klient pošle platný command -> ESP32 vykoná -> state report aktualizuje frontend,
  aj keď backend nemal pending príkaz.
- Pridá sa 10 nových relé v `DEVICES[]` a `devices.json` -> backend a frontend ich zobrazia
  bez ďalšej ručnej logiky.
- Rýchly blink efekt beží 30 sekúnd -> MQTT a frontend nedostávajú spam pri každom toggle.
- Backend sa reštartuje, retained state je `ON`, ale node je offline -> frontend ukáže
  `STALE/UNKNOWN`.

## Implementation phases

### Fáza 1: State topic-y bez zmeny command API - IMPLEMENT

- Zachovať existujúce command a feedback topic-y.
- Dopísať ESP32 publish state po každej reálnej logickej zmene.
- V ESP32 callbacku ignorovať `/state`, aby nevznikli slučky pri wildcard subscribe.
- Pri efektoch nepublikovať každý interný toggle, iba logický stav efektu.
- Backend začne state topic-y routovať a aktualizovať store. V aktuálnom kóde
  netreba nový subscribe, pretože backend už subscribuje `room1/#`.
- Frontend bude stále kompatibilný s `confirmed_state`.

### Fáza 2: `node_id` a offline/stale väzba - IMPLEMENT

- Doplniť explicitný `node_id` do `devices.json`; hodnota musí sedieť s ESP32
  MQTT client/status identifikátorom.
- Backend pri štarte zaregistruje mapovanie `node_id -> topics`.
- Offline status nastaví všetky výstupy uzla na `STALE/UNKNOWN`.
- Reconnect `online` sám o sebe nemá vyčistiť `stale`; stav sa stane aktuálnym
  až po novom `/state` reporte.

### Fáza 3: Presnejšie párovanie príkazov - SUPERSEDED / DEFERRED

- Neimplementovať v aktuálnom scope. `command_id` je pre tento systém zatiaľ
  viac komplexity než prínosu.
- Ak sa v produkcii ukáže problém s rýchlym opakovaním príkazov na rovnaký topic,
  dá sa táto fáza znovu otvoriť.
- Pôvodný referenčný návrh:
- Feedback payload môže byť JSON:

```json
{
  "command_id": "abc123",
  "result": "OK"
}
```

- Tým sa vyrieši rýchle opakovanie príkazov na rovnaký topic.

### Fáza 4: Voliteľné QoS 1 pre kritické príkazy - SUPERSEDED / DEFERRED

- Neimplementovať v aktuálnom scope. QoS 1 mení správanie MQTT vrstvy a neprináša
  dosť hodnoty, kým existuje ACK + state reporting.
- Pre `STOP`, `START` alebo kritické príkazy zvážiť QoS 1 až po konkrétnom
  výpadkovom scenári.
- Feedback a state topic-y ponechať aj pri QoS 1.
- QoS 1 nesmie byť náhrada za state reporting.

### Fáza 5: Voliteľná nová topic schéma - SUPERSEDED / DEFERRED

Neimplementovať v aktuálnom scope. Existujúce topicy sú spätne kompatibilné a
state topic sa dá jednoducho odvodiť pridaním `/state`.

Ak bude raz čas na väčší rework, zvážiť čistejšie názvy:

```text
room1/light/1/set
room1/light/1/ack
room1/light/1/state
```

Pre bakalársky systém a spätnú kompatibilitu však stačí odvodiť:

```text
command: room1/light/1
ack:     room1/light/1/feedback
state:   room1/light/1/state
```

## Odporúčané rozhodnutie

Nerobiť iba quick fix vo feedback trackeri. Správny dlhodobý smer je ponechať feedback
ako odpoveď na konkrétny príkaz a doplniť samostatné retained state topic-y z ESP32.

Aktuálne odporúčanie je implementovať iba Fázu 1 a Fázu 2. To dáva väčšinu hodnoty:
Live view dostane autoritatívny stav, backend po reštarte vie obnoviť posledné známe
hodnoty a offline uzol sa nebude tváriť ako stále platný `ON`.

Keďže systém ešte nie je v ostrej prevádzke, nie je potrebné navrhovať postupnú
live migráciu. Stále však netreba meniť command topic-y ani zavádzať `/set` a
`/ack`, pretože by to zvýšilo rozsah práce bez praktického prínosu pre tento
počet zariadení.

Takýto model je škálovateľný, pretože pri novom zariadení stačí:

1. pridať výstup do `DEVICES[]` vo firmvéri ESP32,
2. pridať položku do `devices.json` vrátane `node_id`,
3. ESP32 začne publikovať `<topic>/state`,
4. backend a frontend stav automaticky zobrazia.
