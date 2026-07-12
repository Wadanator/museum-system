# 07 Window left/right motor support

Tento subor ostava na povodnej ceste len kvoli navaznosti TODO cisla. Obsahovo je
uz autoritativny plan pre `window` / OKNO: jedna fyzicka okenna zostava s lavou
a pravou stranou, teda dva DC motory ovladane cez PWM modul a dva H-mostiky.

## Status rule - DONE

Kazda konkretna cast v tomto TODO ma mat status:

- `DONE` = implementovane alebo rozhodnute v aktualnom scope.
- `NIE JE DONE` = chyba implementacia, HW validacia, meranie alebo finalne rozhodnutie.
- Ak je nieco hotove iba softverovo, piseme `DONE (SW)` a hned vedla co je `NIE JE DONE (HW)`.

## 1. Aktualny ciel testu - DONE (SW), NIE JE DONE (HW)

Ciel teraz nie je finalna mechanika. Ciel je overit, ze po kliknuti vo Web UI alebo
po MQTT prikaze vznikne PWM signal na vystupe Modbus PWM modulu.

- DONE (SW): backend vie poslat prikazy na `room1/window/left` a `room1/window/right`.
- DONE (SW): firmware pouziva `Room1_Window_Ctrl` a window topicy.
- DONE (SW): aktualny test profil ma `endstopsEnabled = false`, aby sa dalo merat bez dorazov.
- DONE (SW): RS485 DE/RE pin je nastaveny na `GPIO21`, co bolo potvrdene na realnom module.
- DONE (SW): MQTT ACK timeout ostava povodny `700 ms`; problem nebol timeout, ale DE pin.
- NIE JE DONE (HW): Arduino IDE build po poslednych opravach musi potvrdit pouzivatel.
- NIE JE DONE (HW): meranie PWM vystupu na PWM module voltmetrom/osciloskopom.
- NIE JE DONE (HW): test cez H-mostiky a realne motory bez mechaniky okna.

## 2. Naming and topics - DONE

Finalny typ v systeme je `window`, nie iny historicky nazov.

Canonical MQTT topicy:

```text
room1/window/left
room1/window/right
room1/window/STOP
room1/STOP
```

Feedback topicy:

```text
room1/window/left/feedback
room1/window/right/feedback
```

State topicy:

```text
room1/window/left/state
room1/window/right/state
```

Device status topic:

```text
devices/Room1_Window_Ctrl/status
```

Aktualne prikazy:

```text
OPEN
OPEN:<speed>
CLOSE
CLOSE:<speed>
STOP
OFF
SPEED:<speed>
```

Speed je percento `0..100`. Pre prakticky test pouzivame hlavne `OPEN:30`,
`CLOSE:30`, `STOP`, pripadne kratko `OPEN:100` iba pri odpojenej mechanike a
kontrole PWM rozsahu.

## 3. Hardware mapping - DONE (plan), NIE JE DONE (full HW validation)

Riadiaci modul:

- DONE: Waveshare ESP32-S3 PoE/ETH modul s LAN/WiFi fallbackom.
- DONE: onboard RS485 `TX=GPIO17`, `RX=GPIO18`, `DE/RE=GPIO21`.
- DONE: externy 4-kanalovy Modbus RTU PWM modul.
- DONE: dva H-mostiky, jeden pre lavu stranu okna, jeden pre pravu stranu okna.
- NIE JE DONE: finalne zatazove meranie prudov motorov a dimenzovanie poistiek/napajania.

PWM kanalove mapovanie:

| Strana okna | Stav | PWM kanal | Duty register | Status |
| --- | --- | --- | --- | --- |
| Lava | OPEN | CH1 | `0x0002` | DONE (SW) |
| Lava | CLOSE | CH2 | `0x0005` | DONE (SW) |
| Prava | OPEN | CH3 | `0x0008` | DONE (SW) |
| Prava | CLOSE | CH4 | `0x000B` | DONE (SW) |

PWM duty scale:

- DONE (SW): firmware pouziva `PWM_DUTY_MAX = 10000`, pretoze modul pouziva duty v krokoch 0.01 percenta.
- NIE JE DONE (HW): potvrdit na realnom module meranim, ze `30 %` prikaz dava ocakavany duty signal.

Dorazy / digital inputs:

| Strana okna | Doraz OPEN | Doraz CLOSE | Predpoklad | Status |
| --- | --- | --- | --- | --- |
| Lava | DI1 / GPIO4 | DI2 / GPIO5 | NC active-low | NIE JE DONE |
| Prava | DI3 / GPIO6 | DI4 / GPIO7 | NC active-low | NIE JE DONE |

Aktualne su dorazy zamerne vypnute:

```cpp
endstopsEnabled = false
```

## 4. Firmware status - DONE (SW), NIE JE DONE (production validation)

Hotove softverovo:

- DONE: firmware priecinok je `esp32/devices/lan/ArduinoIDE/esp32_mqtt_window_controller`.
- DONE: hlavny sketch je `esp32_mqtt_window_controller.ino`.
- DONE: `CLIENT_ID = Room1_Window_Ctrl`.
- DONE: prikazy pre lavu/pravu stranu su oddelene.
- DONE: podporovane su rychlosti cez `OPEN:<speed>`, `CLOSE:<speed>`, `SPEED:<speed>`.
- DONE: pred zapnutim jedneho smeru sa vypina opacny PWM kanal.
- DONE: pri zmene smeru je neblokujuci dead-time `DIRECTION_CHANGE_DEADTIME_MS = 350`; PWM aktivacia sa dokonci v `handleWindows()`.
- DONE: po MQTT disconnecte sa aktivny pohyb zastavi po `NETWORK_FAILOVER_GRACE = 5000`.
- DONE: pri dlhej necinnosti prikazov sa aktivny pohyb zastavi cez `NO_COMMAND_TIMEOUT = 180000`.
- DONE: OTA safe stop zastavi PWM pred update cyklom.
- DONE: WDT je odvodeny od aktivneho max pohybu: `WDT_TIMEOUT_MS = maxMoveMs * 1.5`, teraz 15000 ms.
- DONE: state payload je JSON, napriklad:

```json
{"state":"OPENING","direction":"OPENING","speed":30,"node_id":"Room1_Window_Ctrl","source":"command","ts_ms":12345}
```

Chyba pred produkciou:

- NIE JE DONE: lokalny Arduino IDE build po poslednych opravach musi byt potvrdeny.
- NIE JE DONE: realny test PWM modulu cez RS485 s `DE/RE=GPIO21`.
- NIE JE DONE: test smerov na H-mostikoch a motoroch.
- NIE JE DONE: validacia dorazov po zapojeni.
- NIE JE DONE: dlhodoby burn-in test s opakovanym OPEN/CLOSE/STOP.

## 5. Backend and Web UI status - DONE (base support), NIE JE DONE (production validation)

Backend:

- DONE: `devices.json` ma skupinu `windows` s `window_left` a `window_right`.
- DONE: `/api/devices` akceptuje a vracia `windows`.
- DONE: MQTT actuator state store pozna window stavy `OPENING`, `CLOSING`, `STOPPED`, `OPEN`, `CLOSED`, `UNKNOWN`.
- DONE: globalny force-all-off mapuje window na `STOPPED`.
- DONE: ACK tracker pouziva standardny pattern `<topic>/feedback` a ostava na 700 ms timeout.
- NIE JE DONE: realny RPI runtime test s pripojenym ESP a brokerom po poslednych firmware opravach.

Web UI:

- DONE: Commands view zobrazuje window zariadenia.
- DONE: window karta vie posielat `OPEN:<speed>`, `CLOSE:<speed>` a `STOP`.
- DONE: Scene editor ma window zariadenia v palete.
- DONE: Live/runtime vie zobrazit window pohybove stavy.
- NIE JE DONE: finalny UX test na RPI s realnym ESP feedbackom.

## 6. Config profiles - DONE (SW), NIE JE DONE (HW production profile validation)

Chceme dva jasne profily:

### TEST_NO_ENDSTOPS_SAFE - DONE (current behavior)

Pouzitie: laboratorny test PWM vystupu, H-mostikov a smerov bez dorazov.

- DONE: `endstopsEnabled = false` pre lavu a pravu stranu.
- DONE: default speed je `30`.
- DONE: `maxMoveMs = 10000`, teda max 10 sekund pohybu pre kazdy prikaz/smer aj bez dorazov.
- DONE: stale plati `room1/STOP`, `room1/window/STOP`, MQTT disconnect stop a no-command timeout.

