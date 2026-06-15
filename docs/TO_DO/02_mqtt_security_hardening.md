# TODO: MQTT broker auth a postupny prechod na MQTTS

Date: 2026-06-04

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short date or note if useful, and do not leave completed work only in chat or
git history.

Tento dokument je implementacny navod pre zabezpecenie MQTT vrstvy bez zmeny
topic kontraktu, scen, SceneGen palety alebo modularity ESP32 zariadeni.

Hlavny ciel:

- nahodny klient sa nema vediet pripojit na broker iba preto, ze pozna IP adresu,
- prihlaseny Web ma nadalej posielat prikazy cez Flask API, nie priamo na MQTT broker,
- Raspberry Pi backend a ESP32 uzly sa maju overit voci brokeru,
- existujuce topicy maju ostat rovnake,
- zmena sa ma dat nasadzovat po fazach, kde kazda faza ma vlastny test.

## Aktualne zhodnotenie

Aktualny stav repozitara:

- `raspberry_pi/broker/mosquitto.conf` povoluje anonymous pristup na MQTT `1883`.
- Ten isty subor povoluje anonymous WebSocket listener `9001`.
- `raspberry_pi/utils/mqtt/mqtt_client.py` nepouziva MQTT username/password.
- `raspberry_pi/config/config.ini.example` nema MQTT auth ani TLS nastavenia.
- ESP32 Arduino firmwary pouzivaju `PubSubClient.connect(CLIENT_ID, willTopic, ...)`
  bez mena a hesla.
- Dashboard uz ma vlastnu HTTP/Socket.IO Basic Auth, ale to nechrani MQTT broker.
- Web dashboard v aktualnom flow nevyzera, ze by potreboval priamy MQTT WebSocket
  listener; pouziva Flask API a Socket.IO.

Verdikt:

Aktualny system je funkcny, ale broker je otvoreny pre kazde zariadenie v sieti.
Topic-y nie su bezpecnostny mechanizmus. Spravny prvy krok je vypnut
anonymous pristup a pridat MQTT credentials. MQTTS/TLS je druhy krok po tom, ako
je username/password stabilne nasadene na Raspberry Pi aj na ESP32.

## Bezpecnostny model

### Co ma riesit v1

V1 ma riesit pristup k brokeru:

```text
bez prihlasenia -> broker klienta odmietne
so spravnym MQTT menom/heslom -> system funguje ako dnes
```

Toto brani nahodnemu klientovi publikovat prikazy po sieti.

### Co v1 este neriesi

Username/password bez TLS este nesifruje komunikaciu. Ak niekto vie aktivne
odpocuvat LAN, moze teoreticky zachytit MQTT credentials. Preto je MQTTS planovane
ako dalsia faza, nie ako prvy velky skok.

### Co nemenit

Nemenit existujuce MQTT topicy:

```text
room1/light/1
room1/motor1
room1/effects/group1
room1/scene
room1/start_scene
room1/STOP
devices/<client_id>/status
<command_topic>/feedback
<command_topic>/state
```

Bezpecnost sa nema opierat o nazov topicu alebo nazov ESP32. Prvy stabilny model
je: kto nema platnu MQTT identitu, nepripoji sa.

## Kompatibilita s existujucimi TODO planmi

### `03_mqtt_state_reporting_rework_DONE.md`

Kompatibilne, ak sa dodrzia tieto pravidla:

- auth/TLS nesmie menit command, feedback ani state topic-y,
- `/state` topic-y ostanu retained,
- command a feedback topic-y ostanu non-retained,
- `MQTTMessageHandler` musi po buducej state rework faze stale routovat:
  `device status -> feedback -> state report -> scene/start_scene -> scene parser`,
- ACL, ak sa neskor prida, musi povolit aj `<room_id>/#`, `/feedback`,
  `/state` a `devices/+/status`.

Riziko:

- prilis uzke ACL by mohlo rozbit nove `/state` reporty alebo buduce cover topicy.
- Preto ACL nie je prva produkcna faza. Najprv len username/password.

### `docs/TO DO/07_cover_roleta_support.md`

Kompatibilne, ak buduce Shelly/Waveshare cover uzly dostanu MQTT credentials
rovnako ako ESP32.

Pozor na tieto topicy:

```text
room1/cover/<id>
room1/cover/<id>/feedback
room1/cover/<id>/state
room1/system/heartbeat
devices/Room1_Shelly_Covers/status
```

ACL musi tieto topicy pustit, inak sa pokazi cover feedback/state alebo
heartbeat fail-safe.

### `docs/TO DO/05_cec_display_power_control.md`

Kompatibilne. Ak sa prida manualny topic:

```text
room1/display
```

tak ACL musi povolit jeho publish/subscribe pre Raspberry Pi controller. CEC logika
nie je zavisla od MQTT TLS, iba od toho, ci sa controller vie pripojit na broker.

### `docs/TO DO/01_reliability_stability_future_work.md`

S tymto planom suvisia hlavne dve veci:

- `device_timeout = 25` je aktualny kompromis pre 5s ESP status heartbeat
  bez prilis rychlych fake offline stavov,
- dashboard credentials su stale hardcoded v `raspberry_pi/Web/config.py`.

Odporucanie:

- Ak TLS/reconnecty v praxi sposobia kratke vypadky, znovu zvazit
  `device_timeout` a pripadne ho zvysit nad 25s podla realnych heartbeat
  intervalov.
- Dashboard Basic Auth je samostatna vrstva. Netreba ju miesat s MQTT auth, ale
  produkcne credentials by tiez nemali byt `admin/admin`.

### SceneGen V2 a `devices.json`

Kompatibilne, ak sa nemenia topic-y v `devices.json`.

SceneGen paleta cita zariadenia z Flask API a vklada MQTT topic + message do
sceny. MQTT auth ma byt pod nou, v runtime MQTT klientovi a brokri. SceneGen nema
vediet ani riesit MQTT heslo.

