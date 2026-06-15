# Cover/Roleta Support Plan

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short date or note if useful, and do not leave completed work only in chat or
git history.

Tento dokument popisuje navrhovanu podporu roliet, zaluzii a inych 230 V
obojsmernych pohonov cez `cover` moduly v `museum-system`.

Dokument je zamerne iba implementacny navrh. V repozitari zatial netreba menit
Python, React, Shelly script, ESPHome YAML ani ESP32 firmware kod, kym nie je
potvrdeny finalny hardware a bezpecnostne spravanie.

---

## 1. Ciel integracie

Do systemu sa ma pridat novy typ zariadenia:

- existujuce typy: `motor`, `relay`
- novy typ: `cover`

`cover` znamena motoricky prvok typu roleta, zaluziovy pohon, opona, dvierka
alebo podobny AC/Servo pohon s dvoma smermi. V Shelly terminologii sa tato trieda
zariadeni vola `Cover`.

Hlavny ciel je, aby sa novy cover uzol z pohladu Raspberry Pi spraval rovnako
ako existujuce ESP32 uzly:

- prijima prikazy cez room-scoped MQTT topicy,
- publikuje feedback na `<command_topic>/feedback`,
- publikuje stav zariadenia na `devices/<client_id>/status`,
- reaguje na `roomX/STOP`,
- da sa pridat do `devices.json`,
- zobrazi sa vo frontende v Commands view,
- je dostupny v palete Scene Editora,
- vie byt pouzity v JSON scenach cez standardnu akciu `{"action": "mqtt"}`.

---

## 2. Odporucany hardware

## 2.1 Moznost A: Shelly Pro Dual Cover / Shutter PM

Odporucany hotovy modul:

- `Shelly Pro Dual Cover / Shutter PM`
- DIN rail montaz
- Ethernet/LAN
- MQTT
- Shelly Scripts
- 2 samostatne `Cover` vystupy: `cover:0`, `cover:1`
- power metering

Toto je vhodnejsie ako male Wi-Fi moduly, pretoze muzeum preferuje stabilnu
LAN komunikaciu, montaz do rozvadzaca a centralizovanu servisovatelnost.

## 2.2 Moznost B: existujuci Waveshare ESP32-S3-ETH-8DI-8RO

Pouzitelny modul, ktory uz projekt ma:

- `Waveshare ESP32-S3-ETH-8DI-8RO` alebo PoE varianta,
- ESP32-S3,
- W5500 Ethernet,
- 8 rele vystupov,
- 8 opticky izolovanych digitalnych vstupov,
- I2C expander pre rele vystupy,
- existujuca LAN Arduino firmware vetva v repozitari:
  `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/`.

Prakticky to znamena:

- LAN kabel ano,
- 8 rele = maximalne 4 cover pohony, ak kazdy pouzije 2 rele (`open` + `close`),
- MQTT kompatibilita s tvojim systemom je dosiahnutelna,
- `devices/<client_id>/status` a `<topic>/feedback` uz stylovo sedia k
  existujucemu kodu,
- existujuci `room1/STOP` moze ostat spolocny kill/stop signal.

Dolezita hranica:

Existujuci relay firmware ma `autoOffMs` pre jednotlive vystupy, global STOP,
status a feedback. Nema vsak cover-pair logiku pre dvojicu rele typu
`open/close`. Preto nestaci iba premenovat `DEVICES[]` na
`cover/1/open` a `cover/1/close`. Pre 230 V pohon treba doplnit aspon:

- mutual exclusion: nikdy nezopnut `open` aj `close` naraz,
- dead-time pri zmene smeru,
- jeden command topic na jeden pohon (`room1/cover/1`), nie dva nezavisle
  rele topicy,
- max runtime pre cely pohyb,
- feedback `OK/ERROR` po prijati prikazu,
- state topic, ak ma frontend ukazovat pohyb a poziciu.

## 2.3 Moznost C: Shelly 2PM Gen4 pre jeden pohon

Mozna lacnejsia alternativa:

- `Shelly 2PM Gen4`

Pouzit iba vtedy, ak nevadi Wi-Fi alebo lokalna montaz pri pohone/vypinaci.
Pre poziadavku "bez Wi-Fi, cez LAN kabel" je vhodnejsi Pro rad s Ethernetom.

## 2.4 Porovnanie moznosti

| Moznost                    | Vyhody                                      | Nevyhody                                        | Odporucanie                                                 |
| -------------------------- | ------------------------------------------- | ----------------------------------------------- | ----------------------------------------------------------- |
| Shelly Pro Dual Cover      | Hotovy cover modul, LAN, DIN, 2 pohony      | drahsi, dalsi hardware                          | najlepsie pre rychlu produkcnu instalaciu                   |
| Waveshare Arduino firmware | uz ho mas, zapada do aktualneho ESP32 kodu  | treba doplnit cover interlock logiku            | dobre, ak chces ostat pri vlastnom firmware                 |
| Waveshare ESPHome          | hotovy ESPHome pinout, cover komponent, LAN | iny firmware stack ako zvysok repo Arduino kodu | dobre pre rychle prototypovanie alebo samostatny cover node |
| Shelly 2PM Gen4            | lacnejsie pre 1 pohon                       | bez LAN, lokalna montaz/Wi-Fi                   | pouzit iba ak LAN nie je poziadavka                         |

## 2.5 Co nekupovat alebo nepouzit naivne

Neodporucane:

