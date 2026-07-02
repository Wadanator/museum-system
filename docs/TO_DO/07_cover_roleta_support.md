# Cover/Window Motor Control Plan

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short date or note if useful, and do not leave completed work only in chat or
git history.

Tento dokument popisuje implementačný návrh riadenia dvoch jednosmerných DC
motorov pre dizajnérske okná cez `cover` typ zariadenia v `museum-system`.

Dokument je zámerné iba implementačný návrh. V repozitári zatiaľ netreba meniť
Python, React ani ESP32 firmware kód, kým nie je potvrdený finálny hardware
a bezpečnostné správanie.

---

## Stav k 2026-07-02 - ESP32 SW nástrel

Tento dokument bol aktualizovaný po príprave prvého ESP32 firmware nástrelu.
ESP kód ešte nebol kompilovaný v Arduino IDE ani testovaný na reálnom HW,
preto je stav označený ako **SW draft / not HW-tested**.

**DONE - pripravené v ESP32 firmware nástrele:**

- Vytvorený nový firmware priečinok: `esp32/devices/lan/ArduinoIDE/esp32_mqtt_window_cover_controller`.
- Firmware je odvodený z LAN relay kódu, ale vyčistený na `cover` use case.
- Zachované sú LAN/WiFi fallback, MQTT reconnect, OTA, WDT, status LED a modulárne súbory.
- ESP32 ovláda externý PWM driver priamo cez onboard RS485/Modbus RTU (`GPIO17` TX, `GPIO18` RX), nie cez Raspberry Pi.
- Aktívne sú iba 2 motory: `room1/cover/1`, `room1/cover/2`.
- V kóde sú pripravené 4 softvérové cover sloty; `cover/3` a `cover/4` sú zatiaľ `enabled = false`.
- Pri aktuálnej schéme 2 PWM kanály na 1 motor je 4-kanálový PWM modul plne využitý dvoma motormi. Pre 4 aktívne motory treba 8 PWM výstupov alebo ďalšie HW rozšírenie.
- Implementované je smerové blokovanie, dead-time pri zmene smeru, end-stop polling, max runtime timeout, globálny STOP, MQTT loss stop, heartbeat timeout stop a OTA safe stop.
- MQTT feedback/state/status topicy sú v ESP nástrele implementované.
- Heartbeat timeout je nastavený na `20000 ms`; RPI má pri teste aj produkcii posielať `room1/system/heartbeat`.
- RPI feedback tracker bol skontrolovaný iba čítaním: ACK mechanizmus je kompatibilný pre `room1/cover/1 -> room1/cover/1/feedback` a `room1/cover/2 -> room1/cover/2/feedback`.

**OPEN - treba potvrdiť alebo dorobiť:**

- Potvrdiť presnú register mapu PWM modulu, duty scale, baud rate a Modbus slave ID podľa manuálu konkrétneho modulu.
- Skontrolovať Arduino build v Arduino IDE s knižnicami `PubSubClient`, `ArduinoOTA`, `ModbusMaster` a ESP32 core 3.x.
- Zapojenie HW ešte nebolo spravené: RS485 A/B/GND, DI dorazy, H-mostíky, motory, napájanie.
- Otestovať fyzické smery motorov, logiku NC/NO dorazov, timeout, heartbeat fail-safe, MQTT disconnect fail-safe a OTA safe stop.
- Backend zatiaľ nemení `cover` model. Feedback tracker ACK bude fungovať, ale plná semantika `/state` payloadov `OPEN`, `CLOSED`, `OPENING`, `CLOSING` potrebuje neskoršiu backend/UI podporu.

---

## 1. Cieľ integrácie

Do systému sa má pridať nový typ zariadenia:

- existujúce typy: `motor`, `relay`
- nový typ: `cover`

`cover` znamená motorický prvok s dvoma smermi pohybu (otvoriť/zatvoriť).
V tomto projekte ide konkrétne o jednosmerné DC motory ovládané PWM cez H-mostík.

Hlavný cieľ je, aby sa nový cover uzol z pohľadu systému správal rovnako
ako existujúce ESP32 uzly:

- prijíma príkazy cez room-scoped MQTT topicy,
- publikuje feedback na `<command_topic>/feedback`,
- publikuje stav zariadenia na `devices/<client_id>/status`,
- reaguje na `roomX/STOP`,
- dá sa pridať do `devices.json`,
- zobrazí sa vo frontende v Commands view,
- je dostupný v palete Scene Editora,
- vie byť použitý v JSON scénach cez štandardnú akciu `{"action": "mqtt"}`.