### Legacy cleanup

Pouzivat aktualny room config:

```text
raspberry_pi/config/rooms/<room_id>/devices.json
```

Neopierat novy security plan o legacy:

```text
raspberry_pi/scenes/<room_id>/devices.json
```

## Navrhovany cielovy stav

### Broker

Mosquitto:

```conf
listener 1883 0.0.0.0
protocol mqtt
allow_anonymous false
password_file /etc/mosquitto/passwd
```

WebSocket listener:

- vypnut, ak ho nic nepouziva,
- alebo zabezpecit rovnakym `allow_anonymous false` a `password_file`.

### Raspberry Pi backend

Backend sa pripaja s credentials z `config.ini`:

```ini
[MQTT]
broker_ip = 127.0.0.1
port = 1883
username = museum_rpi
password = CHANGE_ME
```

Ak su username/password prazdne, dev rezim zostane kompatibilny s anonymous
brokerom.

### ESP32

ESP32 firmware ma v konfiguracii:

```cpp
const bool MQTT_AUTH_ENABLED = true;
const char* MQTT_USER = "museum_esp";
const char* MQTT_PASSWORD = "CHANGE_ME";
```

Pri zapnutom auth sa pouzije PubSubClient overload s username/password a LWT:

```cpp
client.connect(
  CLIENT_ID,
  MQTT_USER,
  MQTT_PASSWORD,
  willTopic.c_str(),
  0,
  true,
  "offline"
)
```

Pri vypnutom auth sa ponecha dnesny sposob pripojenia.

### Modularita topicov vo v1

V1 cielene nerobi zoznam povolenych command topicov v Mosquitto ACL ani v
Raspberry Pi backende.

Princip:

- broker overi, ci klient ma platne MQTT credentials,
- po prihlaseni moze Raspberry Pi publikovat lubovolny topic ako dnes,
- po prihlaseni moze button uzol publikovat svoj trigger topic ako dnes,
- po prihlaseni moze novy ESP32 uzol subscribnut topicy, ktore pozna jeho
  firmware,
- samotne ESP32 dalej ignoruje spravy, ktore nesubscribuje alebo nevie
  spracovat,
- pridanie noveho topicu do firmware alebo sceny nevyzaduje zmenu broker ACL.

Toto je zamerne. V1 je ochrana proti nahodnemu klientovi v LAN, ktory pozna IP
brokera, ale nema prihlasenie. Nie je to per-topic autorizacny system.

Ak sa neskor zavedie ACL, odporucany modularny tvar je stale room-level, napriklad
`room1/#` a `devices/#`, nie zoznam konkretnych `room1/light/1`,
`room1/motor1` atd. Per-device ACL je bezpecnejsi, ale patri az do samostatnej
fazy po stabilizacii auth, lebo moze zbytocne brzdit onboarding novych ESP32 a
novych topicov.

## Subory, ktorych sa plan tyka

### Raspberry Pi backend

Upravit:

- `.gitignore`
- `raspberry_pi/config/config.ini.example`
- `raspberry_pi/utils/config_manager.py`
- `raspberry_pi/utils/mqtt/mqtt_client.py`
- `raspberry_pi/utils/service_container.py`
- `raspberry_pi/broker/mosquitto.conf`
- `raspberry_pi/install.sh`
- `raspberry_pi/install_offline.sh`
- `docs/04_mqtt_protocol.md`
- `docs/10_museum_backend_setup.md`
- `docs/11_esp32_firmware_setup.md`

Vytvorit:

- volitelne `raspberry_pi/config/config.local.ini.example`
- `raspberry_pi/utils/mqtt/mqtt_security.py`
- `raspberry_pi/tests/test_mqtt_security_config.py`
- `raspberry_pi/broker/mosquitto.acl.example`
- `raspberry_pi/broker/README_SECURITY.md`
- volitelne `raspberry_pi/tools/mqtt_auth_smoke_test.sh`

Poznamka k modularite:

`mqtt_security.py` ma byt mala helper vrstva, ktora aplikuje auth/TLS na Paho
client. `MQTTClient` ma zostat hlavne wrapper pre connect/reconnect/publish.
`ConfigManager` ma iba nacitat config, nie riesit TLS alebo broker policy.

### ESP32 Arduino firmwary

Upravit konfiguraciu a MQTT connect v:

- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_button/config.h`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_button/config.cpp`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_button/mqtt_manager.cpp`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS/config.h`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS/config.cpp`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS/mqtt_manager.cpp`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_RELAY/config.h`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_RELAY/config.cpp`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_RELAY/mqtt_manager.cpp`
- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/config.h`
- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/config.cpp`
- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/mqtt_manager.cpp`

Volitelne vytvorit neskor:

- `esp32/devices/*/ArduinoIDE/*/secrets.h.example`

Ale prva faza moze ostat v style aktualneho repozitara, teda konfiguracia v
`config.cpp`. Realne hesla nepisat do dokumentacie ani do verejneho commitu.

### ESPHome varianty

Ak sa pouziju ESPHome YAML:

- `esp32/devices/wifi/EspHome/*.yaml`

Pouzit ESPHome `secrets.yaml` a MQTT:

```yaml
mqtt:
  broker: 192.168.0.127
  username: !secret mqtt_user
  password: !secret mqtt_password
```

## Ako s tym pracovat, ked implementuje AI

Kazdu fazu brat ako samostatny mini-task. AI ma najprv urobit iba zmeny pre
aktualnu fazu, spustit lokalne testy, a potom si od teba vypytat vystup z Pi
alebo ESP32, ak ho nevie overit sama.

Zakladny cyklus:

1. AI upravi kod alebo dokumentaciu iba pre jednu fazu.
2. AI napise, co mas spustit na Raspberry Pi alebo v Arduino IDE.
3. Ty neposielas hesla. Posielas iba logy s vymazanym heslom alebo screenshot
   relevantnej chyby.
