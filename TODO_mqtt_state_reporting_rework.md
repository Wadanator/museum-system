# TODO: Autoritatívne MQTT stavové hlásenia pre Live view

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
  "seq": 42,
  "ts_ms": 123456
}
```

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
  "seq": 18,
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

### Message handler

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
- voliteľne `seq`,
- voliteľne `boot_id` alebo `session_id`, ak bude treba odlíšiť starý retained stav od
  stavu po novom štarte ESP32.

Kvôli kompatibilite s frontendom je možné ponechať názov `confirmed_state`, ale jeho
autoritatívnym zdrojom by mali byť nové `state` topic-y. Feedback `OK` môže rušiť pending
stav, ale fyzický/live stav by mal potvrdiť až `state` report.

### Device config mapping

Rozšíriť `raspberry_pi/config/rooms/<room_id>/devices.json` o `node_id`.

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

## Testovací plán

### Backend unit testy

- `room1/light/1/state` sa rozpozná ako state topic.
- JSON payload `{"state":"ON","node_id":"Room1_Relays_Ctrl"}` nastaví stav na `ON`.
- Plain payload `OFF` nastaví stav na `OFF`.
- Retained state po štarte obnoví stav.
- `devices/<node_id>/status = offline` označí všetky mapované topicy ako `STALE`.
- `ERROR` feedback nezmení stav na úspešne potvrdený.

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

## Migračné fázy

### Fáza 1: State topic-y bez rozbitia existujúceho systému

- Zachovať existujúce command a feedback topic-y.
- Dopísať ESP32 publish state po každej reálnej logickej zmene.
- V ESP32 callbacku ignorovať `/state`, aby nevznikli slučky pri wildcard subscribe.
- Pri efektoch nepublikovať každý interný toggle, iba logický stav efektu.
- Backend začne state topic-y počúvať a aktualizovať store.
- Frontend bude stále kompatibilný s `confirmed_state`.

### Fáza 2: `node_id` a offline/stale väzba

- Doplniť `node_id` do `devices.json`.
- Backend pri štarte zaregistruje mapovanie `node_id -> topics`.
- Offline status nastaví všetky výstupy uzla na `STALE/UNKNOWN`.

### Fáza 3: Presnejšie párovanie príkazov

- Voliteľne doplniť `command_id`.
- Feedback payload môže byť JSON:

```json
{
  "command_id": "abc123",
  "result": "OK"
}
```

- Tým sa vyrieši rýchle opakovanie príkazov na rovnaký topic.

### Fáza 4: Voliteľné QoS 1 pre kritické príkazy

- Pre `STOP`, `START` alebo kritické príkazy zvážiť QoS 1.
- Feedback a state topic-y ponechať aj pri QoS 1.
- QoS 1 nesmie byť náhrada za state reporting.

### Fáza 5: Voliteľná nová topic schéma

Ak bude čas na väčší rework, zvážiť čistejšie názvy:

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

Takýto model je škálovateľný, pretože pri novom zariadení stačí:

1. pridať výstup do `DEVICES[]` vo firmvéri ESP32,
2. pridať položku do `devices.json` vrátane `node_id`,
3. ESP32 začne publikovať `<topic>/state`,
4. backend a frontend stav automaticky zobrazia.