---

## 2. Hardware architektúra

### 2.1 Prehľad komponentov

| Komponent | Model | Úloha |
|---|---|---|
| Riadiaci modul | Waveshare ESP32-S3-ETH-8DI-8RO-PoE | MQTT, logika, DI vstupy, riadenie cez RS485 |
| PWM výstupný modul | 4-kanálový PWM Modbus RTU (elecom.sk) | Generovanie PWM signálu pre H-mostíky |
| H-mostík | L298N (2×) | Napájanie a smer DC motorov |
| Motory | 2× jednosmerný DC motor | Pohon okna |
| Dorazové snímače | 4× mechanický mikrospínač (NO/NC) | Horný a dolný doraz každého motora |
| Komunikácia | RS485 (Modbus RTU) | ESP32 → PWM modul |

### 2.2 Schéma zapojenia

```
Raspberry Pi
    │
    │ MQTT (TCP/IP, PoE LAN)
    ▼
Waveshare ESP32-S3-ETH-8DI-8RO-PoE
    │                          │
    │ RS485 (Modbus RTU)       │ 8× DI vstupy
    ▼                          ▼
4-ch PWM Modbus modul      Mikrospínače (end-stop)
    │ CH1, CH2, CH3, CH4       IN1..IN4 (horné/dolné dorazy)
    ▼
H-mostík L298N (Motor 1)   H-mostík L298N (Motor 2)
    │                              │
    ▼                              ▼
DC Motor 1 (Okno 1)         DC Motor 2 (Okno 2)
```

### 2.3 Mapovanie PWM kanálov na motory

| PWM kanál | Funkcia | H-mostík vstup |
|---|---|---|
| CH1 | Motor 1 — smer OPEN | ENA + IN1 |
| CH2 | Motor 1 — smer CLOSE | ENA + IN2 |
| CH3 | Motor 2 — smer OPEN | ENB + IN3 |
| CH4 | Motor 2 — smer CLOSE | ENB + IN4 |

Každý motor má teda pridelené 2 PWM kanály — jeden pre každý smer. Nikdy
nesmú byť aktívne súčasne oba kanály toho istého motora.

### 2.4 Mapovanie DI vstupov na end-stop snímače

| DI vstup | Snímač | Motor |
|---|---|---|
| DI1 | Horný doraz (OPEN) | Motor 1 |
| DI2 | Dolný doraz (CLOSE) | Motor 1 |
| DI3 | Horný doraz (OPEN) | Motor 2 |
| DI4 | Dolný doraz (CLOSE) | Motor 2 |
| DI5–DI8 | Rezerva | — |

Mikrospínače sú zapojené ako NC (normálne zatvorené) alebo NO — treba
overiť pri fyzickom zapojení a nastaviť logiku DI vstupu v kóde podľa toho.
Odporúčanie: NC je bezpečnejší (prerušenie kábla = doraz aktívny).

---

## 3. Waveshare ESP32-S3-ETH-8DI-8RO-PoE — konfigurácia

### 3.1 Piny a rozhrania

Relevantné piny pre tento projekt:

```text
W5500 Ethernet:
  CLK:  GPIO15
  MOSI: GPIO13
  MISO: GPIO14
  CS:   GPIO16
  INT:  GPIO12

I2C expander pre relé výstupy (TCA9554PWR, nepoužitý v cover nástrele):
  SDA: GPIO42
  SCL: GPIO41
  ADR: 0x20

RS485 (na doske vyvedený ako A/B pár):
  TX:  GPIO17  (potvrdené podľa Waveshare wiki)
  RX:  GPIO18  (potvrdené podľa Waveshare wiki)
  DE:  nezverejnený v pin tabuľke; firmware používa `RS485_DE_PIN = -1`

Poznámka: nepoužívať `GPIO8` ako RS485 DE bez ďalšieho potvrdenia. Podľa
Waveshare wiki je `GPIO8` digitálny vstup DI5.
```

Poznámka: relé výstupy (8× RO) nie sú v tomto projekte primárne využité.
Môžu slúžiť ako záložné bezpečnostné vypnutie (napr. vypnúť napájanie
H-mostíkov hardware cestou pri globálnom STOP).

### 3.2 RS485 / Modbus RTU konfigurácia

ESP32 komunikuje s PWM modulom cez RS485 Modbus RTU. Odporúčané nastavenia:

```text
Baud rate:   9600 (default pre väčšinu priemyselných PWM modulov)
Data bits:   8
Parity:      None
Stop bits:   1
Modbus ID:   1 (nastaviť na PWM module DIP prepínačmi)
```

Overiť skutočnú baud rate a Modbus ID z datasheetu konkrétneho PWM modulu
z elecom.sk (SKU 33921).

### 3.3 MQTT konfigurácia

```text
CLIENT_ID:    Window_Covers_Ctrl
STATUS_TOPIC: devices/Window_Covers_Ctrl/status
BASE_TOPIC:   room1/
SUBSCRIPTIONS:
  room1/cover/1
  room1/cover/2
  room1/STOP
  room1/system/heartbeat
```

---

## 4. PWM výstupný modul (Modbus RTU)

### 4.1 Ovládanie cez Modbus

PWM modul z elecom.sk (SKU 33921) je 4-kanálový priemyselný PWM výstup
s Modbus RTU cez RS485. Parametre PWM (duty cycle, frekvencia) sa nastavujú
zápisom do holding registrov.

Typické Modbus registre (overiť z datasheetu modulu):

| Register | Kanál | Popis |
|---|---|---|
| 0x0000 | CH1 | Duty cycle 0–1000 (0.0–100.0 %) |
| 0x0001 | CH2 | Duty cycle |
| 0x0002 | CH3 | Duty cycle |
| 0x0003 | CH4 | Duty cycle |

Príklad Modbus RTU zápisového príkazu pre CH1 na 75 % duty:

```text
Function code: 0x06 (Write Single Register)
Register:      0x0000
Value:         750  (= 75.0 %)
```

### 4.2 Nastavenie smeru vs. PWM

H-mostík L298N potrebuje okrem PWM aj smerové vstupy IN1/IN2. Existujú
dve možné schémy zapojenia:

**Schéma A (odporúčaná): ENA = PWM, smer cez relé alebo pevný vodič**

- CH1 ide na ENA (enable) H-mostíka,
- smer (IN1/IN2) je riadený relé výstupom ESP32 (RO1, RO2),
- jeden kanál PWM = regulácia rýchlosti, relé = smer.

**Schéma B: Každý smer = samostatný PWM kanál**

- CH1 = IN1 (dopredu), CH2 = IN2 (dozadu),
- ENA trvalo HIGH,
- aktívny je vždy iba jeden kanál, druhý = 0.

Schéma B je jednoduchšia na káblovanie a nepotrebuje relé pre smer —
odporúčaná pre tento projekt. Firmware zabezpečí, že nikdy nie sú oba
kanály toho istého motora nenulové súčasne.

---

## 5. Bezpečnostná logika (firmware)

Toto je najkritickejšia časť. Jednosmerný motor napájaný H-mostíkom môže
byť poškodený alebo spôsobiť mechanickú škodu pri nesprávnom riadení.

### 5.1 Smerové blokovanie (mutual exclusion)

**Pravidlo: Pre každý motor smú byť aktívne naraz maximálne 1 PWM kanál.**

```text
Motor 1:
  Pokiaľ CH1 > 0, CH2 musí byť = 0
  Pokiaľ CH2 > 0, CH1 musí byť = 0

Motor 2:
  Pokiaľ CH3 > 0, CH4 musí byť = 0
  Pokiaľ CH4 > 0, CH3 musí byť = 0
```

Toto sa vykonáva vždy softvérovo v ESP32 pred každým zápisom do Modbus
registrov — nie je to len politika, je to podmienka každého príkazu.

### 5.2 Dead-time pri zmene smeru

Pri prechode OPEN → CLOSE (alebo opačne):

```text
1. Nastaviť aktuálny aktívny kanál na 0 (motor stop)
2. Počkať 300–500 ms (dead-time)
3. Aktivovať opačný kanál
```

Dead-time zabraňuje prúdovému špičke pri okamžitej zmene smeru.

### 5.3 End-stop logika (dorazové snímače)

Mikrospínače sú zapojené na DI vstupy ESP32. ESP32 číta stav DI vstupov
asynchrónne (polling alebo interrupt).

```text
Motor 1 — OPEN smer:
  Ak DI1 aktívny (horný doraz) → okamžite CH1 = 0, ignorovať ďalšie OPEN
  príkazy kým DI1 aktívny

Motor 1 — CLOSE smer:
  Ak DI2 aktívny (dolný doraz) → okamžite CH2 = 0, ignorovať ďalšie CLOSE
  príkazy kým DI2 aktívny

(analogicky pre Motor 2 s DI3/DI4)
```

