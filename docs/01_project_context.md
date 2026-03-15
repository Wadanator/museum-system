# Konštitúcia projektu (Bakalárska práca)


## 1. Zmysel projektu (High-Level Overview)
Tento projekt predstavuje integrovaný riadiaci systém (`museum-system`) určený pre interaktívne múzeá ako, expozície či iné zážitkové inštalácie. 
Systém v reálnom čase orchesteruje zvuky, videá a hardvérové zariadenia v reálnych miestnostiach z jedného centrálneho mozgu. Logika, podľa ktorej sa veci v miestnostiach odohrávajú, je dynamicky určená pomocou konfiguračných stavových JSON súborov (označované ako "scény").

## 2. Technologický Stack (Codebase)
Základný priečinok obsahuje 4 rôzne úplne nezávislé sub-projekty, ktoré sa prepájajú pomocou sieťových protokolov:

### A) Raspberry Pi Backend (`/raspberry_pi`)
**Technológie**: Python 3.10+, PyGame (audio engine), `mpv` (video engine), Paho MQTT (komunikácia s HW), jsonschema \& Transitions (stavové automaty a validácia scén), Flask \& Socket.IO (rest/websocket API).
**Zodpovednosť**: Centrálny mozog systému s názvom `MuseumController`. Beží nonstop. Načítava scény, spúšťa `StateMachine` pre každú prebiehajúcu izbu. Zabezpečuje, že sa na základe času a senzorov prehráva hudba a spúšťajú sa MQTT príkazy na ovládanie svetiel/relé/motorov.

### B) ESP32 Firmware/Hardware (`/esp32`)
**Technológie**: C++ (Arduino framework / ESPHome), PubSubClient (MQTT protokoly), GPIO.
**Zodpovednosť**: Vykonalá vrstva (Aktory a Senzory). Mikrokontroléry ESP32 umiestnené za stenami izieb počúvajú na domácej sieti na špeciálne MQTT príkazy z Raspberry Pi (napr. otvor dvere, rýchlo toč motorom). Samy posielajú signály, ak hráč stlačí na scéne fyzické tlačidlo (`esp32_mqtt_button`).

### C) Múzejný Webový Dashboard (`/museum-dashboard`)
**Technológie**: React.js, TailwindCSS, Socket.IO Client.
**Zodpovednosť**: Riadiaci panel (GUI) pre obsluhu múzea (Game Mastera). Panel zobrazuje na obrazovke, čo sa reálne v miestnostiach práve deje, ktoré zariadenia sú pripojené/odpojené k sieti (online status check), poskytuje možnosť manuálne preklenúť prechody stavov alebo posielať manuálne "override" príkazy (napr. force STOP scény).

---

## 3. Ako systém žije? (Runtime a Komunikácia)

1. Centralizovaná event-driven komunikácia: Celý systém si vymieňa veľmi malé a rýchle správy cez **Sieťový protokol MQTT** (broker).
    - Raspberry Pi zverejní (Publish): `room1/motor1` s payloadom `ON:100:L` (alebo `room1/relay1` s payloadom `ON`).
    - ESP32 počúva na tom topicu a pustí silu do domáceho motora (alebo relé). Následne odvetí spätne úspechom na `room1/motor1/feedback`.
2. Architektonické detaily MQTT topicov: Všetky detaily sú už rozpísané v `/docs/mqtt_topics.md`.
3. Akčná postupnosť scény: Mozog v Pythone spracuje vstup podľa daného bodu vo vývojovom strome json súboru scény a aplikuje akcie, ktorými sú: prehratie hudby cez reproduktory (`action: audio`), vyžiadanie motorického pohybu dverí (`action: mqtt`), prehratie video slučky puzla na monitore v miestnosti (`action: video`). Pričom logické prechody medzi jednotlivými stavmi môžu byť vynútené operátorom, časovým uplynutím (timeout) alebo dohraním nejakého media klipu.

## 4. Dodatočná existujúca dokumentácia vo vašom repozitári

Ak budete mať vy, alebo vaša AI pochybnosti o do-hĺbkových detailoch konkrétnych subsystémov, v priečinku `/docs` máte užitočne zdokumentované pre AI:

* `docs/architecture.md` (Topológia v reálnom čase, vrstvy pi kódu a podrobné vnútornosti)
* `docs/mqtt_topics.md` (Štruktúra vašich komunikačných kanálov medzi Python serverom a ESP32 HW nodes)
* `docs/esp32_hardware_reference.md` (Kompletné zhrnutie PWM nastavení a mapovania hardvérových pinov pre každý ESP32 modul)
* `docs/file_structure.md` (Kompletná adresárová štruktúra repozitára)
* `docs/dashboard_api.md` (Zoznam všetkých REST a WebSocket endpointov pre komunikáciu medzi Pi a Reactom)
* `docs/museum_setup_guide.md` & `/docs/audio_playing_tutorial.md` atď.

---
