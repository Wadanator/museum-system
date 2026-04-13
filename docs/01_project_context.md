# Konštitúcia projektu (Bakalárska práca)

## 1. Zmysel projektu (High-Level Overview)
Tento projekt predstavuje integrovaný riadiaci systém `museum-system` určený pre interaktívne múzeá, expozície a iné zážitkové inštalácie.
Systém v reálnom čase koordinuje zvuk, video a hardvérové zariadenia v miestnostiach z jedného centrálneho backendu. Logika priebehu miestnosti je definovaná konfiguračnými JSON scénami.

## 2. Technologický Stack (Codebase)
Základný priečinok obsahuje 3 samostatné subprojekty, ktoré sa prepájajú cez sieťové protokoly:

### A) Raspberry Pi Backend (`/raspberry_pi`)
**Technológie**: Python 3.10+, `pygame` (audio engine), `mpv` (video engine), `paho-mqtt`, `jsonschema`, Flask, Flask-SocketIO.
**Zodpovednosť**: Centrálny backend systému s `MuseumController`. Načítava scény, riadi `StateMachine` pre bežiacu miestnosť a spúšťa MQTT príkazy pre svetlá, relé a motory podľa času a vstupov zo systému.

### B) ESP32 Firmware/Hardware (`/esp32`)
**Technológie**: C++ (Arduino framework), PubSubClient, GPIO.
**Zodpovednosť**: Vykonávacia vrstva pre tlačidlá, motory a relé. ESP32 uzly počúvajú MQTT príkazy z Raspberry Pi a publikujú spätné hlásenia aj stav zariadení.

### C) Múzejný Webový Dashboard (`/museum-dashboard`)
**Technológie**: React.js, Vite, Socket.IO Client.
**Zodpovednosť**: Ovládací panel pre obsluhu múzea. Zobrazuje stav miestností, zariadení, logy a umožňuje manuálne ovládanie scén a príkazov.

---

## 3. Ako systém žije? (Runtime a Komunikácia)

1. Centralizovaná event-driven komunikácia: Celý systém si vymieňa veľmi malé a rýchle správy cez **Sieťový protokol MQTT** (broker).
    - Raspberry Pi zverejní (Publish): `room1/motor1` s payloadom `ON:100:L` (alebo `room1/relay1` s payloadom `ON`).
    - ESP32 počúva na tom topicu a pustí silu do domáceho motora (alebo relé). Následne odvetí spätne úspechom na `room1/motor1/feedback`.
2. Architektonické detaily MQTT topicov: Všetky detaily sú už rozpísané v `/docs/04_mqtt_protocol.md`.
3. Akčná postupnosť scény: Mozog v Pythone spracuje vstup podľa daného bodu vo vývojovom strome json súboru scény a aplikuje akcie, ktorými sú: prehratie hudby cez reproduktory (`action: audio`), vyžiadanie motorického pohybu dverí (`action: mqtt`), prehratie video slučky puzla na monitore v miestnosti (`action: video`). Pričom logické prechody medzi jednotlivými stavmi môžu byť vynútené operátorom, časovým uplynutím (timeout) alebo dohraním nejakého media klipu.

## 4. Dodatočná existujúca dokumentácia vo vašom repozitári

Ak budete mať vy alebo vaša AI pochybnosti o detailoch konkrétnych subsystémov, v priečinku `/docs` je aktuálne relevantná dokumentácia:

* `docs/02_system_architecture.md` (aktuálna runtime architektúra)
* `docs/03_file_structure.md` (aktuálna štruktúra repozitára)
* `docs/04_mqtt_protocol.md` (MQTT topicy a payloady)
* `docs/05_esp32_hardware_reference.md` (ESP32 hardvérové referencie)
* `docs/06_scene_state_machine.md` (stavový model scén)
* `docs/07_audio_engine.md` (audio správanie)
* `docs/08_video_engine.md` (video správanie)
* `docs/09_dashboard_api.md` (API dashboardu)
* `docs/10_museum_backend_setup.md` (nastavenie backendu)
* `docs/11_esp32_firmware_setup.md` (nastavenie ESP32 firmvéru)
* `docs/12_physical_installation.md` (fyzická inštalácia)
* `docs/13_rpi_hardware_watchdog_setup.md` (watchdog setup pre Raspberry Pi)

---
