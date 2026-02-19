# ESP32 MQTT Scene Trigger - Dokumentácia

## Prehľad projektu

Tento projekt slúži ako **jednoduchý MQTT spúšťač (tlačidlo)**. Po stlačení fyzického tlačidla odošle ESP32 správu na MQTT broker, ktorá slúži na odštartovanie scény v múzeu. Kód je optimalizovaný na **stabilitu 24/7** (Watchdog, Auto-reconnect).

---

## 🔧 Hardvér a Zapojenie

- **MCU:** ESP32 Dev Module
- **Vstup (Tlačidlo):** GPIO 32
- **Zapojenie tlačidla:** - Jeden vývod tlačidla na GPIO 32.
  - Druhý vývod na GND.
  - **Dôležité:** Kód počíta s externým pull-up rezistorom (rezistor medzi 3.3V a GPIO 32), preto je pin nastavený len ako `INPUT`.

---

## 📡 MQTT Konfigurácia

Zariadenie komunikuje cez MQTT protokol. Všetky nastavenia sú v súbore `config.cpp`.

### Odosielané správy (Trigger)
Keď užívateľ stlačí tlačidlo (a prejde cooldown), odošle sa:
- **Topic:** `room1/scene` (nastaviteľné cez `BASE_TOPIC_PREFIX` + `SCENE_TOPIC_SUFFIX`)
- **Payload:** `START`

### Status správy
Zariadenie pravidelne (každých 15s) alebo pri pripojení hlási svoj stav:
- **Topic:** `devices/Room1_ESP_Trigger/status`
- **Payload:** `online` (LWT správa pri výpadku je `offline`)

---

## 🛡️ Ochranné a Stabilizačné funkcie

Projekt obsahuje niekoľko vrstiev ochrany pre bezúdržbovú prevádzku:

### 1. Ošetrenie tlačidla (Anti-spam)
- **Debounce:** 60ms (odstránenie zámitov kontaktov)
- **Cooldown:** 4 sekundy (ochrana pred viacnásobným spustením scény tesne po sebe). Počas tohto času tlačidlo nereaguje.

### 2. Watchdog Timer (WDT)
- Ak sa procesor zasekne na viac ako **30 sekúnd**, hardvérový watchdog automaticky reštartuje celé ESP32.

### 3. WiFi & MQTT Reconnect
- **WiFi:** Ak vypadne WiFi, ESP32 sa pokúša znova pripojiť. Ak sa to nepodarí 5x po sebe (s narastajúcim odstupom), zariadenie sa reštartuje.
- **MQTT:** Ak je WiFi OK, ale padne MQTT, klient sa automaticky pokúša o znovupripojenie.

### 4. OTA Aktualizácie
- Umožňuje nahrávať nový firmvér bezdrôtovo cez Arduino IDE (Network Port).
- Pri štarte OTA sa dočasne vypne Watchdog, aby nedošlo k reštartu počas nahrávania.

---

## 📂 Štruktúra kódu

esp32_mqtt_button/  
├── esp32_mqtt_button.ino    # Hlavný loop, manažment úloh  
├── config.cpp / .h          # Nastavenia (WiFi, MQTT, Piny, Časy)  
├── hardware.cpp / .h        # Čítanie tlačidla, debounce logika  
├── mqtt_manager.cpp / .h    # Odosielanie správ, pripájanie k brokerovi  
├── wifi_manager.cpp / .h    # Správa WiFi pripojenia a reštartov  
├── connection_monitor.cpp   # Diagnostika stavu siete  
├── ota_manager.cpp          # Správa bezdrôtového nahrávania  
├── wdt_manager.cpp          # Watchdog timer  
└── debug.cpp                # Pomocné výpisy do konzoly  

---

## 🚀 Rýchly štart

1. Otvor `config.cpp`.
2. Uprav `WIFI_SSID` a `WIFI_PASSWORD`.
3. Uprav `MQTT_SERVER` (IP adresu brokera).
4. Nahraj kód do ESP32.
5. Sleduj Serial Monitor (115200 baud) pre potvrdenie pripojenia.