**Doraz = okamžitý stop (PWM = 0), bez soft-stop.**

Snímač sa overuje:
- aktívne počas pohybu (polling každých 50–100 ms),
- pred začatím pohybu (ak je doraz aktívny, príkaz sa odmietne s feedback ERROR).

### 5.4 Max runtime timeout

Ako záložná ochrana pri poruche snímača:

```text
MAX_MOVE_TIME_MS = 30000   // 30 sekúnd, nastaviť podľa skutočnej doby chodu
```

Ak sa motor pohybuje dlhšie ako tento limit bez dorazu, firmware vykoná
emergency stop (oba kanály = 0) a publikuje:

```text
room1/cover/1/feedback -> ERROR:TIMEOUT
```

### 5.5 Globálny STOP

Príkaz `room1/STOP` zastaví okamžite **všetky** motory:

```text
CH1 = 0, CH2 = 0, CH3 = 0, CH4 = 0  (Modbus write all channels)
Zrušiť všetky aktívne runtime timery
Publikovať feedback OK pre každý aktívny cover
```

### 5.6 Heartbeat watchdog

Raspberry Pi posiela periodicky:

```text
room1/system/heartbeat -> PING  (interval: 5 s)
```

ESP32 sleduje čas posledného heartbeatu. Ak nepríde do timeoutu:

```text
HEARTBEAT_TIMEOUT_MS = 20000  // 20 sekúnd
Akcia pri timeout: STOP všetkých motorov (rovnako ako globálny STOP)
Nepúšťať nové pohybové príkazy, kým sa heartbeat neobnoví
```

Heartbeat fail-safe nezatvára okná automaticky — iba zastaví pohyb.
Automatické zatváranie pri výpadku je aktívny pohyb a môže byť nebezpečné
(návštevník, exponát). Toto rozhodnutie treba potvrdiť.

---

## 6. Kanonický MQTT kontrakt

### 6.1 Command topics

```text
room1/cover/1    // Motor 1 (Okno 1)
room1/cover/2    // Motor 2 (Okno 2)
room1/STOP       // Globálny stop všetkých motorov
```

### 6.2 Payloady

| Payload | Význam |
|---|---|
| `OPEN` | Otvoriť okno (motor v smere OPEN, kým doraz alebo STOP) |
| `CLOSE` | Zatvoriť okno (motor v smere CLOSE, kým doraz alebo STOP) |
| `STOP` | Okamžite zastaviť pohyb |

Pozičné príkazy (`POS:50`) nie sú v tejto verzii implementované — chýba
enkodér alebo iná spätná väzba o polohe. Stačí OPEN/CLOSE/STOP.

### 6.3 Feedback

```text
room1/cover/1/feedback -> OK             // príkaz prijatý a vykonaný
room1/cover/1/feedback -> ERROR          // neplatný payload
room1/cover/1/feedback -> ERROR:TIMEOUT  // max runtime prekročený
room1/cover/1/feedback -> ERROR:ENDSTOP  // doraz aktívny, pohyb odmietnutý
```

### 6.4 Status topic

```text
devices/Window_Covers_Ctrl/status -> online   // periodicky každých 5–10 s
devices/Window_Covers_Ctrl/status -> offline  // MQTT will message
```

Interval musí byť kratší ako `device_timeout` v `config.ini.example`
(aktuálne `25` sekúnd), inak `MQTTDeviceRegistry` označí uzol ako offline,
aj keď reálne funguje — detail a rezerva v 10.2.3.

### 6.5 State topic

```text
room1/cover/1/state -> OPENING
room1/cover/1/state -> CLOSING
room1/cover/1/state -> OPEN      // doraz aktívny (horný)
room1/cover/1/state -> CLOSED    // doraz aktívny (dolný)
room1/cover/1/state -> STOPPED   // zastavený príkazom
room1/cover/1/state -> UNKNOWN   // stav neznámy (napr. po resete)
```

Payload je čistý text (nie JSON) — backend parser má očakávať plain string,
nie JSON objekt. Odôvodnenie a detaily v 10.2.4.

---

## 7. Firmware — implementačný návrh (Arduino/ESP-IDF)

### 7.1 Štruktúra CoverDevice