4. AI vyhodnoti log a az potom sa ide na dalsiu fazu.

Co typicky poslat AI spat:

- vystup `systemctl status mosquitto --no-pager`,
- posledne riadky `journalctl -u mosquitto -n 80 --no-pager`,
- vystup `journalctl -u museum-system -n 120 --no-pager`,
- serial monitor ESP32 pri MQTT connecte,
- vysledok manualneho `mosquitto_pub` / `mosquitto_sub` testu,
- zoznam zariadeni, ktore su fyzicky preflashovane a otestovane.

Co neposielat:

- realne MQTT heslo,
- obsah realneho `config.local.ini`,
- obsah `/etc/mosquitto/passwd`,
- private key alebo CA private key pri MQTTS faze.

## Implementacne fazy

## Faza 0 - Inventar a rozhodnutia

Status: priprava, bez kodu.

Rozhodnut:

- ci sa v prvej produkcnej verzii pouzije jedno spolocne heslo pre vsetky ESP32,
  alebo unikatne heslo pre kazdy typ uzla,
- ci je Mosquitto WebSocket listener `9001` realne pouzivany,
- ci broker ostava dostupny len v LAN,
- ako sa bude bezpecne zapisovat realne heslo na Pi a do ESP32 konfiguracie.

Odporucanie pre v1:

- `museum_rpi` pre Raspberry Pi controller,
- `museum_esp` pre ESP32/Shelly/Waveshare uzly,
- bez ACL v prvej produkcnej faze,
- WebSocket listener vypnut, ak sa nepotvrdi jeho pouzitie,
- secret storage default: `raspberry_pi/config/config.local.ini` v `.gitignore`.

Rozhodnutie pre implementaciu secret storage:

- `config.ini.example` ostava template v repo,
- `config.ini` nesmie obsahovat produkcne heslo,
- `config.local.ini` bude lokalny override s realnym heslom a bude ignorovany
  gitom,
- `ConfigManager` nacita najprv `config.ini` a potom volitelne
  `config.local.ini`, kde lokalny subor prepise iba nastavene hodnoty,
- konflikt sa riesi tak, ze neprazdna hodnota v `config.local.ini` prepise base
  hodnotu z `config.ini`; prazdna hodnota v `config.local.ini` base hodnotu
  nevymaze,
- ak bude niekedy treba hodnotu z base configu vedome vymazat, zaviest na to
  explicitny sentinel alebo samostatny config flag, nie tichy prazdny string,
- AI nesmie zapisat realne heslo do trackovaneho suboru.

Overenie WebSocket listenera `9001`:

```bash
sudo ss -tlnp | grep ':9001'
sudo journalctl -u mosquitto -n 80 --no-pager
```

V dashboarde otvorit browser DevTools -> Network a pozriet, ci sa nepouziva
priame pripojenie na `ws://<broker>:9001`. Aktualne ocakavanie je, ze dashboard
pouziva Flask/Socket.IO, nie Mosquitto WebSocket.

Co ma poslat clovek AI po Faze 0:

- zoznam ESP32/Shelly/Waveshare uzlov, ktore existuju,
- potvrdenie, ktore uzly vies realne preflashovat,
- vystup `sudo ss -tlnp | grep ':9001'`,
- informaciu, ci v Network tabe dashboardu vidno priamy `:9001` WebSocket,
- potvrdenie, ze sa pouzije `config.local.ini` ako default secret storage.

Test:

```bash
mosquitto_sub -h <broker_ip> -t '#' -v
mosquitto_pub -h <broker_ip> -t 'room1/scene' -m 'START'
```

Toto len potvrdi aktualny otvoreny stav pred zmenou.

Acceptance:

- Je jasne, ktore zariadenia treba preflashovat alebo nakonfigurovat.
- Je jasne, ci treba riesit WebSocket listener.
- Je potvrdene, ze produkcne heslo pojde do ignorovaneho `config.local.ini`.

## Faza 1 - Volitelne MQTT credentials v Raspberry Pi kode

Status: bezpecna zmena, broker moze ostat anonymous.

Upravit:

- `config.ini.example`
- `ConfigManager.get_all_config()`
- `MQTTClient.__init__()`
- `MQTTClient._setup_mqtt_client()`
- `ServiceContainer._init_mqtt()`

Navrhovane config keys:

```ini
[MQTT]
username =
password =
tls_enabled = false
tls_ca_file =
tls_insecure = false
```

V interne vratenej flat config mape nepouzivat hole mena `username` a
`password`. Pouzit prefixovane kluce:

```python
mqtt_username
mqtt_password
mqtt_tls_enabled
mqtt_tls_ca_file
mqtt_tls_insecure
```

Inak by sa neskor lahko pomiesali s Web dashboard credentials alebo inou
aplikacnou autentifikaciou.

Do produkcneho repozitara necommitovat realne heslo. Aktualne je
`raspberry_pi/config/config.ini` trackovany subor, takze pred realnou
implementaciou pouzit tento default:

- pridat `raspberry_pi/config/config.local.ini` do `.gitignore`,
- vytvorit iba `raspberry_pi/config/config.local.ini.example`,
- realny `config.local.ini` vytvara operator na Pi alebo lokalne mimo commitu,
- `ConfigManager` nacita `config.ini` a potom volitelny `config.local.ini`.

Alternativy ako root-owned `/etc/museum-system/mqtt.env` alebo odtrackovanie
realneho `config.ini` su tiez mozne, ale pre tento projekt je `config.local.ini`
najjednoduchsia implementacna cesta.

Pri citani hesiel z INI pozor na specialne znaky. Python `ConfigParser` pouziva
interpolaciu cez `%`, takze silne heslo s percentom moze sposobit chybu citania.
Bud citat heslo cez `raw=True`, pouzit `RawConfigParser`, alebo odporucit
URL-safe hesla bez `%`, `;` a `#` v prvej jednoduchej verzii.

