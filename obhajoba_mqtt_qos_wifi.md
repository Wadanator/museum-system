# Priprava na obhajobu: MQTT, QoS, MQTTS a Wi-Fi

Tento text je formulovany podla aktualneho kodu systemu a textu bakalarskej prace.
Aktualna implementacia pouziva MQTT na porte 1883, ESP32 uzly cez Wi-Fi a vlastny
mechanizmus spätnej väzby na urovni aplikacie.

## 1. Otázka oponenta: šifrovanie komunikácie a MQTTS

> **Otázka:** Jakým způsobem byste v navrženém systému řešil šifrování komunikace
> (např. přechod na MQTTS) a jaký vliv by podle vašeho názoru měl tento krok na
> hardware uzlů ESP32 a celkovou latenci systému?

### Krátka odpoveď

V aktuálnom prototype MQTT beží v lokálnej sieti bez šifrovania a broker povoľuje
anonymné pripojenie. Pri reálnom nasadení by som to riešil postupne.

Prvý krok je uzavrieť broker:

```conf
allow_anonymous false
password_file /etc/mosquitto/passwd
```

To znamená, že Raspberry Pi backend aj ESP32 uzly by mali uložené MQTT meno a heslo.
Broker by prijal iba klientov, ktorí sa vedia prihlásiť. Náhodnému človeku by teda
nestačilo poznať IP adresu brokeru ani názov topicu.

Podstatné je, že topic-y nechcem používať ako bezpečnostný mechanizmus. Topic môže byť
ľubovoľný podľa miestnosti a konfigurácie, napríklad `room1/motor1`, alebo úplne iný
názov v inej miestnosti. Bezpečnosť rieši broker: kto nemá platnú identitu, nepripojí
sa a nemôže publikovať príkazy.

Samotné meno a heslo bez MQTTS je dobrý prvý krok proti náhodnému klientovi, ale nie je
ideálne proti odpočúvaniu v sieti. Ak by niekto vedel komunikáciu zachytiť, mohol by sa
pokúsiť získať prihlasovacie údaje. Preto by druhý krok bol prechod na MQTTS.

MQTTS znamená MQTT cez šifrované TLS spojenie, podobne ako HTTPS je šifrovaná verzia HTTP.
Broker by typicky používal port `8883`, ESP32 by namiesto `WiFiClient` použilo
`WiFiClientSecure` a prihlasovacie údaje aj obsah správ by boli prenášané šifrovane.
Silnejšia verzia by bola MQTTS s klientskymi certifikátmi alebo aspoň jedinečné silné
heslo pre každý uzol. Potom identita zariadenia nie je založená na názve topicu ani na
`CLIENT_ID`, ale na tajnom údaji/certifikáte, ktorý náhodný človek nemá.

Broker by zároveň nemal byť vystavený verejne na internet. Mal by byť dostupný iba v
lokálnej alebo oddelenej sieti múzea, prípadne chránený firewallom. Tým sa znižuje
šanca, že sa k nemu dostane niekto zvonku.

### Ako by to fungovalo v praxi

**Aktuálne v mojom kóde:**

1. Klient sa pripojí na IP adresu a port brokeru, napríklad `192.168.x.x:1883`.
2. Mosquitto broker povoľuje anonymné pripojenie (`allow_anonymous true`).
3. Klient sa dostane do MQTT siete bez mena a hesla.
4. Ak pozná alebo uhádne topic, môže publikovať správu, napríklad `room1/motor1`.
5. ESP32, ktoré tento topic odoberá, správu prijme a vykoná podľa firmvéru.

Problém teda nie je v tom, že topic má zlý názov. Problém je v tom, že broker dnes
pustí aj neznámeho klienta.

**Po prvom kroku - broker s prihlasovaním:**

1. Klient sa pokúsi pripojiť na IP adresu a port brokeru.
2. Raspberry Pi backend alebo ESP32 pošle v MQTT `CONNECT` správe svoje meno a heslo.
3. Broker ich porovná so zoznamom povolených používateľov.
4. Ak sú nesprávne, klienta nepripojí a nemôže publikovať žiadny príkaz.
5. Ak sú správne, klient sa pripojí a systém funguje rovnako ako dnes.