```cpp
struct CoverDevice {
  const char* topicName;       // napr. "cover/1"
  int pwmOpenChannel;          // Modbus register pre OPEN kanál (0-based)
  int pwmCloseChannel;         // Modbus register pre CLOSE kanál (0-based)
  int diOpenPin;               // DI vstup — horný doraz (open endstop)
  int diClosePin;              // DI vstup — dolný doraz (close endstop)
  unsigned long moveTimeoutMs; // max čas pohybu v ms
  // runtime stav:
  unsigned long moveStartTime;
  bool isMoving;
  int moveDirection;           // +1 = OPEN, -1 = CLOSE, 0 = stop
};
```

### 7.2 Postup pri príkaze OPEN

```text
1. Skontrolovať DI (horný doraz):
   - ak aktívny → feedback ERROR:ENDSTOP, koniec
2. Nastaviť pwmCloseChannel = 0 cez Modbus
3. Počkať dead-time (300 ms)
4. Nastaviť pwmOpenChannel = PWM_DUTY (napr. 800 = 80 %) cez Modbus
5. Zaznamenať moveStartTime = millis()
6. Nastaviť isMoving = true, moveDirection = +1
7. Publikovať room1/cover/1/state -> OPENING
8. Publikovať room1/cover/1/feedback -> OK
```

### 7.3 Postup pri príkaze CLOSE

```text
1. Skontrolovať DI (dolný doraz):
   - ak aktívny → feedback ERROR:ENDSTOP, koniec
2. Nastaviť pwmOpenChannel = 0 cez Modbus
3. Počkať dead-time (300 ms)
4. Nastaviť pwmCloseChannel = PWM_DUTY cez Modbus
5. Zaznamenať moveStartTime = millis()
6. Nastaviť isMoving = true, moveDirection = -1
7. Publikovať room1/cover/1/state -> CLOSING
8. Publikovať room1/cover/1/feedback -> OK
```

### 7.4 Postup pri príkaze STOP

```text
1. Nastaviť pwmOpenChannel = 0 a pwmCloseChannel = 0 cez Modbus
2. isMoving = false, moveDirection = 0
3. Zrušiť runtime timer
4. Publikovať room1/cover/1/state -> STOPPED
5. Publikovať room1/cover/1/feedback -> OK
```

### 7.5 Loop — pravidelné kontroly

Každých 50–100 ms:

```text
Pre každý CoverDevice kde isMoving == true:

  a) Skontrolovať doraz v smere pohybu:
     - OPEN a diOpenPin aktívny  → emergency stop, state = OPEN, feedback OK
     - CLOSE a diClosePin aktívny → emergency stop, state = CLOSED, feedback OK

  b) Skontrolovať timeout:
     - millis() - moveStartTime > moveTimeoutMs → emergency stop,
       feedback ERROR:TIMEOUT

  c) Emergency stop:
     - Modbus: oba kanály = 0
     - isMoving = false
```

### 7.6 Modbus write helper

```cpp
// Príklad s knižnicou ModbusMaster alebo vlastným UART Modbus RTU
void setPwmChannel(int channel, int duty) {
  // duty: 0–1000 (0.0–100.0 %)
  // channel: 0–3 (pre CH1–CH4)
  modbusClient.writeSingleRegister(0x0000 + channel, duty);
}
```

Pred zápisom vždy overiť smerové blokovanie — nikdy nepísať duty > 0
na oba kanály toho istého motora.

---

## 8. Manuálne MQTT testy

Pred zapojením do scén otestovať cez broker.

### 8.1 Subscribe na feedback a state

```bash
mosquitto_sub -h <broker_ip> -t 'room1/cover/#' -v
```

### 8.2 Otvoriť okno 1

```bash
mosquitto_pub -h <broker_ip> -t 'room1/cover/1' -m 'OPEN'
```

Očakávané:
```text
room1/cover/1/feedback -> OK
room1/cover/1/state    -> OPENING
... (po doraze) ...
room1/cover/1/state    -> OPEN
```

### 8.3 Zatvoriť okno 1

```bash
mosquitto_pub -h <broker_ip> -t 'room1/cover/1' -m 'CLOSE'
```

### 8.4 Stop

```bash
mosquitto_pub -h <broker_ip> -t 'room1/cover/1' -m 'STOP'
```

### 8.5 Globálny stop

```bash
mosquitto_pub -h <broker_ip> -t 'room1/STOP' -m 'STOP'
```

### 8.6 End-stop test