- obycajny `Shelly 1`, `Shelly 1PM`, `Shelly Plus 1`,
- genericke dvojrele bez cover/shutter rezimu,
- existujuci Waveshare relay firmware bez specialnej interlock logiky,
- dve nezavisle MQTT rele akcie pre `open` a `close` bez centralneho
  motorickeho guardu.

Pri 230 V pohone s vodičmi `L_open` a `L_close` je kriticke, aby nikdy neboli
aktivne oba smery naraz. Cover modul toto riesi ako jeden motoricky prvok.
Obycajne rele to berie ako dva nezavisle vystupy, co je rizikove.

---

## 3. Shelly konfiguracia

Konfiguracia sa robi vo web UI Shelly zariadenia alebo cez Shelly RPC.
Presne nazvy poloziek sa mozu lisit podla firmware verzie, ale princip ostava
rovnaky.

## 3.1 Siet

Pre `Shelly Pro Dual Cover / Shutter PM`:

- pripojit Ethernet RJ45,
- nastavit DHCP reservation alebo staticku IP,
- Wi-Fi moze ostat vypnute, ak sa nechce pouzivat ako fallback,
- Shelly Cloud vypnut, ak ma byt system plne lokalny,
- overit, ze Raspberry Pi a Shelly su v rovnakej sieti ako MQTT broker.

## 3.2 MQTT

Nastavit:

- `MQTT enable = true`
- `server = <broker_ip>:1883`
- `topic_prefix = shellypro-cover-room1` alebo iny stabilny interny prefix
- `enable_control = true`
- `enable_rpc = true`
- `status_ntf = true` volitelne, vhodne pre diagnostiku

Poznamka k statusu:

Shelly ma vlastne native MQTT status/online topicy, ale tvoj backend dnes
ocakava `devices/<client_id>/status` s payloadom `online` alebo `offline`.
Preto sa pre kompatibilitu nepouziva iba Shelly native online topic. Adapter
script ma periodicky publikovat:

```text
devices/Room1_Shelly_Covers/status -> online
```

Tym aktualny `MQTTDeviceRegistry` funguje bez specialnej znalosti Shelly
topicov. Ak Shelly prestane status publikovat, registry ho po
`device_timeout` oznaci ako offline.

## 3.3 Cover setup

Pre kazdy fyzicky pohon:

- nastavit vystup ako `Cover`/`Shutter`, nie ako dve samostatne rele,
- overit smerovanie `open` a `close`,
- nastavit maximalny cas pohybu,
- nastavit vstupy podla zapojenia:
  - `dual` pre dve tlacidla hore/dole,
  - `detached`, ak fyzicke tlacidla nemaju priamo ovladat pohon,
  - safety input iba ak ho elektrikarsky navrh vyzaduje.

## 3.4 Kalibracia

Kalibracia je potrebna iba pre pozicne prikazy.

Bez kalibracie:

- `OPEN` funguje,
- `CLOSE` funguje,
- `STOP` funguje,
- `POS:<0-100>` nema byt pouzite.

Po kalibracii:

- `POS:0` znamena uplne zatvorene,
- `POS:100` znamena uplne otvorene,
- `POS:50` znamena priblizne polovica drahy.

Shelly dokumentacia uvadza, ze `Cover.GoToPosition` vyzaduje kalibrovany cover
a znamu aktualnu poziciu. Po vypadku napajania moze byt nutne pohon najprv
poslat na znamy koncovy bod.

---

## 3B. Waveshare konfiguracia

Tato sekcia popisuje druhu moznost: pouzit existujucu Waveshare
`ESP32-S3-ETH-8DI-8RO` dosku ako cover controller.

## 3B.1 Co uz v repozitari mas

Relevantna aktualna vetva:

```text
esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/
```

Podla aktualneho kodu:

- LAN/W5500 je primarny transport,
- Wi-Fi je fallback,
- MQTT client id je `Room1_Relays_Ctrl`,
- status topic je `devices/Room1_Relays_Ctrl/status`,
- base topic je `room1/`,
- firmware subscribuje `room1/<device_name>`, `room1/effects/#`, `room1/STOP`,
- feedback ide na `<command_topic>/feedback`,
- rele vystupy su cez I2C expander `0x20`,
- I2C piny su `GPIO42`/`GPIO41`,
- W5500 piny su `GPIO15`, `GPIO14`, `GPIO13`, `GPIO16`, `GPIO12`,
- `autoOffMs` uz vie vypnut jednotlive vystupy po case.

To je dobry zaklad pre cover node, ale aktualne je to stale relay controller,
nie cover controller.

## 3B.2 Odporucana Arduino firmware cesta

Ak chceme ostat v style aktualneho repozitara, odporucam nevymenit firmware
stack za ESPHome, ale spravit novu kopiu existujuceho LAN relay firmveru:

```text
esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_COVERS/
```

Zaklad:

```text
copy esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY
  -> esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_COVERS
```

Potom upravit konfiguraciu:

```text
CLIENT_ID = Room1_Covers_Ctrl
STATUS_TOPIC = devices/Room1_Covers_Ctrl/status
BASE_TOPIC_PREFIX = room1/
```

Navrhovane mapovanie 8 rele na 4 cover pohony:

| Cover topic       | Open relay bit | Close relay bit |
| ----------------- | -------------: | --------------: |
| `room1/cover/1` |              0 |               1 |
| `room1/cover/2` |              2 |               3 |
| `room1/cover/3` |              4 |               5 |
| `room1/cover/4` |              6 |               7 |

Pozor: toto plati iba pre dedikovanu Waveshare dosku na rolety. Ak aktualna
Waveshare doska uz ovlada dymostroj, svetla a efekty, nema volnych 8 rele pre
4 rolety. Vtedy treba bud dalsiu dosku, alebo premapovat realne fyzicke
vystupy.