V tejto faze implementovat iba username/password. TLS kluce sa mozu nacitat ako
placeholder pre buducu fazu, ale nesmie sa tym komplikovat connect flow.

Navrhovany helper:

```text
raspberry_pi/utils/mqtt/mqtt_security.py
```

Zodpovednosti helpera:

- zistit, ci credentials existuju,
- zavolat `client.username_pw_set(username, password)`,
- validovat, ze `password` bez `username` je config chyba,
- nikdy nelogovat heslo,
- pri zlom prihlaseni logovat len typ chyby, nie credentials,
- neskor doplnit `client.tls_set(...)`.

Implementacny detail v `MQTTClient.connect()`:

- `username_pw_set(...)` musi prebehnut pred prvym `connect(...)`,
- ak broker odmietne prihlasenie a `_on_connect` dostane nenulovy `rc`, klient
  nesmie nechat bezat staru Paho network loop thread donekonecna,
- po neuspesnom connect/timeoute je vhodne zavolat `loop_stop()` a
  `disconnect()` best-effort pred dalsim retry,
- return code pre bad username/password alebo unauthorized ma byt v logu
  rozpoznatelny, aby operator nehladal problem vo WiFi.

Testy:

```bash
cd raspberry_pi
source venv/bin/activate
pytest -q tests/test_mqtt_security_config.py
python3 tests/run_quick_tests.py
```

Manualny test:

- broker stale anonymous,
- spustit backend s prazdnym username/password,
- spustit backend s vyplnenym username/password,
- v oboch pripadoch sa musi pripojit.

Acceptance:

- Pri prazdnych credentials sa spravanie nezmeni.
- Pri vyplnenych credentials Paho client vola `username_pw_set`.
- Logs neobsahuju plaintext heslo.

## Faza 2 - Volitelne MQTT credentials v ESP32 firmwari

Status: bezpecna zmena, broker moze stale ostat anonymous.

Upravit v kazdom Arduino firmware:

- `config.h`
- `config.cpp`
- `mqtt_manager.cpp`

Pridat:

```cpp
extern bool MQTT_AUTH_ENABLED;
extern const char* MQTT_USER;
extern const char* MQTT_PASSWORD;
```

Do `config.cpp`:

```cpp
bool MQTT_AUTH_ENABLED = false;
const char* MQTT_USER = "";
const char* MQTT_PASSWORD = "";
```

V `connectToMqtt()` pouzit helper alebo lokalnu vetvu:

```cpp
bool connected;
if (MQTT_AUTH_ENABLED) {
  connected = client.connect(
    CLIENT_ID,
    MQTT_USER,
    MQTT_PASSWORD,
    willTopic.c_str(),
    0,
    true,
    "offline"
  );
} else {
  connected = client.connect(CLIENT_ID, willTopic.c_str(), 0, true, "offline");
}
```

Pozor:

- zachovat LWT `offline`,
- zachovat retained `online` status,
- nemenit `CLIENT_ID`,
- nemenit `BASE_TOPIC_PREFIX`,
- nemenit subscriptions.

Implementacny edge case:

- aktualne relay a motor firmwary po `MAX_MQTT_ATTEMPTS` restartuju ESP32,
- pri zlom MQTT hesle by to vytvorilo restart loop,
- pocas auth rollout-u rozlisit `client.state()` pre auth chyby ako bad
  credentials alebo unauthorized,
- pri trvalo zlom hesle prejst do dlhsieho backoff/degraded rezimu,
- rychly restart po max pokusoch nechat iba pre prechodne sietove chyby.

PubSubClient orientacna logika:

```cpp
int rc = client.state();
bool authFailure = (rc == MQTT_CONNECT_BAD_CREDENTIALS ||
                    rc == MQTT_CONNECT_UNAUTHORIZED);

if (authFailure) {
  // Trvala konfiguracna chyba. Nerebootovat stale dokola.
  mqttRetryInterval = AUTH_FAILURE_RETRY_INTERVAL; // napriklad 5 minut
  mqttAttempts = 0;
  mqttConnected = false;
  signalMqttAuthFailure(); // LED/debug podla konkretneho firmware
  return;
}

if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
  // Sietova chyba alebo broker nedostupny. Aj tu pocas rollout-u radsej
  // preferovat dlhy backoff pred agresivnym restart loopom.
  mqttRetryInterval = MAX_RETRY_INTERVAL;
  mqttAttempts = 0;
  return;
}
```

Poznamka:

- `client.connect(...) == false` je iba vseobecne zlyhanie,
- `client.state()` pomaha rozlisit MQTT CONNACK chyby,
- ak konkretna kniznica alebo stav nerozlisuje auth spolahlivo, bezpecny fallback
  je po viacerych neuspesnych pokusoch prejst do dlheho backoff rezimu namiesto
  restart loopu,
- do serial logu vypisat iba `rc`, nikdy nie heslo.

Rozsah testu zleho hesla:

- povinne otestovat aspon jeden reprezentativny build pre kazdy odlisny
  `connectToMqtt()` flow,
- minimalne pokryt WiFi relay, WiFi motors a LAN relay, pretoze tieto vetvy maju
  alebo mali restart po MQTT zlyhaniach,
- button firmware tiez otestovat, ak je dostupny, ale jeho riziko restart loopu
  je nizsie ako pri relay/motor vetvach,
- ak je konkretne fyzicke zariadenie nedostupne, otestovat rovnaky firmware na
  nahradnom ESP32 alebo zapisat, ze tento build nie je overeny,
- Faza 3 sa nema zapnut pre aktivnu miestnost, kym nie su aktivne buildy
  overene alebo vedome vyradene z rollout-u.

Manualne testy:

1. Broker anonymous stale povoleny.
2. Nahraj ESP32 s `MQTT_AUTH_ENABLED = false`.
3. Over `devices/<CLIENT_ID>/status = online`.
4. Nahraj ESP32 s `MQTT_AUTH_ENABLED = true`.
5. Over, ze sa stale pripoji.
6. Nahraj alebo nastav zle heslo a over, ze ESP32 nevytvara restart loop.
7. Over command + feedback:

```bash
mosquitto_sub -h <broker_ip> -t 'room1/#' -v
mosquitto_pub -h <broker_ip> -t 'room1/light/1' -m 'ON'
mosquitto_pub -h <broker_ip> -t 'room1/light/1' -m 'OFF'
```

Acceptance:

- ESP32 funguje s auth vypnutym aj zapnutym.
- LWT `offline` stale funguje pri odpojeni.
- Feedback topic-y sa nezmenili.

## Faza 3 - Mosquitto password_file a vypnutie anonymous MQTT

Status: prva realna ochrana brokeru.

Upravit:

- `raspberry_pi/broker/mosquitto.conf`
- `raspberry_pi/install.sh`
- `raspberry_pi/install_offline.sh`
- `raspberry_pi/broker/README_SECURITY.md`

Navrhovany Mosquitto config pre prvu produkcnu fazu:

```conf
listener 1883 0.0.0.0
protocol mqtt
allow_anonymous false
password_file /etc/mosquitto/passwd

# listener 9001
# protocol websockets
# allow_anonymous false
# password_file /etc/mosquitto/passwd
```

Password file vytvorit na Pi:

```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd museum_rpi
sudo mosquitto_passwd /etc/mosquitto/passwd museum_esp
sudo systemctl restart mosquitto
```

Do install skriptu nedavat realne hesla. Installer moze:

- blokovat nasadenie produkcneho Mosquitto configu, ak
  `/etc/mosquitto/passwd` neexistuje,
- nevypinat anonymous pristup, kym password file nie je pripraveny,
- vypisat explicitnu chybu a skoncit nenulovym exit kodom,
- vytvorit dev fallback iba po explicitnom potvrdeni operatora.

Installer pravidlo:

```text
if allow_anonymous false is target and /etc/mosquitto/passwd does not exist:
    print clear error
    do not copy production mosquitto.conf
    do not restart mosquitto with broken config
    exit 1
```

Pred kopirovanim produkcneho Mosquitto configu overit:

- `/etc/mosquitto/passwd` existuje,
- subor vie citat pouzivatel, pod ktorym bezi Mosquitto,
- config prejde `mosquitto -c <config> -v` v stagingu alebo pri docasne
  zastavenom brokeri; nebrat to ako cisty dry-run na bezacej produkcii,
- po restarte `systemctl status mosquitto` nehlasi chybu s password file,
- v pripade zlyhania sa instalacny skript zastavi s jasnou hlaskou.

Pri viacerych listeneroch si explicitne ujasnit Mosquitto auth scope:

- ak sa pouzije `per_listener_settings true`, musi mat kazdy listener vlastne
  `allow_anonymous false` a `password_file`,
- ak sa pouzije globalne nastavenie, musi byt overene, ze plati aj pre
  WebSocket listener,
- neponechat port `9001` anonymous, inak ostava bypass mimo portu `1883`.

Deployment politika pred vypnutim anonymous:

- ak nie je preflashovany alebo nakonfigurovany kazdy aktivny ESP32/Shelly uzol,
  Faza 3 sa odklada,
- docasny anonymous rezim je lepsi ako rozbita miestnost pocas akcie,
- firewall vynimka pre konkretne MAC/IP je iba nudzovy docasny workaround a ma
  byt zapisany v deployment poznamkach,
- nechat broker anonymous a zaroven tvrdit, ze v1 security je hotova, nie je
  akceptovatelne.

Rollback musi byt fyzicky dostupny pred zmenou:

- mat otvoreny SSH pristup na Raspberry Pi z tej istej LAN,
- idealne mat pri produkcnom prepnuti dostupny aj monitor/klavesnicu alebo inu
  lokalnu konzolu,
- mat pripraveny backup povodneho Mosquitto configu,
- vediet rychlo vratit `allow_anonymous true` a restartnut Mosquitto,
- nerobit Fazu 3 pocas ostrej akcie alebo bez cloveka pri instalacii.

Retained device status cleanup:

- retained spravy sa daju cistit iba publishom na konkretny topic,
- wildcard `devices/+/status` je platny pre subscribe, ale nie pre publish,
- pred smoke testom najprv pozorovat aktualne retained statusy:

```bash
mosquitto_sub -h <broker_ip> -u museum_rpi -P '<password>' -t 'devices/+/status' -v
```

- ak dashboard ukazuje stare zariadenie ako online, vycistit presny retained
  status topic:

```bash
mosquitto_pub -h <broker_ip> -u museum_rpi -P '<password>' -t 'devices/<CLIENT_ID>/status' -n -r
```

- po vycisteni nechat realne ESP32 znova publikovat `online`.

Co ma poslat clovek AI pred Fazou 3:

- potvrdenie, ze vsetky aktivne uzly su preflashovane alebo nakonfigurovane,
- vystup `ls -l /etc/mosquitto/passwd`,
- neposielat obsah `/etc/mosquitto/passwd`; staci existencia a prava cez `ls -l`,
- vystup `sudo systemctl status mosquitto --no-pager`,
- vystup `sudo journalctl -u mosquitto -n 80 --no-pager`.

Testy po zapnuti:

Bez hesla musi zlyhat:

```bash
mosquitto_pub -h <broker_ip> -t 'room1/light/1' -m 'ON'
```

S heslom musi prejst:

```bash
mosquitto_pub -h <broker_ip> -u museum_rpi -P '<password>' -t 'room1/light/1' -m 'ON'
```

Monitorovaci smoke test v samostatnom terminali:

```bash
mosquitto_sub -h <broker_ip> -u museum_rpi -P '<password>' -t '#' -v
```

Pouzit iba ako kratky test a ukoncit cez `Ctrl+C`. Ak sa neskor zavedie ACL,
nahradit `#` uzsim setom topicov, napriklad `room1/#` a `devices/+/status`.

Overit backend:

```bash
cd raspberry_pi
source venv/bin/activate
python3 main.py
```

Overit ESP32:

- status `online`,
- command `ON/OFF`,
- feedback,
- scene start cez `room1/scene START`,
- manual publish z dashboardu `/api/mqtt/send`.

Acceptance:

- Nahodny klient bez credentials sa nepripoji.
- Raspberry Pi controller sa pripoji.
- ESP32 uzly sa pripoja.
- Funkcia systemu je rovnaka ako pred zmenou.

Rollback:

```conf
allow_anonymous true
```

a restart Mosquitto. Kvoli bezpecnosti ma byt rollback docasny a zapisany v
deployment poznamkach.

## Faza 4 - Volitelne ACL po stabilizacii

Status: neskor, az ked auth funguje stabilne.

ACL nie je nutne pre prvy ciel "random klient sa nepripoji". Prilis skore ACL
moze rozbit modularitu a buduce topicy.

Minimalny room-level ACL priklad:

```conf
user museum_rpi
topic readwrite room1/#
topic read devices/+/status

user museum_esp
topic readwrite room1/#
topic write devices/+/status
```

Ak sa pouzije cover heartbeat alebo display control, stale sedi do `room1/#`.

Ak sa neskor zavedu per-device users:

- nespoliehat sa na user-facing nazov zariadenia,
- pouzit stabilny room prefix a node rolu,
- davat pozor na LWT `devices/<CLIENT_ID>/status`,
- dokumentovat, ktory user patri ktoremu firmware build-u.

Testy:

- `room1/light/1` command,
- `room1/light/1/feedback`,
- `room1/light/1/state` po state-reporting reworku,
- `devices/<client_id>/status`,
- `room1/scene`,
- `room1/start_scene`,
- `room1/STOP`,
- buduce `room1/cover/1`,
- buduce `room1/system/heartbeat`,
- buduce `room1/display`.

Acceptance:

- ACL nepridava ziadne specialne pravidlo viazane na jeden konkretny nazov ESP.
- Pridanie noveho topicu v room prefixe nevyzaduje edit Mosquitto ACL.

## Faza 5 - MQTTS/TLS proof of concept

Status: volitelne, az po username/password.

MQTTS pridava:

- sifrovanie MQTT komunikacie,
- ochranu MQTT hesla pred jednoduchym odpocuvanim,
- overenie, ze klient komunikuje so spravnym brokerom.

Navrhovany broker port:

```conf
listener 8883 0.0.0.0
protocol mqtt
allow_anonymous false
password_file /etc/mosquitto/passwd
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
```

Raspberry Pi Paho:

```python
client.tls_set(ca_certs=ca_file)
```

ESP32:

```cpp
WiFiClientSecure wifiClient;
PubSubClient client(wifiClient);
wifiClient.setCACert(ROOT_CA_CERT);
```

Nepouzivat `setInsecure()` ako finalne riesenie. Je prijatelne iba ako kratky
diagnosticky test, pretoze vypina overenie brokeru.

### Hostname a IP adresa certifikatu

Ak sa klienti pripajaju na broker cez IP adresu, server certifikat musi mat tuto
IP adresu v `subjectAltName`. Ak sa pripajaju cez DNS alebo `.local` meno, musi
mat v `subjectAltName` toto meno.

Pozor:

- Common Name uz nestaci ako spolahlive overenie mena,
- zmena z `192.168.x.x` na `museum-pi.local` meni poziadavku na certifikat,
- ESP32 aj Raspberry Pi backend musia pouzivat rovnaky host format, pre ktory je
  certifikat vystaveny,
- pri DHCP zmene IP moze TLS zlyhat, preto je pre MQTTS lepsie pouzit staticku
  IP alebo stabilne lokalne DNS meno.

### Cas a certifikaty

TLS certifikat ma platnost `not before` a `not after`. Ak Raspberry Pi alebo
ESP32 nema rozumny cas, overenie certifikatu moze zlyhat.

Pre offline/LAN muzeum su prakticke moznosti:

1. Raspberry Pi s RTC modulom, napriklad DS3231.
2. Raspberry Pi ako lokalny casovy zdroj v LAN, napriklad `chrony`.
3. ESP32 pred MQTT TLS pripojenim spravi SNTP sync z Raspberry Pi/routera.
4. Vlastna lokalna CA s dlhsou platnostou certifikatov.

Odporucanie:

- pred MQTTS vyriesit cas na Raspberry Pi,
- pri ESP32 cakat na SNTP sync pred TLS connectom,
- nepouzivat public Let's Encrypt pre izolovanu LAN instalaciu, ak RPi nema
  stabilny WAN/DNS/cas flow.

### Latencia

TLS handshake sa deje hlavne pri connect/reconnecte. Pri otvorenom MQTT spojeni
by latencia samotnych command sprav nemala dramaticky narast.

Po MQTTS zmerat:

- cas od bootu ESP32 po `online`,
- cas reconnectu po vypadku WiFi/LAN,
- command -> feedback latenciu,
- command -> state latenciu po state-reporting reworku.

Acceptance:

- ESP32 sa vie pripojit na `8883`,
- RPi backend sa vie pripojit na `8883`,
- bez CA alebo s nespravnym certifikatom sa spojenie odmietne,
- pri rozumnom case certifikat prejde,
- reconnect latencia je akceptovatelna pre muzealny flow.

## Faza 6 - Finalna dokumentacia a deployment checklist

Aktualizovat:

- `docs/04_mqtt_protocol.md`
- `docs/10_museum_backend_setup.md`
- `docs/11_esp32_firmware_setup.md`
- `raspberry_pi/broker/README_SECURITY.md`
- pripadne README cast o instalacii.

Do dokumentacie doplnit:

- ako vytvorit `/etc/mosquitto/passwd`,
- ako nastavit `config.ini`,
- ako nastavit ESP32 credentials,
- ako otestovat anonymous reject,
- ako otestovat dashboard manual MQTT publish,
- ako rollbacknut len docasne,
- co robit pri strate certifikatov alebo zlom case.

## Operacny checklist pre implementaciu s AI

### Faza 0

AI robi:

- necaka sa zmena kodu,
- pripravi presny inventar suborov a navrh nastaveni.

Ty robis:

- zistis, ktore ESP32/Shelly/Waveshare uzly fyzicky existuju,
- oznacis, ktore vies realne preflashovat,
- overis, ci dashboard pouziva Mosquitto WebSocket `9001`,
- potvrdis, ze default secret storage bude `config.local.ini`.

Posli AI:

- zoznam uzlov a ich stav,
- vystup `sudo ss -tlnp | grep ':9001'`,
- info z browser Network tabu, ci vidis `:9001`,
- rozhodnutie `config.local.ini = ano`.

### Faza 1

AI robi:

- upravi Python config a MQTT klienta,
- prida testy pre auth config,
- zabezpeci, ze prazdne credentials nemenia dev spravanie.

Ty robis:

- po poziadani spustis backend na Pi s anonymous brokerom,
- nevkladas realne heslo do trackovaneho `config.ini`,
- ak treba, vytvoris lokalny `config.local.ini`.

Posli AI:

- vystup `pytest -q tests/test_mqtt_security_config.py`, ak bezis testy na Pi,
- vystup `python3 main.py` alebo `journalctl -u museum-system -n 120 --no-pager`,
- log bez hesiel, hlavne riadky okolo MQTT connectu.

### Faza 2

AI robi:

- upravi ESP32 `config.h`, `config.cpp`, `mqtt_manager.cpp`,
- zachova LWT, retained status, subscriptions a topic kontrakt,
- odstrani restart loop pri MQTT auth zlyhani.

Ty robis:

- nahras firmware do jedneho testovacieho ESP32,
- najprv testujes s auth vypnutym,
- potom testujes s auth zapnutym, ale broker stale moze byt anonymous,
- spravis jeden test so zlym heslom a sledujes, ci ESP32 nerebootuje dokola.

Posli AI:

- Serial Monitor log od bootu po MQTT connect,
- log pri zlom hesle s `client.state()` hodnotou,
- potvrdenie, ci LED/status signalizacia dava zmysel,
- zoznam uzlov, ktore uz maju novy firmware.

### Faza 3

AI robi:

- upravi Mosquitto config a install skripty,
- prida blokujuci check na `/etc/mosquitto/passwd`,
- vypne alebo zabezpeci WebSocket listener `9001`.

Ty robis:

- vytvoris `/etc/mosquitto/passwd` priamo na Pi,
- overis, ze vsetky aktivne uzly su ready,
- pripravis SSH alebo lokalny rollback pristup k Raspberry Pi,
- az potom dovolis vypnut `allow_anonymous`.

Posli AI:

- `ls -l /etc/mosquitto/passwd`,
- `sudo systemctl status mosquitto --no-pager`,
- `sudo journalctl -u mosquitto -n 80 --no-pager`,
- potvrdenie, ze mas dostupny rollback pristup,
- zoznam presnych `devices/<CLIENT_ID>/status` topicov, ktore bolo treba
  vycistit ako retained,
- vysledok anonymneho `mosquitto_pub`, ktory ma zlyhat,
- vysledok `mosquitto_pub -u museum_rpi ...`, ktory ma prejst.

### Faza 4

AI robi:

- ACL riesi iba ak je na to samostatny dovod,
- ak sa robi, navrhne room-level ACL, nie zoznam jednotlivych topicov.

Ty robis:

- otestujes nove a stare topicy,
- potvrdis, ze nove ESP32 topic-y nevyzaduju edit ACL.

Posli AI:

- manualne MQTT testy pre `room1/#`, `devices/+/status`, feedback a buduce
  `/state` topic-y,
- pripadne Mosquitto log pri `not authorized` chybe.

### Faza 5

AI robi:

- pripravi MQTTS proof of concept,
- riesi CA, `subjectAltName`, Paho TLS a ESP32 `WiFiClientSecure`.

Ty robis:

- overis cas na RPi,
- rozhodnes, ci bude staticka IP alebo stabilne lokalne DNS meno,
- neposielas private key.

Posli AI:

- vystup `date`,
- host/IP, cez ktory sa klienti realne pripajaju na broker,
- TLS connect log bez private key materialu.

### Faza 6

AI robi:

- upravi dokumentaciu a deployment checklist,
- zhrnie rollback a known limitations.

Ty robis:

- prejdes checklist na realnom Pi,
- potvrdzujes iba vysledky, nie tajomstva.

Posli AI:

- finalny smoke-test log,
- zoznam zariadeni online,
- pripadne co este nie je nasadene.

## Testovaci matrix

### Offline Python testy

Po Python zmenach:

```bash
cd raspberry_pi
source venv/bin/activate
python3 tests/run_quick_tests.py
```

Minimalne nove testy:

- prazdne MQTT credentials nic nenastavia,
- username/password zavolaju Paho `username_pw_set`,
- `password` bez `username` je odmietnuty alebo ignorovany podla zvolenej
  explicitnej policy,
- heslo s `%` v configu nezruti `ConfigManager`,
- heslo sa neloguje,
- auth reject nezanecha beziacu Paho loop thread medzi retry pokusmi,
- TLS config s prazdnou CA je odmietnuty alebo ignorovany podla zvolenej policy,
- `MQTTClient` zostava kompatibilny s doterajsimi konstruktormi.