```text
1. Spustiť OPEN
2. Ručne aktivovať horný mikrospínač (simulovať doraz)
3. Overiť, že motor zastane a state = OPEN
4. Skúsiť znova OPEN → očakávané: ERROR:ENDSTOP
```

### 8.7 Heartbeat fail-safe test

```text
1. Spustiť heartbeat:
   mosquitto_pub -h <broker_ip> -t 'room1/system/heartbeat' -m 'PING' -l
   (loop mode, každú sekundu)
2. Spustiť pohyb okna
3. Zastaviť heartbeat (Ctrl+C)
4. Po 20 s overiť, že motor zastane
```

---

## 9. Bezpečnostné pravidlá

### 9.1 Smerové blokovanie

Smerové blokovanie musí riešiť **firmware** v ESP32 pred každým Modbus zápisom.
Nestačí spoliehať sa len na MQTT logiku. Dva aktívne PWM kanály toho istého
motora = možné poškodenie H-mostíka alebo motora.

### 9.2 End-stop snímače ako primárna ochrana

Mikrospínače sú primárna hardvérová ochrana pred mechanickým prechodom cez
krajnú polohu. Softvérový timeout je iba záloha pri poruche snímača.
Oba mechanizmy musia fungovať nezávisle.

### 9.3 Odporúčané zapojenie NC mikrospínačov

```text
NC (normálne zatvorený) je bezpečnejší ako NO:
  - prestrihnutý/odpojený kábel = snímač hlási aktívny doraz
  - firmware zastane, neposiela motor do prechodenia
```

### 9.4 Pohyb pri strate riadenia

Heartbeat fail-safe zastaví pohyb, ale **nespustí** aktívne zatváranie.
Aktívny pohyb pri výpadku komunikácie môže ohroziť návštevníka alebo exponát.
Toto rozhodnutie treba potvrdiť pred finálnou implementáciou.

### 9.5 Napájanie H-mostíka

H-mostíky L298N musia mať vlastný napájací zdroj pre motorovú časť (VM),
oddelený od logického napájania (VSS 5V). Pri výpadku VM motory zastanú
prirodzene — to je želané správanie.

Zvážiť pridanie hardware kill: jeden relé výstup ESP32 (RO1) ovláda
napájanie oboch H-mostíkov. Pri globálnom STOP alebo heartbeat timeout
môže firmware odpojiť VM napájanie hardwarovo, nielen nullovať PWM.

---

## 10. Backend a frontend integrácia

### 10.1 `devices.json` návrh

Aktuálny room config:

```text
raspberry_pi/config/rooms/room1/devices.json
```

Aktuálne obsahuje kľúče `motors` a `relays`. Navrhované rozšírenie o
`covers`:

```json
{
  "motors": [],
  "relays": [],
  "covers": [
    {
      "id": "cover_1",
      "name": "Okno 1",
      "type": "cover",
      "topic": "room1/cover/1",
      "nodeId": "Window_Covers_Ctrl",
      "esp32CoverIndex": 1,
      "supportsPosition": false,
      "heartbeatTopic": "room1/system/heartbeat",
      "failSafeAction": "STOP",
      "stopAction": "STOP"
    },
    {
      "id": "cover_2",
      "name": "Okno 2",
      "type": "cover",
      "topic": "room1/cover/2",
      "nodeId": "Window_Covers_Ctrl",
      "esp32CoverIndex": 2,
      "supportsPosition": false,
      "heartbeatTopic": "room1/system/heartbeat",
      "failSafeAction": "STOP",
      "stopAction": "STOP"
    }
  ]
}
```

Poznámky k poliam:

- `esp32CoverIndex` nahrádza Shelly-špecifický `coverId` (`cover:0`/`cover:1`
  index v rámci jedného Shelly zariadenia, ktorý sa pre tento hardware
  nehodí). Je to mapovací kľúč zodpovedajúci indexu v `CoverDevice[]` poli
  vo firmware tohto ESP32 uzla (pozri 7.1). Backend ho nijako nevyhodnocuje,
  iba ho preposiela/zobrazuje vo frontende pre debugging a servis.
- `supportsPosition` je natvrdo `false` — tento hardware nemá enkodér ani
  inú spätnú väzbu o polohe (pozri 6.2).
- `failSafeAction` je `"STOP"`, nie `"CLOSE"` — zodpovedá rozhodnutiu z
  5.6/9.4, že heartbeat fail-safe iba zastaví pohyb, nezatvára okno
  automaticky.

#### 10.1.1 Spätná kompatibilita pri ukladaní configu