## 3B.3 Co treba do Arduino firmware doplnit

Minimalna nova logika:

```text
struct CoverDevice {
  const char* topicName;       // cover/1
  int openRelayIndex;          // bit 0
  int closeRelayIndex;         // bit 1
  unsigned long moveTimeoutMs; // napr. 30000
};
```

Parser v `mqtt_manager.cpp` ma pred existujucim "Individual device" blokom
rozpoznat:

```text
room1/cover/1 -> OPEN
room1/cover/1 -> CLOSE
room1/cover/1 -> STOP
room1/cover/1 -> POS:50
```

Pre `OPEN`:

1. vypnut close relay,
2. pockat kratky dead-time, napr. 500 ms,
3. zapnut open relay,
4. nastavit max runtime timer,
5. publikovat `room1/cover/1/feedback -> OK`.

Pre `CLOSE`:

1. vypnut open relay,
2. pockat kratky dead-time,
3. zapnut close relay,
4. nastavit max runtime timer,
5. publikovat feedback `OK`.

Pre `STOP`:

1. vypnut oba rele,
2. zrusit runtime timer,
3. publikovat feedback `OK`.

Pre neznamy alebo nevalidny payload:

```text
room1/cover/1/feedback -> ERROR
```

`POS:<n>` cez cisty rele modul bez merania pozicie nie je skutocna pozicia.
Da sa implementovat iba ako casovy odhad po kalibracii drahy, podobne ako
ESPHome `time_based` cover. Ak nie je potrebne polohovanie, prvu verziu
obmedzit na `OPEN`, `CLOSE`, `STOP`.

## 3B.4 Preco nestaci iba `DEVICES[]`

Teoreticky by sa dalo urobit:

```text
room1/cover/1/open  -> ON
room1/cover/1/close -> ON
```

Toto vsak neodporucam.

Dovod:

- aktualny `setDevice()` nevie, ze dve rele patria k jednemu motoru,
- scene alebo manualny operator by mohli omylom zapnut oba smery,
- `autoOffMs` riesi maximalny cas jedneho vystupu, nie smerove blokovanie,
- frontend by videl dve rele, nie jeden cover pohon.

Spravna abstrakcia pre system je:

```text
room1/cover/1 -> OPEN/CLOSE/STOP/POS:50
```

Teda jeden topic pre jeden fyzicky pohon.

## 3B.5 ESPHome cesta na tej istej Waveshare doske

ESPHome je druha mozna cesta na rovnakom hardware. Hodila by sa vtedy, ak
chceme rychlo prototypovat cover spravanie bez pisania C++ Arduino firmware.

Vyhody:

- oficialny ESPHome device profil pre tuto dosku existuje,
- W5500 Ethernet je podporeny,
- rele su uz popisane cez `pca9554` expander,
- ESPHome ma `time_based` cover komponent,
- GPIO switch komponent ma `interlock` a `interlock_wait_time`,
- MQTT ma `birth_message`, `will_message`, `on_message` a `mqtt.publish`.

Zakladne piny pre tuto dosku:

```yaml
ethernet:
  type: W5500
  clk_pin: GPIO15
  mosi_pin: GPIO13
  miso_pin: GPIO14
  cs_pin: GPIO16
  interrupt_pin: GPIO12

i2c:
  sda: GPIO42
  scl: GPIO41

pca9554:
  - id: TCA9554_hub
    address: 0x20
```

Poznamka: nepouzivat nahodne W5500 piny z generickych prikladov. Tvoj
existujuci Arduino firmware aj ESPHome devices profil pouzivaju pre tuto
Waveshare dosku `GPIO15/13/14/16/12`.

Rele v ESPHome nie su priame `GPIO1`, `GPIO2`, ale piny na expanderi:

```yaml
switch:
  - platform: gpio
    id: relay1
    pin:
      pca9554: TCA9554_hub
      number: 0
      mode:
        output: true
    restore_mode: ALWAYS_OFF
    interlock: [relay2]
    interlock_wait_time: 500ms

  - platform: gpio
    id: relay2
    pin:
      pca9554: TCA9554_hub
      number: 1
      mode:
        output: true
    restore_mode: ALWAYS_OFF
    interlock: [relay1]
    interlock_wait_time: 500ms
```

Time-based cover skeleton:

```yaml
cover:
  - platform: time_based
    id: cover_1
    name: "Cover 1"
    open_action:
      - switch.turn_off: relay2
      - delay: 500ms
      - switch.turn_on: relay1
    close_action:
      - switch.turn_off: relay1
      - delay: 500ms
      - switch.turn_on: relay2
    stop_action:
      - switch.turn_off: relay1
      - switch.turn_off: relay2
    open_duration: 30s
    close_duration: 30s
```

Pre motory s vlastnymi koncovymi dorazmi aj tak odporucam nechat
`open_duration` a `close_duration` ako softverovu poistku. Nepouzivat
`has_built_in_endstop: true` bez rozmyslu, pretoze pri tejto volbe ESPHome po
dobehu casu nevykona `stop_action`.

## 3B.6 ESPHome a tvoj MQTT protokol

ESPHome native MQTT cover command topic nemusi sam o sebe publikovat tvoj
`/feedback` format. Pre plnu kompatibilitu treba doplnit `mqtt.on_message`
adapter, ktory pocuva tvoje topicy:

```text
room1/cover/1
room1/cover/2
room1/STOP
room1/system/heartbeat
```

a vykona:

```text
OPEN  -> cover.open
CLOSE -> cover.close
STOP  -> cover.stop
POS:n -> cover.control position n
```

Po prijati validneho prikazu publikuje:

```text
room1/cover/1/feedback -> OK
```

Pri nevalidnom prikaze:

```text
room1/cover/1/feedback -> ERROR
```

Tento `OK` znamena "ESPHome prikaz prijal a vykonal lokalnu akciu", nie
hardverovo potvrdeny koncovy doraz. Rovnako funguje aj vacsina existujucich
ESP32 relay potvrdeni v projekte.

## 3B.7 ESPHome fail-safe

`birth_message` a `will_message` riesia online/offline stav pre backend:

```yaml
mqtt:
  broker: 192.168.0.127
  topic_prefix: room1/covers_ctrl
  birth_message:
    topic: devices/Room1_Covers_Ctrl/status
    payload: online
    retain: true
  will_message:
    topic: devices/Room1_Covers_Ctrl/status
    payload: offline
    retain: true
```

Ale will message sam nezatvori roletu. Na fail-safe zatvorenie treba bud:

- `mqtt.on_disconnect` akcia, ktora spusti `cover.close`, alebo
- vlastny heartbeat watchdog cez `room1/system/heartbeat`.

Pre tvoju poziadavku "ak nejde MQTT alebo LAN, zatvorit" je robustnejsi
heartbeat watchdog. Dovod: `on_disconnect` riesi MQTT spojenie, ale heartbeat
vie pokryt aj stav, ked Raspberry Pi alebo hlavna aplikacia nebezi spravne.

## 3B.8 Odporucanie pre Waveshare variantu

Ak chces co najviac konzistentny system s aktualnym repozitarom:

1. pouzit dedikovanu Waveshare dosku pre covers,
2. skopirovat existujuci LAN Arduino relay firmware do noveho
   `esp32_mqtt_controller_COVERS`,
3. doplnit cover-pair parser a interlock logiku,
4. pouzit rovnaky MQTT kontrakt ako Shelly alternativa:
   `room1/cover/<id>`, `/feedback`, `devices/<id>/status`, `room1/STOP`,
5. frontend a backend pisat iba proti abstrakcii `cover`, nie proti Shelly
   alebo Waveshare detailom.

Ak chces rychlo overit fyzicke zapojenie a casy pohybu:

1. pouzit ESPHome na Waveshare,
2. nakonfigurovat 1 cover na rele 1/2,
3. overit `OPEN/CLOSE/STOP`,
4. az potom sa rozhodnut, ci ostanes pri ESPHome alebo prepises logiku do
   Arduino firmware stylu repozitara.

---

## 4. Kanonicky MQTT kontrakt pre museum-system

## 4.1 Naming

Pouzivat anglicky technicky nazov `cover`, pretoze:

- zodpoveda Shelly API,
- je ASCII,
- je vseobecnejsi ako `blind`, `shutter`, `roleta` alebo `zaluzia`,
- dobre sedi k buducemu frontendu `covers`.

Priklad pre miestnost `room1`:

```text
room1/cover/1
room1/cover/2
```

Ak jeden Shelly Pro modul ovlada dve rolety:

```text
room1/cover/1 -> Shelly cover:0
room1/cover/2 -> Shelly cover:1
```

## 4.2 Command topics

Kazdy cover ma jeden prikazovy topic:

```text
roomX/cover/<cover_id>
```

Priklady:

```text
room1/cover/1
room1/cover/2
```

## 4.3 Feedback topics

Shelly adapter musi odpovedat na rovnaky topic s `/feedback` suffixom:

```text
room1/cover/1/feedback -> OK
room1/cover/1/feedback -> ERROR
```

Toto je kompatibilne s aktualnym `MQTTFeedbackTracker`, pretoze
`MQTTTopicRules.expected_feedback_topic(original_topic)` sklada feedback ako
`<original_topic>/feedback`.

Poznamka:

`MQTTClient` dnes subscribuje aj `room1/#`, takze nested feedback
`room1/cover/1/feedback` sa do message handlera dostane. `room1/+/feedback`
samotne by nested topic nepokrylo, ale `room1/#` ano.

## 4.4 Status topic

Pre registry kompatibilitu:

```text
devices/Room1_Shelly_Covers/status -> online
```

Odporucany `client_id`:

```text
Room1_Shelly_Covers
```

Ak bude v jednej miestnosti viac Shelly modulov:

```text
Room1_Shelly_Covers_A
Room1_Shelly_Covers_B
```

Status publikovat periodicky, napriklad kazdych 5 az 10 sekund. Aktualny
`config.ini.example` ma `device_timeout = 25`, preto musi byt interval kratsi
ako timeout a mal by mat rezervu aspon niekolko heartbeatov.

## 4.5 State topic

Pre plnohodnotny frontend je vhodne pridat samostatny state topic:

```text
room1/cover/1/state
```

Odporucany JSON payload:

```json
{
  "state": "opening",
  "position": 42,
  "target": 100,
  "source": "shelly",
  "calibrated": true
}
```

Minimalny textovy payload, ak sa nechce posielat JSON:

```text
OPENING
CLOSING
OPEN
CLOSED
STOPPED
UNKNOWN
```

Pre plnu integraciu je lepsi JSON, lebo frontend vie zobrazit percenta a
kalibracny stav.

## 4.6 Heartbeat topic

Pre fail-safe "ak nejde MQTT/Pi/siet, zatvorit" treba heartbeat z Raspberry Pi
do Shelly:

```text
room1/system/heartbeat -> PING
```