### Broker smoke test

Pred `allow_anonymous false`:

```bash
mosquitto_pub -h <broker_ip> -t 'room1/light/1' -m 'ON'
```

Po `allow_anonymous false`:

```bash
mosquitto_pub -h <broker_ip> -t 'room1/light/1' -m 'ON'
```

ocakavane zlyhanie.

Potom:

```bash
mosquitto_pub -h <broker_ip> -u museum_rpi -P '<password>' -t 'room1/light/1' -m 'ON'
```

ocakavany uspech.

### Runtime test na Raspberry Pi

```bash
cd raspberry_pi
source venv/bin/activate
python3 main.py
```

Overit v logoch:

- MQTT connected,
- ESP32 status online,
- ziadne plaintext heslo v logu.

### Dashboard test

Overit:

- login do dashboardu,
- `/api/status`,
- `/api/devices`,
- manual MQTT send,
- start scene,
- stop scene.

Poznamka:

Dashboard HTTP Basic Auth a MQTT auth su dve oddelene vrstvy. Dashboard user
nepotrebuje MQTT heslo, pretoze publish robi backend.

### ESP32 test

Pre kazdy firmware:

- boot,
- MQTT connect,
- status online,
- LWT offline pri vypnuti,
- command,
- feedback,
- STOP,
- reconnect.

Pre relay effects:

- `room1/effects/group1 ON`,
- `room1/effects/group1 OFF`,
- feedback `ACTIVE/INACTIVE`.

Pre state-reporting buducnost:

- ESP32 ignoruje `/state` topic-y pri wildcard subscribe.

## Rizika a odporucane poradie

### Najmensie riziko

1. Pridat optional credentials do Pythonu.
2. Pridat optional credentials do ESP32.
3. Otestovat v anonymous broker rezime.
4. Az potom vypnut anonymous broker.

### Najvacsie riziko

Zapnut `allow_anonymous false` skor, ako su vsetky ESP32 uzly preflashovane alebo
nakonfigurovane. Vtedy sa zariadenia nepripoja a miestnost prestane reagovat.

### Co nerobit v prvom kroku

- nemenit topic schemu,
- nezavadzat ACL viazane na konkretne nazvy ESP32,
- nezavadzat MQTTS skor ako username/password,
- nedavat MQTT heslo do browser frontendu,
- nepouzivat `setInsecure()` ako finalnu MQTTS implementaciu,
- nemiesat cleanup alebo SceneGen refactor do tej istej zmeny.

## Kriticka revizia podla aktualneho kodu

Tieto body treba vyriesit alebo vedome akceptovat pred implementaciou. Su to
miesta, kde by inak zabezpecenie mohlo vyrobit regresiu.

### P0 - riesit pred prvym realnym heslom

- Realny `raspberry_pi/config/config.ini` je v repo trackovany. Produkcne MQTT
  heslo preto pojde do ignorovaneho `config.local.ini`, nie do `config.ini`.
- Ak ostane Mosquitto WebSocket listener `9001` anonymous, port `1883` moze byt
  zabezpeceny a broker bude stale obchadzatelny cez WebSocket.
- Relay a motor ESP32 firmwary maju restart po prilis mnohych MQTT pokusoch.
  Pri zlom hesle to moze znamenat restart loop.
- `MQTTClient.connect()` musi pri odmietnuti auth alebo timeoute upratat Paho
  loop thread, inak health-check reconnect moze postupne vrstvit retry stav.

### P1 - testovat v tej istej zmene

- Hesla s `%` alebo specialnymi znakmi mozu narazit na `ConfigParser`
  interpolaciu, ak sa citaju bez `raw=True`.
- Mosquitto restart musi mat preflight na existenciu a citatelnost
  `/etc/mosquitto/passwd`; inak vypnutie anonymous moze broker zhodit.
- MQTTS certifikat musi mat spravny `subjectAltName` pre IP alebo meno, ktore
  klient realne pouziva pri connecte.
- RPi bez presneho casu moze fungovat s username/password, ale MQTTS moze padat
  na platnosti certifikatu.

### P2 - vedome obmedzenia v1

- Spolocne heslo `museum_esp` chrani pred nahodnym klientom, ale nie pred
  uniknutym firmwarom alebo kompromitovanym ESP32.
- ACL per zariadenie su silnejsie, ale nemaju ist do prvej zmeny, aby sa
  nerozbila modularita topicov a jednoduchy onboarding ESP32.
- Retained `online/offline` statusy mozu pocas migracie vyzerat zastarane, ak sa
  stare zariadenie uz nepripoji; treba ich pri rollout-e pozorovat alebo vycistit
  manualne.

## Definition of done pre v1

V1 je hotova, ked:

- broker odmieta anonymous klienta,
- Raspberry Pi backend sa pripaja cez MQTT credentials,
- vsetky aktivne ESP32 uzly sa pripajaju cez MQTT credentials,
- prihlaseny klient nie je obmedzeny na pevny zoznam command topicov v brokeri,
- Web dashboard nadalej ovlada MQTT iba cez Flask API,
- existujuce sceny a topic-y sa nemenia,
- manualny MQTT publish bez credentials zlyha,
- manualny MQTT publish s credentials prejde,
- `room1/scene START`, `room1/STOP`, feedback a device status funguju,
- dokumentacia obsahuje postup nastavenia a rollback.

## Odporucane rozhodnutie

Implementovat najprv MQTT username/password ako modularnu, volitelnu vrstvu.
Nechat topic-y a scene JSON kontrakt bez zmeny. Po uspesnom otestovani na Pi a
ESP32 vypnut `allow_anonymous`. MQTTS riesit az v dalsej faze, spolu s lokalnym
casom alebo RTC, pretoze overovanie certifikatov je citlive na nespravny cas.