`POST /api/devices` dnes validuje, že config obsahuje aspoň jeden z kľúčov:

```text
motors
relays
lights
```

Pre plnú podporu treba pridať aj `covers` (pozri 10.2.1). Kým sa backend
neupraví, config musí stále obsahovať aspoň prázdne `motors` alebo `relays`
polia — inak `POST /api/devices` vráti chybu validácie, aj keď je `covers`
pole vyplnené správne.

### 10.2 Backend (Raspberry Pi Python)

#### 10.2.1 Validácia `/api/devices`

Aktuálne: `motors / relays / lights`
Navrhované: `motors / relays / lights / covers`

#### 10.2.2 `MQTTActuatorStateStore` — rozšírenie

Pridať:

- `cover_state`: `OPEN`, `CLOSED`, `OPENING`, `CLOSING`, `STOPPED`, `UNKNOWN`
- `cover_position`: vždy `null` — tento hardware nemá pozičnú spätnú väzbu
  (pozri 6.2). Pole sa zachováva v štruktúre pre prípadnú budúcu
  kompatibilitu s pozičnými covermi (napr. Shelly v inej miestnosti), ale
  parser ho pre tento ESP32 typ nikdy nenastavuje.
- `cover_target`: vždy `null`, z rovnakého dôvodu.
- `cover_calibrated`: vždy `false` alebo `null` — kalibrácia sa v tejto
  verzii nepoužíva.

Mapovanie príkazov:

| Command | Desired cover state |
|---|---|
| `OPEN` | `OPENING` |
| `CLOSE` | `CLOSING` |
| `STOP` | `STOPPED` |

Feedback `OK` sám o sebe neznamená, že okno už dorazilo — iba že cover uzol
príkaz prijal. Skutočný finálny stav (`OPEN`/`CLOSED`) prichádza zo state
topicu po dosiahnutí dorazu (pozri 6.5, 7.5).

#### 10.2.3 Status interval a `device_timeout`

Status (`devices/Window_Covers_Ctrl/status -> online`) sa má posielať
periodicky každých 5–10 sekúnd (pozri 6.4). Aktuálny `config.ini.example`
má `device_timeout = 25`, takže interval musí byť kratší ako tento timeout
a mal by mať rezervu aspoň na niekoľko vynechaných heartbeatov — inak
`MQTTDeviceRegistry` označí uzol ako offline, hoci reálne funguje.

#### 10.2.4 Formát payloadu state topicu

State topic (`room1/cover/1/state`) posiela čistý textový payload, nie
JSON:

```text
OPENING
CLOSING
OPEN
CLOSED
STOPPED
UNKNOWN
```

Toto je vedomé zjednodušenie oproti JSON variante (relevantná pre Shelly
cover s pozíciou) — pretože `cover_position`, `cover_target` a
`cover_calibrated` sú pre tento hardware vždy `null`/`false`, JSON payload
by neprinášal žiadnu extra informáciu. Backend parser má očakávať plain
string, nie JSON objekt.

### 10.3 Frontend

Zmeny potrebné:

- rozšíriť `useDevices` o `covers` typ,
- pridať `CoverCard` komponent s tlačidlami OPEN / STOP / CLOSE,
- rozšíriť `CommandsView`,
- rozšíriť `useDevicePalette` a `EditorPalette` o `OPEN`, `CLOSE`, `STOP` akcie,
- runtime state zobraziť cez Socket.IO event `device_runtime_state_update`.

### 10.4 Scény — príklady

Otvoriť okno 1:
```json
{
  "action": "mqtt",
  "topic": "room1/cover/1",
  "message": "OPEN"
}
```

Zatvoriť pri konci scény:
```json
{
  "action": "mqtt",
  "topic": "room1/cover/1",
  "message": "CLOSE"
}
```

---

## 11. Rozhodnutia na potvrdenie pred implementáciou

1. **NC vs. NO mikrospínače** — potvrdiť typ, nastaviť inverznú logiku DI ak NC.
2. **PWM duty cycle** — aká rýchlosť motorov? Plný výkon (100 %) alebo obmedzený (napr. 70–80 %)?
3. **Schéma zapojenia H-mostíka** — Schéma A (relé pre smer) alebo Schéma B (2× PWM kanál)?
4. **MAX_MOVE_TIME_MS** — namerať skutočnú dobu prechodu okna a nastaviť s rezervou +50 %.
5. **DONE 2026-07-02:** Heartbeat timeout akcia — iba STOP, nie automatické CLOSE.
6. **Hardware kill relé** — použiť RO výstup ESP32 pre napájanie VM H-mostíkov?
7. **Modbus slave ID** — nastaviť DIP prepínačmi na PWM module, skontrolovať default.
8. **PARTIAL 2026-07-02:** RS485 TX/RX piny overené podľa Waveshare wiki (`GPIO17`/`GPIO18`); DE pin nie je v pin tabuľke, firmware ho necháva vypnutý (`-1`).