Cover adapter si interne resetuje watchdog pri kazdom prijatom heartbeat.
Ak heartbeat nepride do nastaveneho timeoutu, cover uzol vykona bezpecnostnu
akciu podla policy.

Odporucane hodnoty:

```text
Raspberry Pi heartbeat interval: 5 s
Shelly heartbeat timeout: 20 az 30 s
```

Heartbeat musi bezat stale pocas zdraveho runtime, nie iba pocas aktivnej
sceny. Inak by Shelly zatvaral rolety pocas idle stavu.

---

## 5. Payloady

## 5.1 Povinne payloady

Tieto payloady ma podporovat kazdy cover:

| Payload   | Vyznam                  | Shelly RPC metoda |
| --------- | ----------------------- | ----------------- |
| `OPEN`  | otvorit                 | `Cover.Open`    |
| `CLOSE` | zatvorit                | `Cover.Close`   |
| `STOP`  | okamzite zastavit pohyb | `Cover.Stop`    |

## 5.2 Pozicne payloady

Pozicne payloady pouzit iba po kalibracii:

| Payload     | Vyznam                 | Shelly RPC metoda      |
| ----------- | ---------------------- | ---------------------- |
| `POS:0`   | zatvorit na 0 percent  | `Cover.GoToPosition` |
| `POS:50`  | ist na 50 percent      | `Cover.GoToPosition` |
| `POS:100` | otvorit na 100 percent | `Cover.GoToPosition` |

`POS:<n>` musi validovat rozsah `0..100`.

Ak cover nie je kalibrovany alebo Shelly vrati chybu, adapter odpovie:

```text
room1/cover/1/feedback -> ERROR
```

## 5.3 Volitelne admin payloady

Tieto payloady neodporucam davat do beznej palety Scene Editora, ale mozu byt
uzitocne pre servis:

| Payload       | Vyznam                                                     |
| ------------- | ---------------------------------------------------------- |
| `STATUS`    | adapter publikuje aktualny stav na `room1/cover/1/state` |
| `CALIBRATE` | spusti kalibraciu, iba servisne                            |

`CALIBRATE` moze byt rizikovy prikaz, preto ho nepouzivat v beznych scenach.

---

## 6. STOP a fail-safe politika

Toto su dve rozdielne veci a nemaju sa miesat.

## 6.1 `room1/STOP`

Aktualny backend pri `stop_scene()` publikuje:

```text
room1/STOP -> STOP
```

Pre cover zariadenia odporucam:

- `room1/STOP` vykona `Cover.Stop`, nie `Cover.Close`,
- ciel je okamzite zastavit pohyb a nevyvolat novy pohyb.

Dovod: operator moze stlacit "Vypnut vsetko" prave preto, ze sa nieco hybe
neziaducim smerom. Automaticke zatvaranie po global STOP by mohlo sposobit
dalsi pohyb.

Ak expozicia explicitne vyzaduje zatvorenie pri stopnuti sceny, scena ma mat
vlastny `onExit` alebo finalny stav:

```json
{
  "action": "mqtt",
  "topic": "room1/cover/1",
  "message": "CLOSE"
}
```

## 6.2 Heartbeat fail-safe

Pri strate riadiaceho systemu je poziadavka ina:

- Raspberry Pi crash,
- MQTT broker nedostupny,
- LAN kabel odpojeny,
- Shelly pripojeny k napajaniu, ale nema spojenie s brokerom.

Vtedy ma Shelly po timeout-e vykonat policy:

```text
failSafeAction = CLOSE
```

Odporucane spravanie:

- po starte scriptu spustit watchdog,
- heartbeat resetuje watchdog,
- ak heartbeat nepride do 20 az 30 sekund, vykonat `Cover.Close`,
- po vykonani fail-safe uz dalej neopakovat prikaz kazdu sekundu, iba raz za
  timeout cyklus alebo po zmene stavu.

## 6.3 Co fail-safe nevyriesi

Fail-safe cez cover adapter nevyriesi:

- vypadok 230 V napajania Shelly,
- mechanicku poruchu pohonu,
- zaseknutu roletu,
- zle zapojene smery,
- fyzicky odpojeny motor.

Pre realnu bezpecnost musi byt zapojenie a mechanika overena elektrikarsky.

---

## 7. Shelly adapter script - zodpovednosti

Adapter script nie je firmware nahrada. Je to tenka prekladova vrstva medzi
museum MQTT protokolom a Shelly Cover RPC API.

## 7.1 Script robi

- subscribuje `room1/cover/1`,
- subscribuje `room1/cover/2`, ak modul ovlada dve rolety,
- subscribuje `room1/STOP`,
- subscribuje `room1/system/heartbeat`,
- preklada `OPEN`, `CLOSE`, `STOP`, `POS:<n>` na Shelly `Cover.*` RPC,
- publikuje `OK` alebo `ERROR` na `<command_topic>/feedback`,
- periodicky publikuje `devices/<client_id>/status = online`,
- publikuje aktualny cover stav na `room1/cover/<id>/state`,
- drzi heartbeat watchdog pre fail-safe zatvorenie.

## 7.2 Script nerobi

- neriesi sceny,
- neriesi casovanie show,
- neriesi audio/video,
- neobsahuje business logiku miestnosti,
- nemeni MQTT protokol Raspberry Pi backendu.

## 7.3 Minimalna konfiguracia scriptu

Odporucane konstanty:

```text
ROOM_ID = room1
CLIENT_ID = Room1_Shelly_Covers
STATUS_TOPIC = devices/Room1_Shelly_Covers/status
HEARTBEAT_TOPIC = room1/system/heartbeat
HEARTBEAT_TIMEOUT_MS = 30000
STATUS_INTERVAL_MS = 5000
```