### PROD_WITH_ENDSTOPS - DONE (SW switch exists), NIE JE DONE (HW validation)

Pouzitie: finalna mechanika s dorazmi.

- DONE (SW): pridany compile-time prepinac `WINDOW_PROFILE_TEST_NO_ENDSTOPS_SAFE` / `WINDOW_PROFILE_PROD_WITH_ENDSTOPS`; aktivny je zatial bez dorazov.
- NIE JE DONE: nastavit `endstopsEnabled = true` pre lavu a pravu stranu.
- NIE JE DONE: potvrdit NC/NO logiku dorazov na realnom zapojeni.
- NIE JE DONE: urcit produkcne `maxMoveMs` z meraneho casu realneho pohybu + rezerva.
- NIE JE DONE: ak budu OPEN a CLOSE casy rozdielne, rozdelit jeden `maxMoveMs` na `maxOpenMs` a `maxCloseMs`.

## 7. Safety model for production - DONE (plan), NIE JE DONE (full implementation/HW)

Bezpecnost nesmie stat iba na jednom mechanizme. Nespoliehat sa iba na broker,
ani iba na dorazy. Produkcna verzia ma mat vrstvy, ktore funguju aj pri ciastocnej
poruche.

| Vrstva | Co robi | Status |
| --- | --- | --- |
| Startup safe-off | po boote vypnut vsetky PWM kanaly | DONE (SW) |
| Direction interlock | pred OPEN vypnut CLOSE a naopak | DONE (SW) |
| Dead-time | kratka pauza pri zmene smeru bez blokovania hlavneho loopu | DONE (SW) |
| Local max runtime | zastavit pohyb po `maxMoveMs` aj ked nepride doraz | DONE (SW): 10000 ms teraz, WDT 15000 ms; NIE JE DONE: finalna hodnota po merani |
| MQTT disconnect stop | pri strate broker spojenia zastavit aktivny pohyb | DONE (SW) |
| No-command timeout | pri dlhom tichu prikazov zastavit aktivny pohyb | DONE (SW) |
| Global STOP | `room1/STOP` a `room1/window/STOP` | DONE (SW) |
| Endstops | fyzicke dorazy OPEN/CLOSE | NIE JE DONE |
| Hardware kill | rele/stykac na odpojenie napajania H-mostikov | NIE JE DONE |
| Fusing/current limit | poistky alebo driver current limit podla motorov | NIE JE DONE |
| Burn-in test | opakovane cykly a sledovanie teploty/prudu | NIE JE DONE |

Max runtime pravidlo:

- DONE (SW): kazdy aktivny pohyb ma casovy limit; opakovany prikaz rovnakym smerom neresetuje `moveStartedAt`.
- NIE JE DONE: finalny limit musi byt odmerany na realnom okne. Odporucanie: realny cas jazdy v danom smere + 30 az 50 percent rezerva, nikdy nie nekonecno.
- NIE JE DONE: pri produkcii zvazit samostatne limity pre lavu/pravu stranu aj pre OPEN/CLOSE smer.

## 8. Heartbeat decision - DONE (current decision), NIE JE DONE (optional stronger layer)

Samostatny RPI heartbeat teraz nie je povinny.

Dovod:

- ESP uz vie zistit stratu MQTT spojenia s brokerom.
- Firmware ma MQTT keepalive a reconnect logiku.
- Pri strate MQTT spojenia aktivny pohyb zastavi cez `NETWORK_FAILOVER_GRACE`.
- Pri dlhom case bez prikazov aktivny pohyb zastavi cez `NO_COMMAND_TIMEOUT`.
- Kriticka ochrana musi byt lokalna v ESP: `maxMoveMs`, dorazy a pripadne hardware kill, nie len signal z RPI.

Co z toho plynie:

- DONE: pre aktualny test nechceme pridavat povinny `room1/system/heartbeat`.
- DONE: nespoliehat sa iba na to, ze broker je online/offline.
- DONE: nespoliehat sa iba na dorazy, lebo mozu byt zle zapojene alebo mechanicky zlyhat.
- NIE JE DONE: ak sa neskor ukaze potreba, pridat heartbeat ako extra diagnosticku vrstvu, nie ako hlavny safety prvok.