Rozdiel oproti aktuálnemu stavu je teda v tom, že náhodný človek sa nedostane ani do
fázy, v ktorej by mohol posielať MQTT správy. Topic-y môžu zostať ľubovoľné.
Slabina tejto verzie je, že bez MQTTS ide meno a heslo stále cez obyčajné TCP spojenie,
takže pri odpočúvaní siete by ich bolo možné zachytiť.

Na ESP32 by sa princípovo zmenilo pripojenie z:

```cpp
mqttClient.connect(CLIENT_ID);
```

na:

```cpp
mqttClient.connect(CLIENT_ID, MQTT_USER, MQTT_PASSWORD);
```

Na Raspberry Pi by backend pred pripojením nastavil prihlasovacie údaje MQTT klienta.

**Po druhom kroku - MQTTS:**

1. Klient sa nepripája obyčajným MQTT na port `1883`, ale cez MQTTS, typicky na port `8883`.
2. Najprv vznikne šifrované TLS spojenie medzi klientom a brokerom.
3. ESP32 alebo Raspberry Pi si overí, že komunikuje so správnym brokerom.
4. Až potom sa vo vnútri šifrovaného spojenia odošle MQTT meno a heslo.
5. Vo vnútri toho istého šifrovaného spojenia idú aj topic-y, príkazy a feedback.

Na vytvorenie TLS spojenia ešte netreba MQTT heslo. Je to iba sieťové spojenie s
brokerom, v ktorom si ESP32 a broker dohodnú šifrovanie. Až po vytvorení tohto
šifrovaného kanála prebehne MQTT prihlásenie. Náhodný klient teda môže skúsiť otvoriť
TLS spojenie, ale ak následne nepošle správne MQTT meno a heslo, broker ho neprijme a
neumožní mu publikovať príkazy.

Pri odpočúvaní siete by útočník videl, že zariadenie komunikuje s brokerom, ale nevidel
by jednoducho MQTT heslo, názvy topicov ani obsah príkazov. To je hlavný rozdiel medzi
obyčajným MQTT s heslom a MQTTS.

### Ako vyzerá správa pri MQTT a MQTTS

Pri obyčajnom MQTT ide komunikácia cez nešifrované TCP spojenie. MQTT paket je teda v
prenose čitateľný. Zjednodušene by bolo vidieť napríklad:

```text
MQTT CONNECT
client_id = esp32_motor
username  = esp32_motor
password  = tajne_heslo

MQTT PUBLISH
topic   = room1/motor1
payload = OPEN
```

To neznamená, že každý človek si to automaticky prečíta bez nástrojov, ale ak má možnosť
odpočúvať sieťovú komunikáciu, MQTT bez TLS mu tieto údaje nechráni. Preto samotné meno
a heslo rieši prístup k brokeru, ale ešte nerieši bezpečné prenesenie hesla po sieti.

Pri MQTTS najprv prebehne TLS handshake. Počas neho si ESP32 a broker dohodnú šifrované
spojenie a ESP32 si overí certifikát brokeru. Až potom idú MQTT pakety vnútri tohto
šifrovaného spojenia:

```text
TLS encrypted data
  -> vo vnútri je MQTT CONNECT s menom a heslom
  -> vo vnútri je MQTT PUBLISH s topicom room1/motor1 a payloadom OPEN
```

Človek, ktorý by komunikáciu odpočúval, by videl hlavne to, že ESP32 komunikuje s IP
adresou brokeru na porte `8883`. Nevidel by jednoducho MQTT heslo, názvy topicov ani
obsah príkazov. Šifrovanie a dešifrovanie sa nerobí ručne v mojom kóde pri každej správe.
Po správnom nastavení ho automaticky rieši `WiFiClientSecure` na ESP32 a TLS vrstva
Mosquitto brokeru.

Čo by som musel definovať:

- na brokeri certifikát a privátny kľúč pre TLS,
- na ESP32 certifikát alebo CA certifikát, ktorým si overí certifikát brokeru,
- MQTT meno a heslo pre zariadenie,
- port `8883` namiesto nešifrovaného portu `1883`.

Dôležité je, že ESP32 musí certifikát brokeru reálne overovať. Použitie
`wifiClient.setInsecure()` by bolo vhodné nanajvýš na testovanie, ale nie ako finálne
bezpečné riešenie, pretože by sa tým stratilo overenie, či sa zariadenie pripája na
správny broker.

Na ESP32 sú teda dve samostatné zmeny. Pri prvom kroku by sa doplnilo iba meno a heslo,
ale spojenie by bolo stále obyčajné MQTT:

```cpp
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

mqttClient.connect(CLIENT_ID, MQTT_USER, MQTT_PASSWORD);
```

Pri druhom kroku, teda pri MQTTS, by sa zmenil aj typ sieťového klienta. `WiFiClient`
znamená obyčajné nešifrované TCP spojenie. `WiFiClientSecure` znamená TCP spojenie
zabezpečené cez TLS:

```cpp
WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

wifiClient.setCACert(ROOT_CA_CERT);
mqttClient.connect(CLIENT_ID, MQTT_USER, MQTT_PASSWORD);
```

Oproti aktuálnemu obyčajnému variantu:

```cpp
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

mqttClient.connect(CLIENT_ID);
```

### Vplyv na ESP32 a latenciu

ESP32 prechod na MQTTS zvládne, ale má to cenu: väčší firmvér, vyššia spotreba RAM a
pomalšie pripájanie kvôli TLS handshake. Tento handshake sa však robí hlavne pri
pripojení alebo reconnecte, nie pri každom príkaze. Pri bežnom behu by MQTT spojenie
zostalo otvorené, takže latencia krátkych riadiacich správ by sa nemala dramaticky
zvýšiť.

V práci som pri obyčajnom MQTT nameral priemernú latenciu 111,7 ms a maximum 219 ms.
Po prechode na MQTTS by som meranie zopakoval, ale pri efektoch trvajúcich sekundy
neočakávam zásadné zhoršenie používateľského zážitku.

### Stručná finálna veta

> Bezpečnosť by som nestaval na názvoch topicov, pretože tie môžu zostať ľubovoľné a
> modulárne podľa miestnosti. Najprv by som vypol anonymný prístup k brokeru a každé
> RPi/ESP32 by sa muselo prihlásiť menom a heslom. Následne by som prešiel na MQTTS,
> aby sa prihlasovacie údaje a komunikácia nedali jednoducho odpočúvať. Dopad na ESP32
> by bol hlavne pri pripájaní, nie pri každom jednotlivom príkaze.

## 2. Otázka oponenta: QoS 0 a feedback tracker

> **Otázka:** V práci uvádíte, že pro odesílání řídicích příkazů používáte MQTT
> s úrovní kvality služby QoS 0 a pro jejich potvrzení jste implementoval vlastní
> mechanismus sledování zpětné vazby („feedback tracker“) v backendu. Proč jste se
> rozhodl pro tento přístup namísto využití nativní podpory QoS 1 nebo QoS 2, které
> řeší garanci doručení a potvrzování přímo na úrovni samotného protokolu MQTT?

### Krátke zhodnotenie

Nemyslím si, že použitie QoS 0 bolo v tomto prototype chyba. Je to obhájiteľný kompromis,
ale treba ho vysvetliť presne: QoS 0 samo o sebe negarantuje doručenie, preto je doplnené
aplikačnou spätnou väzbou. Zároveň však feedback tracker nie je to isté ako QoS 1 alebo
QoS 2. Rieši inú úroveň problému.

MQTT QoS rieši doručenie správy na úrovni protokolu. Feedback tracker rieši, či ESP32
príkaz reálne prijalo, rozpoznalo, vykonalo a odpovedalo výsledkom. Pri ovládaní fyzických
výstupov je pre mňa dôležitejšia práve tá druhá informácia.

