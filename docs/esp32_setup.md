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
2. **Kľúčové Konfigurácie:** Ešte pred nahratím kódu na dosku musíte v hlavičke každého `*.ino` súboru upraviť nasledujúce konštanty (prípadne nájsť ich v prislúchajúcom hlavičkovom súbore `config.h` alebo na začiatku hlavného `.ino` súboru):
    ```cpp
    const char* ssid = "VAS_NAZOV_WIFI_SIETE";
    const char* password = "HESLO_WIFI_SIETE";
    const char* mqtt_server = "192.168.1.100";  // IP adresa Raspberry Pi
    ```
3. Uistite sa, že `mqtt_server` smeruje presne na lokálnu IP adresu vášho Raspberry Pi. Všetky zariadenia by mali bežať na rovnakej sieti bez dodatočnej filtrácie portu `1883`.
4. Pripojte vašu ESP32 dosku cez USB k počítaču.
5. V sekcii `Tools -> Board` vyberte **ESP32 Dev Module** (alebo iný konkrétny typ ktorý používate).
6. Vyberte správny `Port`, na ktorom sa doska objavila.
7. Kliknite na **Upload**.

---

## 3. Riešenie problémov (Hardware)

Po úspešnom nahratí môžete otvoriť **Serial Monitor** v Arduino IDE (Baud rate zväčša nastavený na `115200`).
Mali by ste ihneď vidieť:
1. Pripájanie do lokálnej WiFi siete.
2. Pokus o spojenie s MQTT Brokerom na zvolenej IP.
3. Správu `MQTT Connected!` a zoznam topics (kanálov), na ktoré sa zariadenie odoberá (napr. `room1/motor1` pre príjem príkazov).

Ak zariadenie indikuje `MQTT failed, rc=-2`, znamená to nedostupnosť broker servera (Raspberry Pi nie je zapnuté, nie je na sieti, alebo je nesprávne špecifikovaná jeho IP adresa vo vašom C++ kóde).