Mapovanie coverov:

```text
room1/cover/1 -> Shelly cover id 0
room1/cover/2 -> Shelly cover id 1
```

## 7.4 Poznamky k Shelly mJS

Shelly Scripts nie su Node.js. Pouzivat iba Shelly podporovane API:

- `Shelly.call(...)`
- `Shelly.getComponentStatus(...)`
- `Shelly.addStatusHandler(...)`
- `MQTT.subscribe(...)`
- `MQTT.publish(...)`
- `Timer.set(...)`
- `Timer.clear(...)`

Nepouzivat:

- Node.js moduly,
- `async`/`await`,
- Promise-based flow,
- velke kniznice.

Pre tento adapter je to v poriadku, pretoze logika je mala.

---

## 8. `devices.json` navrh

Aktualny room config je:

```text
raspberry_pi/config/rooms/room1/devices.json
```

Aktualne obsahuje:

- `motors`
- `relays`

Navrhovane rozsirenie:

```json
{
  "motors": [],
  "relays": [],
  "covers": [
    {
      "id": "cover_1",
      "name": "Roleta 1",
      "type": "cover",
      "topic": "room1/cover/1",
      "nodeId": "Room1_Shelly_Covers",
      "coverId": 0,
      "supportsPosition": true,
      "heartbeatTopic": "room1/system/heartbeat",
      "failSafeAction": "CLOSE",
      "stopAction": "STOP"
    },
    {
      "id": "cover_2",
      "name": "Roleta 2",
      "type": "cover",
      "topic": "room1/cover/2",
      "nodeId": "Room1_Shelly_Covers",
      "coverId": 1,
      "supportsPosition": true,
      "heartbeatTopic": "room1/system/heartbeat",
      "failSafeAction": "CLOSE",
      "stopAction": "STOP"
    }
  ]
}
```

## 8.1 Compatibility note

`POST /api/devices` dnes validuje, ze config obsahuje aspon jeden z klucov:

```text
motors
relays
lights
```

Pre plnu podporu treba povolit aj:

```text
covers
```

Kym sa backend neupravi, config by mal stale obsahovat aspon prazdne `motors`
alebo `relays`, inak save endpoint vrati chybu.

## 8.2 Nemenit topic na user-facing nazov

User-facing text moze byt slovensky:

```text
Roleta vstup
Zaluzia kotol
Opona scena
```

MQTT topic ma ostat stabilny a ASCII:

```text
room1/cover/1
```

Nemenit topic pri kazdej zmene nazvu vo frontende.

---

## 9. Backend zmeny pre plnu implementaciu

Tato sekcia popisuje buduce zmeny. Zatial sa nekoduju.

## 9.1 `commands.py`

Upravit validaciu `POST /api/devices`:

Aktualne:

```text
motors / relays / lights
```

Navrhovane:

```text
motors / relays / lights / covers
```

## 9.2 `MQTTActuatorStateStore`

Aktualny store vie hlavne:

- `ON`,
- `OFF`,
- motor direction,
- motor speed.

Pre cover treba pridat:

- `cover_state`: `OPEN`, `CLOSED`, `OPENING`, `CLOSING`, `STOPPED`, `UNKNOWN`
- `cover_position`: number alebo `null`
- `cover_target`: number alebo `null`
- `cover_calibrated`: boolean alebo `null`

Odporucane mapovanie prikazov:

| Command     | Desired cover state                     |
| ----------- | --------------------------------------- |
| `OPEN`    | `OPENING`                             |
| `CLOSE`   | `CLOSING`                             |
| `STOP`    | `STOPPED`                             |
| `POS:<n>` | `MOVING_TO_POSITION` + target `<n>` |

Feedback `OK` sam o sebe neznamena, ze roleta uz dosla. Znamena iba, ze cover
uzol prikaz prijal. Skutocny finalny stav ma prist zo state topicu.

## 9.3 `MQTTMessageHandler`

Pridat routing pre:

```text
room1/cover/+/state
```

alebo vseobecne:

```text
<room_id>/cover/<id>/state
```

Tento state event by mal ist do `MQTTActuatorStateStore`, nie iba do
`scene_parser.register_mqtt_event(...)`.

Zaroven je dobre state topic ponechat dostupny aj pre `mqttMessage`
prechody v scenach. Moznosti:

1. update-nut store a potom stale forwardnut event do scene parsera,
2. forwardnut iba ak aktivna scena potrebuje transition eventy.

Jednoduchsia a konzistentna varianta je prva.

## 9.4 Raspberry Pi heartbeat publisher

Pridat maly centralny heartbeat publisher:

```text
room1/system/heartbeat -> PING
```

Odporucane parametre v `config.ini`:

```ini
[MQTT]
system_heartbeat_interval_s = 5
```

Heartbeat ma bezat stale, kym je `MuseumController` zdravy a MQTT client je
pripojeny. Nie je naviazany na aktivnu scenu.

## 9.5 `room1/STOP`

Backend uz `room1/STOP` publikuje v `MuseumController.broadcast_stop()`.
Pre Shelly/Waveshare adapter netreba menit backend, iba zabezpecit, ze cover
uzol subscribuje `room1/STOP` a vykona `Cover.Stop` alebo ekvivalentne
vypnutie oboch smerovych rele.

---

## 10. Frontend zmeny pre plnu implementaciu

Tato sekcia popisuje buduce zmeny. Zatial sa nekoduju.

## 10.1 `useDevices.js`