### Čo by mi dalo QoS 1 alebo QoS 2

QoS 1 by znamenalo, že MQTT správa sa má doručiť aspoň raz. Broker a klient si vymenia
potvrdenie na úrovni protokolu. Nevýhoda je, že pri opakovaní môže prísť duplikát správy.
Pri príkazoch typu `ON`/`OFF` to väčšinou nevadí, lebo sú stavové a idempotentné. Pri
časovaných scénach však môže byť problém, ak sa starší príkaz zopakuje alebo príde neskôr,
keď už scéna pokračuje ďalej.

QoS 2 by riešilo doručenie presne raz na úrovni MQTT protokolu, ale za cenu väčšej réžie,
viacerých potvrdzovacích krokov a vyššej latencie. Pri riadení efektov synchronizovaných
so scénou by som ho nepovažoval za vhodnú predvolenú voľbu.

Dôležité je, že ani QoS 1 ani QoS 2 mi nepovedia, či ESP32 príkaz správne spracovalo,
či payload nebol neplatný, či sa podarilo prepnúť relé alebo nastaviť motor. Povedia iba
to, že MQTT správa bola doručená podľa pravidiel protokolu.

### Prečo dáva zmysel môj feedback tracker

V mojom systéme ESP32 po prijatí príkazu vykoná svoju logiku a následne publikuje odpoveď
na topic `<command_topic>/feedback`. Odpoveď môže byť napríklad `OK`, `ERROR`, `ACTIVE`
alebo `INACTIVE`. Backend túto odpoveď zachytí a spáruje ju s pôvodným príkazom.

Tým získavam informácie, ktoré by samotné QoS neposkytlo:

- či uzol naozaj odpovedal,
- ako dlho trval celý cyklus príkaz - vykonanie - feedback,
- či ESP32 hlási úspech alebo chybu,
- aký je rozdiel medzi požadovaným stavom (`desired`) a potvrdeným stavom (`confirmed`),
- aktuálne stavy pre webový dashboard a logovanie.

Práve preto by čisté QoS nevedelo nahradiť celú aktuálnu funkcionalitu. Dashboard by síce
mohol vedieť, že MQTT správa bola odoslaná, ale nevedel by, či ju zariadenie skutočne
vykonalo.

Konkrétny príklad: ak backend pošle na svetlo správu `BLINK`, ale firmvér ESP32 pozná
iba príkazy `ON` a `OFF`, vyššie QoS by potvrdilo iba doručenie MQTT správy. Feedback
tracker však zachytí odpoveď `ERROR` z ESP32 a backend vie, že príkaz nebol úspešne
vykonaný. Táto informácia sa cez samotné QoS získať nedá.

### Vplyv na synchronizáciu so scénou

Pri scénach synchronizovaných so zvukom je dôležité, aby sa príkazy neposielali zbytočne
neskoro a aby systém nečakal na potvrdenie pred pokračovaním scény. V mojom riešení sa
feedback sleduje paralelne. Scéna teda po odoslaní MQTT príkazu neblokuje celé prehrávanie
a nečaká, kým sa vráti potvrdenie.

Zároveň by som netvrdil, že aktuálny systém garantuje presnosť na úrovni 20 ms. V práci
bola meraná latencia celého cyklu od odoslania príkazu po návrat feedbacku. Priemer bol
111,7 ms, maximum 219 ms a doručiteľnosť feedbacku v teste bola 100 %. Toto meranie
zahŕňa aj cestu späť, spracovanie na ESP32 a párovanie v backende, takže nejde o čistú
jednosmernú latenciu fyzického výstupu. Pre efekty trvajúce sekundy je to však použiteľné.

Ak by som potreboval veľmi presnú synchronizáciu na úrovni jednotiek až desiatok
milisekúnd, nespoliehal by som sa iba na jednotlivé MQTT príkazy v reálnom čase. Lepšie
riešenie by bolo poslať ESP32 jeden spúšťací príkaz vopred a časovo citlivú sekvenciu
vykonať lokálne priamo na ESP32, prípadne použiť káblové riešenie alebo samostatný
synchronizačný signál.

