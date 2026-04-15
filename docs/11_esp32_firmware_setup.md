# Nastavenie a kompilácia ESP32 Hardvéru

Tento dokument ukazuje, ako uviesť do prevádzky koncové mikrokontroléry ESP32 (Senzory a Aktory), ktoré komunikujú s Raspberry Pi.
Všetky kódy pre zariadenia sa nachádzajú v zložke `esp32/devices/wifi/`.

---

## 1. Technologické požiadavky

Na kompiláciu súčasnej verzie senzorov a aktorov budete potrebovať:
1. Nainštalované **Arduino IDE** (odporúčaná verzia 2.x).
2. Pridanú podporu pre ESP32 dosky v *Board Manager*.
   *(Vložte do Additional Boards Manager URLs JSON link od Espressif: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`)*
3. Dve hlavné externé knižnice dostupné cez Arduino Library Manager:
   - **`PubSubClient`** (od autora Nick O'Leary) - pre MQTT komunikáciu.
   - **`ArduinoJson`** (od autora Benoit Blanchon) - ak je vyžadované parsovanie.

---

## 2. Inštalačný postup do ESP32

Postup je pri všetkých uzloch (`esp32_mqtt_button`, `esp32_mqtt_controller_MOTORS` atď.) identický:

1. **Otvorte zložku** konkrétneho zariadenia (napríklad `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_button`) a dvoj-klikom spustite `.ino` súbor v Arduino IDE.
2. **Kľúčové Konfigurácie:** Konfigurácia siete a MQTT sa už nenachádza v hlavnom `.ino` súbore, ale v dedikovanom súbore `config.cpp` pre daný modul. Pred nahratím kódu tam upravte:
    ```cpp
    const char* WIFI_SSID = "VAS_NAZOV_WIFI_SIETE";
    const char* WIFI_PASSWORD = "HESLO_WIFI_SIETE";
    const char* MQTT_SERVER = "TechMuzeumRoom1.local";  // mDNS hostname alebo lokálna IP Raspberry Pi
    ```
    *Poznámka: Projekt tlačidla ponúka aj **ESPHome** alternatívy (`esp32_mqtt_button.yaml` a `esp32_mqtt_button_led.yaml`). V ich prípade nemusíte používať Arduino IDE; kompilujete a inicializujete priamo cez ESPHome.*
3. Uistite sa, že `MQTT_SERVER` smeruje na existujúci lokálny server vášho Raspberry Pi. Všetky zariadenia by mali bežať na rovnakej sieti bez dodatočnej filtrácie portu `1883`.
4. Pripojte vašu ESP32 dosku cez USB k počítaču.
5. V sekcii `Tools -> Board` vyberte **ESP32 Dev Module** (alebo iný konkrétny typ ktorý používate).
6. Vyberte správny `Port`, na ktorom sa doska objavila.
7. Kliknite na **Upload**.

---

## 3. MQTT Heartbeat a Status Publishing

Všetky Arduino firmvéry ESP32 zariadení (RELAY, MOTORS, BUTTON) pravidelne publikujú status heartbeat na tému `devices/{CLIENT_ID}/status` s payloadom `"online"`.

**Súčasné nastavenia:**
- **RELAY** (`esp32_mqtt_controller_RELAY`): `STATUS_PUBLISH_INTERVAL = 5000 ms` (5 sekúnd)
- **MOTORS** (`esp32_mqtt_controller_MOTORS`): `STATUS_PUBLISH_INTERVAL = 15000 ms` (15 sekúnd)
- **BUTTON** (`esp32_mqtt_button`): `STATUS_PUBLISH_INTERVAL = 5000 ms` (5 sekúnd)

**Dôležitá oprava (od apríla 2026):**
Pri opätovnom pripojení k MQTT brokeru sa heartbeat timer resetuje na `0`, aby sa status publikoval **ihneď** bez čakania na interval. To zamedzuje falošným "timeoutom" na Raspberry Pi, keď sa zariadenie krátko odpojí a znova pripojí.

- **RELAY**: `lastStatusPublish = 0` sa nastavuje po MQTT reconnecte v `connectToMqtt()`
- **MOTORS**: `lastStatusPublish = 0` sa nastavuje po `publishStatusImmediate()`
- **BUTTON**: `lastStatusPublish = 0` sa nastavuje po MQTT reconnecte v `connectToMqtt()`

**ESPHome varianty** (BUTTON YAML) to spravujú automaticky cez `on_connect` callback a `keepalive: 5s`.

---

## 4. Riešenie problémov (Hardware)

Po úspešnom nahratí môžete otvoriť **Serial Monitor** v Arduino IDE (Baud rate zväčša nastavený na `115200`).
Mali by ste ihneď vidieť:
1. Pripájanie do lokálnej WiFi siete.
2. Pokus o spojenie s MQTT Brokerom na zvolenej IP.
3. Správu `MQTT Connected!` a zoznam topics (kanálov), na ktoré sa zariadenie odoberá (napr. `room1/motor1` pre príjem príkazov).

**Problémy s MQTT:**

| Problém | Príčina | Riešenie |
|---------|--------|---------|
| `MQTT failed, rc=-2` | Server nedostupný | Uistite sa, že Raspberry Pi je zapnutá a na sieti. Skontrolujte IP v `config.cpp` |
| Zariadenie sa odpojí a prihlási `timeout` v logoch | Heartbeat sa neposielal po reconnecte (stará verzia firmware) | Aktualizujte firmware - resetujte `lastStatusPublish = 0` pri reconnecte |
| Zariadenie sa nezobrazuje ako `online` | Zariadenie sa nepripojilo k MQTT | Skontrolujte WiFi pripojenie a MQTT konfigáciu |