Aktualne vracia:

```text
devices
motors
relays
```

Navrhnut:

```text
devices
motors
relays
covers
```

`devices` ma obsahovat vsetky tri skupiny.

## 10.2 `CommandsView.jsx`

Pridat novu sekciu:

```text
Rolety / Zaluziove pohony
```

Renderovat `CoverCard` pre kazdy item z `covers`.

## 10.3 `CoverCard.jsx`

Novy komponent ma mat minimalne:

- tlacidlo `Otvorit` -> `OPEN`
- tlacidlo `Stop` -> `STOP`
- tlacidlo `Zatvorit` -> `CLOSE`

Ak `supportsPosition = true`:

- slider alebo numeric input `0..100`,
- command `POS:<n>`.

Zobrazenie runtime stavu:

- `OPENING`
- `CLOSING`
- `OPEN`
- `CLOSED`
- `STOPPED`
- percento, ak je dostupne.

## 10.4 `useDevicePalette.js`

Pridat `coverItems`:

```text
quickMessages = ["OPEN", "CLOSE", "STOP", "POS:50"]
```

`POS:50` zobrazovat iba pre `supportsPosition = true`.

## 10.5 `EditorPalette.jsx`

Pridat novu sekciu:

```text
Rolety
```

Ikona moze byt z `lucide-react`, napr. `Blinds`, ak je v pouzitej verzii
dostupna. Ak nie, docasne pouzit neutralnu ikonu podobnu motorom.

## 10.6 `useDeviceRuntimeState.js`

Dnes motory formatuju direction + speed, relays iba `ON/OFF`.

Pre `device.type === "cover"` treba zobrazit:

- `cover_state`,
- `cover_position`,
- `cover_target`,
- fallback na `confirmed_state`, ak este nie je implementovany cover store.

---

## 11. Scene JSON priklady

## 11.1 Otvorenie rolety pri starte stavu

```json
{
  "sceneId": "cover_open_test",
  "version": "1.0",
  "initialState": "OPEN_COVER",
  "states": {
    "OPEN_COVER": {
      "onEnter": [
        {
          "action": "mqtt",
          "topic": "room1/cover/1",
          "message": "OPEN"
        }
      ],
      "transitions": [
        {
          "type": "timeout",
          "delay": 10,
          "goto": "END"
        }
      ]
    },
    "END": {
      "onEnter": [
        {
          "action": "mqtt",
          "topic": "room1/cover/1",
          "message": "STOP"
        }
      ]
    }
  }
}
```

## 11.2 Pozicia po kalibracii

```json
{
  "action": "mqtt",
  "topic": "room1/cover/1",
  "message": "POS:50"
}
```

## 11.3 Zatvorenie pri konci sceny

```json
{
  "action": "mqtt",
  "topic": "room1/cover/1",
  "message": "CLOSE"
}
```

---

## 12. Manualne MQTT testy

Pred zapojenim do scen otestovat cez broker.

## 12.1 Subscribe na feedback

```bash
mosquitto_sub -h <broker_ip> -t 'room1/cover/1/#' -v
```

## 12.2 Otvorit

```bash
mosquitto_pub -h <broker_ip> -t 'room1/cover/1' -m 'OPEN'
```

Ocakavane:

```text
room1/cover/1/feedback OK
room1/cover/1/state {"state":"opening",...}
```

## 12.3 Zastavit

```bash
mosquitto_pub -h <broker_ip> -t 'room1/cover/1' -m 'STOP'
```

## 12.4 Zatvorit

```bash
mosquitto_pub -h <broker_ip> -t 'room1/cover/1' -m 'CLOSE'
```

## 12.5 Global stop

```bash
mosquitto_pub -h <broker_ip> -t 'room1/STOP' -m 'STOP'
```

Ocakavane:

```text
Cover.Stop alebo vypnutie oboch smerovych rele pre vsetky cover vystupy
```

## 12.6 Heartbeat fail-safe test

1. Spustit Shelly script, Waveshare cover firmware alebo ESPHome cover node.
2. Posielat heartbeat:

```bash
mosquitto_pub -h <broker_ip> -t 'room1/system/heartbeat' -m 'PING'
```

3. Prestat posielat heartbeat.
4. Po `HEARTBEAT_TIMEOUT_MS` overit, ze cover uzol vykona `CLOSE`.

---

## 13. Testovaci plan v repozitari

Ked sa bude implementovat kod, doplnit testy.

## 13.1 Python unit testy

Rozsirit alebo pridat test vedla:

```text
raspberry_pi/tests/test_mqtt_feedback_state.py
```

Testovat:

- `OPEN` vytvori desired cover state `OPENING`,
- `CLOSE` vytvori desired cover state `CLOSING`,
- `STOP` vytvori desired cover state `STOPPED`,
- `POS:50` ulozi target position `50`,
- `ERROR` feedback neprepise confirmed stav,
- state topic JSON aktualizuje `cover_state` a `cover_position`.

## 13.2 Frontend manual test

Overit:

- `covers` sa nacitaju z `/api/devices`,
- Commands view zobrazi novu sekciu,
- `CoverCard` posiela spravne MQTT payloady,
- Scene Editor paleta ponuka `OPEN`, `CLOSE`, `STOP`, `POS:50`,
- runtime state sa aktualizuje cez Socket.IO event
  `device_runtime_state_update`.

## 13.3 Runtime test na Raspberry Pi

Overit:

- Shelly online status sa zobrazi v `connected_devices`,
- manualny `OPEN` vrati `OK`,
- manualny `CLOSE` vrati `OK`,
- `room1/STOP` zastavi pohyb,
- strata heartbeat zatvori cover,
- po obnove MQTT spojenia Shelly znova publikuje `online`.