### Čo by som zlepšil do budúcna

Najrozumnejšie rozšírenie by podľa mňa nebolo nahradiť feedback tracker samotným QoS,
ale použiť hybridný model:

- bežné scénické príkazy ponechať na QoS 0 kvôli nízkej réžii a nízkej latencii,
- feedback tracker ponechať vždy, lebo potvrdzuje aplikačné vykonanie príkazu,
- pre vybrané kritické príkazy zvážiť QoS 1,
- pri opakovaných rýchlych príkazoch na rovnaký topic doplniť identifikátor príkazu,
  aby sa feedback nepároval iba podľa topicu,
- pre veľmi presné časovanie presunúť sekvenciu bližšie k hardvéru, teda na ESP32.

QoS 2 by som pre tento systém nepoužil ako predvolenú voľbu, pretože jeho výhoda by bola
menšia než cena v podobe vyššej réžie a potenciálneho oneskorenia.

### Stručná finálna veta

> QoS 0 som zvolil ako kompromis pre nízku réžiu a nízku latenciu pri časovaných scénach.
> Samotné QoS 1 alebo QoS 2 by mi síce riešilo protokolové doručenie MQTT správy, ale
> nepotvrdilo by fyzické vykonanie príkazu na ESP32. Preto som doplnil aplikačný feedback
> tracker, ktorý sleduje odpoveď zariadenia, meria latenciu, rozlišuje požadovaný a
> potvrdený stav a poskytuje údaje pre dashboard. Do budúcna by som zvážil hybridný model:
> QoS 0 pre bežné časovo citlivé príkazy, QoS 1 pre vybrané kritické príkazy, ale
> aplikačnú spätnú väzbu by som ponechal v každom prípade.

## 3. Otázka oponenta: Wi-Fi a alternatívne bezdrôtové štandardy

> **Otázka:** Jako jedno z hlavních omezení uvádíte použití Wi-Fi komunikace.
> Nebylo by řešením přejít na jiné bezdrátové standardy, které platforma ESP nabízí?
> Dokázal byste tyto standardy zhodnotit a porovnat?

### Krátka odpoveď

Áno, existujú aj iné možnosti, ale v mojom systéme Wi-Fi nie je použitá iba preto, že je
bezdrôtová. Hlavný dôvod je, že Wi-Fi poskytuje priamo IP sieť, a tým pádom aj jednoduché
použitie MQTT, webového dashboardu, OTA aktualizácií a komunikácie s Raspberry Pi.

Dôležité je, že MQTT nie je viazané iba na Wi-Fi. MQTT beží nad IP sieťou, takže rovnaký
návrh môže fungovať cez Wi-Fi aj cez Ethernet/LAN. Preto by som do budúcna nebral
architektúru ako "Wi-Fi systém", ale skôr ako "MQTT/IP systém", kde transport môže byť
podľa situácie Wi-Fi, LAN alebo PoE.

Pre pevne osadené a kritické uzly by bolo najlepšie riešenie káblové pripojenie, ideálne
LAN alebo PoE. Wi-Fi by som ponechal tam, kde je ťahanie kábla nepraktické, napríklad pri
rozmiestnených zariadeniach vo väčšej miestnosti, hale alebo pri prvkoch, ktoré sa môžu
meniť podľa expozície.

### Prečo Wi-Fi dáva zmysel v mojom návrhu

V múzejnej inštalácii môžu byť zariadenia rozmiestnené vo veľkej miestnosti, v dlhšej
hale alebo vo viacerých miestnostiach. V takom prípade je praktické mať IP sieť s viacerými
access pointmi a zariadenia pripájať do rovnakej MQTT infraštruktúry.

Z pohľadu systému mi Wi-Fi prináša:

- priame pripojenie ESP32 na MQTT broker na Raspberry Pi,
- jednoduché smerovanie správ cez topic-y,
- možnosť webového dashboardu v každej miestnosti,
- možnosť OTA aktualizácií firmvéru,
- jednoduchú integráciu s existujúcou sieťovou infraštruktúrou,
- možnosť neskôr spraviť nadradený/global dashboard.