---

## 12. Implementačný checklist

### 12.1 Hardware

- [ ] Zapojiť mikrospínače na DI1–DI4 (NC alebo NO, zdokumentovať)
- [ ] Zapojiť PWM modul cez RS485 (A/B, GND)
- [ ] Nastaviť Modbus slave ID na PWM module
- [ ] Zapojiť H-mostíky (L298N) podľa zvolenej schémy
- [ ] Zapojiť motory na H-mostíky
- [ ] Overiť napájanie VM (motorová časť) a VSS (logika)
- [ ] Fyzicky otestovať smer motorov (OPEN = skutočné otváranie)

### 12.2 ESP32 Firmware

- [ ] PARTIAL 2026-07-02: Overiť RS485 piny na PoE variante dosky - TX/RX potvrdené podľa wiki, DE zostáva fyzicky neoverené
- [x] DONE 2026-07-02 SW draft: Implementovať Modbus RTU klienta (knižnica `ModbusMaster` alebo vlastná)
- [x] DONE 2026-07-02 SW draft: Implementovať `CoverDevice`/`CoverConfig` štruktúru
- [x] DONE 2026-07-02 SW draft: Implementovať smerové blokovanie (mutual exclusion)
- [x] DONE 2026-07-02 SW draft: Implementovať dead-time pri zmene smeru
- [x] DONE 2026-07-02 SW draft: Implementovať end-stop polling
- [x] DONE 2026-07-02 SW draft: Implementovať max runtime timeout
- [x] DONE 2026-07-02 SW draft: Implementovať MQTT parser pre `room1/cover/1`, `room1/cover/2`, `room1/STOP`
- [x] DONE 2026-07-02 SW draft: Implementovať heartbeat watchdog (`20000 ms`)
- [x] DONE 2026-07-02 SW draft: Implementovať state topic a feedback topic publikovanie
- [x] DONE 2026-07-02 SW draft: Implementovať `devices/Window_Covers_Ctrl/status` (periodický online)

### 12.3 Backend

- [ ] Pridať `covers` pole do `devices.json` (pozri 10.1)
- [ ] Povoliť `cover` v device validácii — kým sa nedokončí, `motors`/`relays`
      musia ostať v configu aspoň ako prázdne polia (pozri 10.1.1)
- [ ] Pridať heartbeat publisher - ESP firmware už očakáva `room1/system/heartbeat` každých pár sekúnd
- [ ] Rozšíriť state store o cover stavy: `cover_state`, `cover_position`
      (vždy `null`), `cover_target` (vždy `null`), `cover_calibrated`
      (vždy `false`/`null`) — pozri 10.2.2
- [ ] Spracovať `/state` a `/feedback` topicy — plain text payload, nie
      JSON (pozri 10.2.4). 2026-07-02: ACK feedback je kompatibilný už teraz, cover `/state` semantika ostáva backend TODO.
- [ ] Doplniť testy

### 12.4 Frontend

- [ ] `CoverCard` komponent
- [ ] Rozšíriť `CommandsView`
- [ ] Rozšíriť Scene Editor paletu
- [ ] Runtime state cez Socket.IO

### 12.5 Dokumentácia

Po implementácii aktualizovať:

- `docs/04_mqtt_protocol.md`
- `docs/09_dashboard_api.md`
- `docs/12_physical_installation.md`
- tento dokument

---

## 13. Externé referencie

- Waveshare ESP32-S3-ETH-8DI-8RO wiki: `https://www.waveshare.com/wiki/ESP32-S3-ETH-8DI-8RO`
- PWM Modbus modul (SKU 33921): `https://www.elecom.sk/priemyselny-4-kanalovy-pwm-vystupny-modul--protokol-modbus-rtu--izolovane-rozhranie-rs485/`
- L298N H-mostík datasheet: `https://www.st.com/resource/en/datasheet/l298.pdf`
- Arduino ModbusMaster knižnica: `https://github.com/4-20ma/ModbusMaster`