## 9. Production missing checklist - NIE JE DONE until explicitly validated

Firmware and ESP:

- NIE JE DONE: potvrdit Arduino IDE compile po opravach hlaviciek, BOM a `RS485_DE_PIN=21`.
- NIE JE DONE: potvrdit ze firmware publikuje feedback do 700 ms pri realnom brokeri.
- NIE JE DONE: potvrdit ze `/state` JSON sa cita spravne v backend runtime stave.
- DONE (SW): config profile switch existuje; aktivny je `WINDOW_PROFILE_TEST_NO_ENDSTOPS_SAFE` s 10 s limitom a 15 s WDT.

PWM module:

- NIE JE DONE: odmerat vystup PWM modulu na CH1 az CH4.
- NIE JE DONE: overit `OPEN:30`, `CLOSE:30`, `STOP`, potom kratko `OPEN:100` bez mechanickej zataze.
- NIE JE DONE: potvrdit polaritu/smerovanie H-mostikov.

Mechanika and safety:

- NIE JE DONE: fyzicky zapojit dorazy a potvrdit aktivnu logiku.
- NIE JE DONE: odmerat cas OPEN/CLOSE pre lavu aj pravu stranu.
- NIE JE DONE: nastavit produkcne max casy.
- NIE JE DONE: doplnit poistky/current-limit/hardware kill podla realnych prudov.
- NIE JE DONE: spravit burn-in test viac cyklov bez prehrievania.

Backend/Web:

- NIE JE DONE: test na RPI s realnym ESP modulom cez broker.
- NIE JE DONE: potvrdit ze dashboard uz nema feedback timeout pri funkcnej RS485 komunikacii.
- NIE JE DONE: potvrdit ze window prikazy v Scene Editore bezia rovnako ako manualne prikazy.

Docs:

- DONE: tento TODO je prepisany na `window` s dvomi motormi.
- NIE JE DONE: doplnit finalne realne hodnoty po merani: prud, casy, profil, zapojenie dorazov.

## 10. Navrhovane batch kroky

### Batch 1 - PWM signal only - PREBIEHA

- DONE: ACK timeout vratit na 700 ms.
- DONE: DE/RE pin ponechat `GPIO21`.
- DONE: test profil bez dorazov `WINDOW_PROFILE_TEST_NO_ENDSTOPS_SAFE`.
- NIE JE DONE: Arduino IDE compile potvrdeny pouzivatelom.
- NIE JE DONE: meranie PWM na vystupe modulu.

Odporucany test:

```text
1. Zapnut broker a backend na RPI.
2. Zapnut ESP window controller.
3. Subscribnut: mosquitto_sub -t 'room1/window/#' -v
4. Poslat z UI alebo MQTT: room1/window/left = OPEN:30
5. Merat CH1 PWM vystup modulu oproti GND.
6. Poslat: room1/window/left = STOP
7. Overit, ze CH1 padne na 0.
8. Poslat: room1/window/left = CLOSE:30
9. Merat CH2 PWM vystup modulu oproti GND.
10. Rovnako zopakovat pre pravu stranu CH3/CH4.
```

### Batch 2 - H-mostiky bez mechaniky - NIE JE DONE

- NIE JE DONE: pripojit H-mostiky bez zataze alebo s bezpecnou test zatazou.
- NIE JE DONE: potvrdit smer OPEN/CLOSE pre lavu a pravu stranu.
- NIE JE DONE: potvrdit STOP vypne oba smery.

### Batch 3 - Produkcne dorazy - NIE JE DONE

- NIE JE DONE: zapojit dorazy a zistit NC/NO logiku.
- NIE JE DONE: zapnut `endstopsEnabled = true` v produkcnom profile.
- NIE JE DONE: otestovat odmietnutie pohybu do aktivneho dorazu.
- NIE JE DONE: otestovat zastavenie pri dosiahnuti dorazu pocas pohybu.

### Batch 4 - Final production hardening - NIE JE DONE

- NIE JE DONE: odmerat realne casy a nastavit finalne produkcne runtime hodnoty; aktualny SW limit je 10 s.
- NIE JE DONE: doplnit hardware kill alebo iny sposob odpojenia napajania H-mostikov.
- NIE JE DONE: dlhodoby test cyklovania.
- NIE JE DONE: finalne upratat docs podla realneho zapojenia.