Práve webový dashboard je silný argument pre IP sieť. Ak by malo múzeum viac miestností,
každá miestnosť môže mať vlastné Raspberry Pi, vlastný broker a vlastný web server.
Nad tým môže existovať jednoduchá nadstavba, ktorá zobrazí stav všetkých miestností.
Pri kliknutí na konkrétnu miestnosť môže používateľa presmerovať na IP adresu alebo web
danej miestnosti. Toto je s Wi-Fi/LAN prirodzené, ale pri ESP-NOW alebo BLE by bolo nutné
vytvoriť ďalšie gateway-e a vlastnú integračnú vrstvu.

### Porovnanie možností

| Technológia | Výhody | Nevýhody | Hodnotenie pre môj systém |
|---|---|---|---|
| Wi-Fi | Priama IP komunikácia, MQTT, dashboard, OTA, jednoduché prepojenie s RPi | Rušenie, závislosť od AP, vyššia spotreba | Dobrá voľba pre prototyp a pre miestnosti s kvalitnou sieťou |
| LAN/Ethernet/PoE | Najvyššia spoľahlivosť, stabilná latencia, napájanie aj dáta jedným káblom pri PoE | Nutnosť kabeláže, menej flexibilné rozmiestnenie | Najlepšie pre finálne pevné a kritické uzly |
| ESP-NOW | Rýchle krátke správy, nízka réžia, nepotrebuje AP | Nie je to IP/MQTT, treba gateway, obmedzený payload, párovanie peerov, závislosť od Wi-Fi kanála | Vhodné ako lokálny doplnok, nie ako náhrada celej MQTT siete |
| BLE | Nízka spotreba, dobré pre malé periférie | Nižšia priepustnosť, menší praktický dosah, zložitejšie riadenie viacerých aktuátorov | Skôr pre senzory alebo servisné funkcie, nie pre hlavné riadenie scén |
| BLE Mesh | Mesh topológia a nízka spotreba | Vyššia komplexita, latencia a horšia integrácia s MQTT/dashboardom | Nevhodné ako jednoduchá náhrada súčasnej architektúry |
| Zigbee / Thread | Robustná low-power mesh sieť | Vyžaduje vhodný ESP variant alebo rádio a gateway do MQTT/IP | Zaujímavé pre senzory/svetlá, ale nie priamo pre tento prototyp |
| Wi-Fi Mesh / ESP-MESH | Vie rozšíriť dosah bez viacerých káblových AP | Zložitejšie smerovanie, stále používa Wi-Fi, môže zvýšiť latenciu | Použil by som iba tam, kde nejde spraviť kvalitné AP pokrytie |
| LoRa / LoRaWAN | Veľký dosah | Nízka priepustnosť, vyššia latencia, externé rádio | Nevhodné pre rýchle riadenie scén v interiéri |

### ESP-NOW ako doplnok, nie hlavný prenos

ESP-NOW by mohol byť zaujímavý v hybridnom scenári. Napríklad v miestnosti môže byť jeden
pevný ESP32 alebo Waveshare modul pripojený cez Ethernet/LAN, ktorý komunikuje s Raspberry Pi
cez MQTT. V jeho blízkosti môžu byť ďalšie jednoduché ESP32 uzly, ktoré s ním komunikujú cez
ESP-NOW. Tento hlavný uzol by potom fungoval ako gateway medzi ESP-NOW a MQTT.

Takýto model by dával zmysel napríklad vtedy, ak by Ethernetový relay modul ovládal relé,
ale v jeho blízkosti by bolo klasické ESP32 určené na PWM riadenie motorov alebo LED efektov.
ESP-NOW by vtedy slúžilo iba ako krátka lokálna bezdrôtová linka. Hlavná architektúra by
stále zostala MQTT/IP, takže web dashboard a Raspberry Pi backend by sa nemuseli zásadne
meniť.