---

## 14. Bezpecnostne pravidla

## 14.1 Elektricka cast

230 V cast musi zapojit elektrikarsky sposobilá osoba. Systemovy kod a MQTT
protokol nesmie byt jedinou ochranou pred nespravnym spinanim smerov.

## 14.2 Smerove blokovanie

Smerove blokovanie musi riesit Shelly cover rezim alebo certifikovana
elektroinstalacia. Nepouzivat dve nezavisle rele topic-y pre `open` a `close`.

## 14.3 Manualny vypinac

Ak je pri pohone fyzicky vypinac:

- musi byt kompatibilny so Shelly cover zapojenim,
- jeho input mode musi byt nastaveny podla realneho typu tlacidla/spinaca,
- treba otestovat, ze manualne ovladanie a MQTT ovladanie sa nebiju.

## 14.4 Pohyb pri strate riadenia

Fail-safe zatvorenie pri strate MQTT je poziadavka, ale stale je to aktivny
pohyb. Pred zapnutim tejto policy treba potvrdit, ze zatvaranie nemoze ohrozit
navstevnika, obsluhu alebo exponat.

---

## 15. Rozhodnutia na potvrdenie pred kodom

Pred implementaciou treba potvrdit:

1. Presny cover hardware: Shelly, Waveshare Arduino firmware alebo Waveshare ESPHome.
2. Pocet fyzickych pohonov.
3. Ci ma jeden Pro/Waveshare modul ovladat jeden, dva alebo viac pohonov.
4. Ci je pozicne ovladanie `POS:<n>` povinne alebo staci `OPEN/CLOSE/STOP`.
5. Ci `room1/STOP` ma pre cover znamenat `STOP` alebo `CLOSE`.
6. Heartbeat timeout: odporucane `30 s`.
7. Ci bude Wi-Fi vypnute a pouzije sa iba LAN.
8. Finalne MQTT topicy, odporucane `room1/cover/1`, `room1/cover/2`.
9. Pri Waveshare variante: ci bude dedikovana doska pre covers alebo sa budu
   zdielat rele s existujucimi svetlami/efektami.

---

## 16. Implementacny checklist

## 16.1 Shelly

- kupit `Shelly Pro Dual Cover / Shutter PM`,
- zapojit pohony elektrikarsky,
- nastavit LAN,
- nastavit MQTT broker,
- nastavit cover mode,
- kalibrovat, ak sa bude pouzivat `POS:<n>`,
- nahrat adapter script,
- zapnut autostart scriptu.

## 16.2 Backend

- povolit `covers` v `/api/devices` validacii,
- pridat heartbeat publisher,
- rozsirit actuator state store pre cover stavy,
- spracovat `roomX/cover/+/state`,
- doplnit testy.

## 16.3 Waveshare Arduino firmware

- vytvorit novu kopiu LAN relay firmveru:
  `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_COVERS/`,
- zmenit `CLIENT_ID` na `Room1_Covers_Ctrl`,
- pridat `CoverDevice` mapovanie rele parov,
- pridat parser `room1/cover/<id>`,
- pridat mutual exclusion a dead-time,
- pridat max runtime pre pohyb,
- pridat state topic `room1/cover/<id>/state`,
- zachovat `room1/STOP` ako vypnutie oboch smerov.

## 16.4 Waveshare ESPHome

- zobrat ESPHome device profil pre `Waveshare ESP32-S3-ETH-8DI-8RO`,
- pouzit W5500 piny `GPIO15/13/14/16/12`,
- pouzit I2C `GPIO42/41` a `pca9554` address `0x20`,
- rele pary definovat ako switch-e s `interlock` a `interlock_wait_time`,
- pridat `time_based` cover,
- pridat MQTT `birth_message`/`will_message`,
- pridat `mqtt.on_message` adapter pre `room1/cover/<id>` a `/feedback`,
- pridat heartbeat fail-safe.

## 16.5 Frontend

- rozsirit `useDevices`,
- pridat `CoverCard`,
- rozsirit `CommandsView`,
- rozsirit `useDevicePalette`,
- rozsirit `EditorPalette`,
- rozsirit runtime state display.

## 16.6 Dokumentacia

Po implementacii aktualizovat:

- `docs/04_mqtt_protocol.md`,
- `docs/09_dashboard_api.md`,
- `docs/12_physical_installation.md`,
- tento dokument.

---

## 17. Externe referencie

- Shelly Cover component:
  `https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Cover/`
- Shelly MQTT component:
  `https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Mqtt/`
- Shelly Script language features:
  `https://shelly-api-docs.shelly.cloud/gen2/Scripts/ShellyScriptLanguageFeatures/`
- Shelly Pro Dual Cover PM device:
  `https://shelly-api-docs.shelly.cloud/gen2/Devices/Gen2/ShellyProDualCoverPM/`
- Waveshare ESP32-S3-ETH-8DI-8RO ESPHome device profile:
  `https://devices.esphome.io/devices/waveshare-esp32-s3-eth-8di-8ro/`
- Waveshare ESP32-S3-ETH-8DI-8RO wiki:
  `https://www.waveshare.com/wiki/ESP32-S3-ETH-8DI-8RO`
- ESPHome time based cover:
  `https://esphome.io/components/cover/time_based/`
- ESPHome MQTT component:
  `https://esphome.io/components/mqtt/`
- ESPHome GPIO switch interlock:
  `https://esphome.io/components/switch/gpio/`