Nepoužil by som však ESP-NOW ako hlavnú sieť pre celé múzeum. Dôvod je, že by som stratil
priamu IP konektivitu, jednoduchý dashboard, bežné MQTT routovanie a jednoduchú správu
viacerých miestností.

### Čo by som zlepšil pri Wi-Fi variante

Ak by som zostal pri Wi-Fi, nespoliehal by som sa na náhodnú bežnú sieť. Pre reálne nasadenie
by som navrhol:

- oddelenú sieť pre technológiu expozície, nie sieť pre návštevníkov,
- samostatné SSID alebo VLAN,
- kvalitné AP s dobrým pokrytím miestnosti alebo haly,
- plánovanie kanálov a meranie RSSI,
- monitoring výpadkov, reconnectov a MQTT timeoutov,
- pri kritických uzloch prechod na LAN/PoE,
- ponechanie rovnakej MQTT topic architektúry bez ohľadu na to, či uzol ide cez Wi-Fi alebo LAN.

### Stručná finálna veta

> Iné bezdrôtové štandardy by bolo možné použiť, ale nepovažujem ich za priamu náhradu
> súčasného návrhu. Wi-Fi som zvolil najmä preto, že poskytuje IP sieť, a tým jednoduché
> použitie MQTT, webového dashboardu, OTA aktualizácií a viacmiestnostného dohľadu. Do
> budúcna by som kritické pevné uzly riešil skôr cez LAN alebo PoE, pričom Wi-Fi by zostala
> pre flexibilne rozmiestnené uzly. ESP-NOW by som vedel použiť ako lokálny doplnok alebo
> bridge pri blízkych ESP32 zariadeniach, ale nie ako hlavný komunikačný štandard celého
> systému.

## 4. Kratka odpoved na obhajobu

Ak by som to mal povedat strucne:

Aktualne som zvolil MQTT s QoS 0, pretoze system bezi v lokalnej oddelenej sieti a
potrebujem minimalnu reziu. Spolahlivost som neriesil iba na urovni protokolu, ale
aplikacnou spätnou väzbou. QoS 1 alebo QoS 2 by potvrdili dorucenie spravy, ale nie
to, ze ESP32 realne vykonalo prikaz. Feedback tracker preto potvrdzuje az vysledok
na strane zariadenia a zaroven poskytuje diagnostiku.

Prechod na MQTTS je technicky mozny. Vyziadal by si TLS konfiguraciu brokeru a pouzitie
`WiFiClientSecure` na ESP32. Dopad na latenciu by bol najvyraznejsi pri nadviazani
spojenia, nie pri kazdej sprave, ak by spojenie zostalo trvalo otvorene. Hardverovo je
to pre ESP32 zvladnutelne, ale treba ratat s vyssou spotrebou RAM a CPU.

Samotne sifrovanie by som ale nebral ako jedinu ochranu. Ak by bol broker dostupny
bez autentifikacie, znalost jeho IP adresy by stacila na spamovanie topicov alebo
odosielanie falosnych prikazov. Preto by som v produkcii vypol anonymny pristup,
pridal prihlasovanie alebo klientske certifikaty, ACL pravidla pre jednotlive uzly
a firewall alebo oddelenu VLAN. MQTTS by bolo az jedna z vrstiev tejto ochrany.

Wi-Fi som zvolil preto, ze poskytuje IP konektivitu a tym jednoducho zapada do MQTT,
Raspberry Pi backendu aj weboveho rozhrania. Samotny navrh vsak nie je viazany iba na
Wi-Fi; rovnaka MQTT/IP architektura moze bezat aj cez LAN alebo PoE. Alternativy ako
ESP-NOW, BLE alebo Zigbee maju svoje vyhody, ale vyzadovali by brany alebo zmenu
architektury. Pre tuto pracu je preto najlepsie Wi-Fi prevadzkovat na vyhradenej sieti
a pri kritickych buducich instalaciach uvazovat skor o LAN/PoE, pripadne o RS-485 tam,
kde dava zmysel priemyselna zbernica.
