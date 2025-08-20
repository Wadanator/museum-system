# ESP32 MQTT Controller - Dokumentácia

## Prehľad projektu

Tento projekt implementuje MQTT kontrolér pre ESP32, ktorý ovláda rôzne hardvérové zariadenia (motor, svetlo, para) cez MQTT protokol. Kód je rozdelený do modulárnej štruktúry pre lepšiu údržbu a rozšíriteľnosť.

## Štruktúra súborov

```
esp32_mqtt_controller/
├── esp32_mqtt_controller.ino    # Hlavný Arduino súbor
├── config.h                     # Deklarácie konštánt
├── config.cpp                   # Implementácia konfigurácie
├── debug.h                      # Debug funkcie - hlavička
├── debug.cpp                    # Debug implementácia
├── hardware.h                   # Hardware ovládanie - hlavička
├── hardware.cpp                 # Hardware implementácia
├── wifi_manager.h               # WiFi manažment - hlavička
├── wifi_manager.cpp             # WiFi implementácia
├── mqtt_manager.h               # MQTT manažment - hlavička
├── mqtt_manager.cpp             # MQTT implementácia
├── connection_monitor.h         # Monitorovanie - hlavička
└── connection_monitor.cpp       # Monitorovanie implementácia
```

---

## Detailný popis implementačných súborov (.cpp)

### 1. `esp32_mqtt_controller.ino` - Hlavný súbor

**Účel:** Hlavný vstupný bod aplikácie, obsahuje `setup()` a `loop()` funkcie.

**Čo robí:**
- **Inicializácia Watchdog Timer** - Nastavuje watchdog s 30s timeout pre automatický restart pri zamrznutí
- **Volanie inicializačných funkcií** - Postupne inicializuje hardware, WiFi a MQTT
- **Hlavný loop** - Nepretržite monitoruje pripojenia, udržiava WiFi a MQTT spojenie
- **Reset watchdog** - V každom cykle resetuje watchdog timer

**Kľúčové funkcie:**
```cpp
void setup()    // Jednorazová inicializácia pri štarte
void loop()     // Nekonečná slučka - hlavná logika
```

**Závislosti:** Používa všetky ostatné moduly.

---

### 2. `config.cpp` - Konfiguračné hodnoty

**Účel:** Centralizované úložisko všetkých konfiguračných konštánt.

**Čo obsahuje:**
- **WiFi údaje** - SSID a heslo pre WiFi sieť
- **MQTT nastavenia** - IP adresa brokera, port, klient ID, topic prefix
- **Hardware definície** - Čísla GPIO pinov pre motor, svetlo a paru
- **Timing konštanty** - Intervaly pre reconnect, status publishing, monitoring
- **Limity** - Maximálne pokusy o pripojenie, timeout hodnoty

**Prečo je dôležitý:**
- Všetky nastavenia na jednom mieste
- Ľahké upravovanie bez hľadania po kóde
- Konzistentné používanie hodnôt v celom projekte

---

### 3. `debug.cpp` - Debug systém

**Účel:** Poskytuje jednotný systém pre debug výpisy.

**Čo robí:**
- **Podmienené výpisy** - Zobrazuje debug správy len ak je `DEBUG = true`
- **Timestamp** - Pridáva čas v milisekundách k každej správe
- **Formátovanie** - Jednotný formát: `[DEBUG] 12345ms - správa`

**Implementácia:**
```cpp
void debugPrint(const String& message) {
  if (DEBUG) {
    Serial.print("[DEBUG] ");
    Serial.print(millis());
    Serial.print("ms - ");
    Serial.println(message);
  }
}
```

**Výhody:**
- Jednoduché vypínanie debug výpisov
- Konzistentné formátovanie
- Performance optimalizácia (žiadne výpisy v release verzii)

---

### 4. `hardware.cpp` - Ovládanie hardvéru

**Účel:** Centralizované ovládanie všetkých hardvérových komponentov.

**Komponenty:**
- **Motor** - GPIO pin 4, príkazy: START/STOP
- **Svetlo** - GPIO pin 5, príkazy: ON/OFF  
- **Para** - GPIO pin 14, príkazy: ON/OFF

**Kľúčové funkcie:**
```cpp
void initializeHardware()     // Nastavenie pinov, vypnutie všetkého
void controlMotor(command)    // Ovládanie motora
void controlLight(command)    // Ovládanie svetla
void controlSteam(command)    // Ovládanie pary
void turnOffHardware()        // Bezpečnostné vypnutie všetkého
```

**Bezpečnostné funkcie:**
- **Automatické vypnutie** pri strate MQTT pripojenia
- **Stav hardwareOff** - sleduje či je hardware bezpečnostne vypnutý
- **Validácia príkazov** - kontroluje neznáme príkazy

**Logika:**
- Pri každom zapnutí zariadenia sa nastaví `hardwareOff = false`
- Pri strate pripojenia sa všetko vypne a nastaví `hardwareOff = true`
- Zabraňuje opakovanému vypínaniu

---

### 5. `wifi_manager.cpp` - WiFi manažment

**Účel:** Kompletná správa WiFi pripojenia s pokročilými funkciami.

**Hlavné funkcie:**
```cpp
bool initializeWiFi()     // Prvotné pripojenie k WiFi
void reconnectWiFi()      // Automatické opätovné pripájanie
bool isWiFiConnected()    // Kontrola stavu pripojenia
```

**Pokročilé funkcie:**
- **Exponenciálny backoff** - Postupne predlžuje intervaly medzi pokusmi
- **Maximálne pokusy** - Po 5 neúspešných pokusoch reštartuje ESP32
- **Automatická detekcia** - Rozpozná stratu a obnovu pripojenia
- **Status tracking** - Udržiava globálny stav `wifiConnected`

**Retry logika:**
1. Prvý pokus: okamžite
2. Druhý pokus: po 5 sekundách  
3. Tretí pokus: po 10 sekundách
4. Štvrtý pokus: po 20 sekundách
5. Piaty pokus: po 40 sekundách
6. Ak všetko zlyhá: restart ESP32

**Výhody:**
- Odolnosť proti dočasným výpadkom WiFi
- Šetrenie energie (nekonštantné pokusy)
- Automatické zotavenie

---

### 6. `mqtt_manager.cpp` - MQTT manažment

**Účel:** Komplexný MQTT klient s automatickým pripájaním a spracovaním správ.

**Hlavné komponenty:**
- **PubSubClient objekt** - Hlavný MQTT klient
- **Callback systém** - Spracovanie prichádzajúcich správ
- **Status publishing** - Pravidelné oznamovanie stavu "online"
- **Topic management** - Správa MQTT topic štruktúry

**Kľúčové funkcie:**
```cpp
void initializeMqtt()        // Nastavenie servera a callback
void connectToMqtt()         // Pripojenie s retry logikou
void mqttCallback()          // Spracovanie prichádzajúcich správ
void publishStatus()         // Publikovanie stavu zariadenia
void mqttLoop()              // Udržiavanie MQTT spojenia
```

**Topic štruktúra:**
- **Príkazy:** `room1/motor`, `room1/light`, `room1/steam`
- **Status:** `devices/esp32_wifi_controller/status`
- **Will message:** "offline" pri neočakávanom odpojení

**Callback logika:**
```
Príchod správy → Parsovanie topic → Identifikácia zariadenia → Vykonanie príkazu
```

**Retry mechanizmus:**
- Podobný ako WiFi - exponenciálny backoff
- Last Will Testament pre indikáciu odpojenia
- Automatické opätovné prihlásenie na topics

**Bezpečnosť:**
- Kontrola WiFi pripojenia pred MQTT pokusmi
- Automatické vypnutie hardware pri strate MQTT
- Keep-alive mechanizmus (15 sekúnd)

---

### 7. `connection_monitor.cpp` - Monitorovanie pripojení

**Účel:** Centrálne monitorovanie stavu všetkých pripojení a diagnostika.

**Čo monitoruje:**
- **WiFi stav** - `WiFi.status() == WL_CONNECTED`
- **MQTT stav** - `client.connected()`
- **Zmeny stavu** - Detekcia straty a obnovy pripojenia

**Implementácia:**
```cpp
void monitorConnections() {
    // Každých 10 sekúnd kontrola
    if (currentTime - lastConnectionCheck >= CONNECTION_CHECK_INTERVAL) {
        // Log aktuálneho stavu
        debugPrint("Status - WiFi: OK/FAIL, MQTT: OK/FAIL");
        
        // Detekcia zmien stavu
        // Aktualizácia globálnych premenných
    }
}
```

**Diagnostické informácie:**
- Pravidelné status logy každých 10 sekúnd
- Detekcia a logovanie zmien stavu
- Synchronizácia globálnych stavových premenných

**Výhody:**
- Prehľad o stave systému
- Včasná detekcia problémov  
- Debug informácie pre ladenie

---

## Globálne premenné a stav

### Stavové premenné:
```cpp
bool wifiConnected = false;        // Stav WiFi pripojenia
bool mqttConnected = false;        // Stav MQTT pripojenia  
bool hardwareOff = false;          // Stav hardware (bezpečnostne vypnuté)
```

### Timing premenné:
```cpp
unsigned long lastWifiAttempt = 0;      // Čas posledného WiFi pokusu
unsigned long lastMqttAttempt = 0;      // Čas posledného MQTT pokusu
unsigned long lastStatusPublish = 0;    // Čas posledného status publish
unsigned long lastConnectionCheck = 0;  // Čas poslednej kontroly pripojení
```

---

## Tok programu

### Inicializácia (setup):
1. **Serial komunikácia** (115200 baud)
2. **Watchdog Timer** (30s timeout)  
3. **Hardware inicializácia** (nastavenie pinov, vypnutie)
4. **WiFi pripojenie** (prvotný pokus)
5. **MQTT konfigurácia** (server, callback)

### Hlavný cyklus (loop):
1. **Reset watchdog** - zabránenie reštartu
2. **Monitor pripojení** - kontrola stavov každých 10s
3. **WiFi management** - reconnect ak treba
4. **MQTT management** - pripojenie ak WiFi OK
5. **MQTT loop** - spracovanie správ a status publish
6. **Hardware safety** - vypnutie pri strate MQTT
7. **Delay 50ms** - šetrenie CPU

---

## Bezpečnostné mechanizmy

### 1. Watchdog Timer
- **Timeout:** 30 sekúnd
- **Funkcia:** Automatický restart pri zamrznutí
- **Reset:** V každom loop cykle

### 2. Hardware Safety
- **Trigger:** Strata MQTT pripojenia
- **Akcia:** Vypnutie všetkých zariadení
- **Ochrana:** Pred nekontrolovaným chodom

### 3. Connection Retry Limits
- **WiFi:** Max 5 pokusov → restart
- **MQTT:** Max 5 pokusov → restart  
- **Zabránenie:** Nekonečným pokusom

### 4. Exponential Backoff
- **Účel:** Šetrenie zdrojov
- **Logika:** Postupne dlhšie pauzy
- **Maximum:** 60 sekúnd medzi pokusmi

---

## Rozšíriteľnosť

### Pridanie nového zariadenia:
1. **Konfigurácia:** Pridať pin do `config.h/cpp`
2. **Hardware:** Pridať control funkciu do `hardware.cpp`
3. **MQTT:** Pridať case do `mqttCallback` funkcie
4. **Topic:** Rozšíriť topic štruktúru

### Pridanie nového sensoru:
1. **Hardware:** Čítanie hodnôt v `hardware.cpp`
2. **MQTT:** Publishing v `mqtt_manager.cpp`
3. **Timing:** Nový interval v config

### Pridanie WiFi portálu:
1. **Nový modul:** `wifi_portal.h/cpp`
2. **Integrácia:** Volanie z `wifi_manager.cpp`
3. **Fallback:** Pri zlyhaní štandardného pripojenia

Projekt je navrhnutý modulárne, takže pridávanie nových funkcií je jednoduché bez narušenia existujúceho kódu.


# ESP32 MQTT Controller - Documentation

## Project Overview

This project implements an MQTT controller for ESP32 that controls various hardware devices (motor, light, steam) via MQTT protocol. The code is divided into a modular structure for better maintenance and extensibility.

## File Structure

```
esp32_mqtt_controller/
├── esp32_mqtt_controller.ino    # Main Arduino file
├── config.h                     # Constants declarations
├── config.cpp                   # Configuration implementation
├── debug.h                      # Debug functions - header
├── debug.cpp                    # Debug implementation
├── hardware.h                   # Hardware control - header
├── hardware.cpp                 # Hardware implementation
├── wifi_manager.h               # WiFi management - header
├── wifi_manager.cpp             # WiFi implementation
├── mqtt_manager.h               # MQTT management - header
├── mqtt_manager.cpp             # MQTT implementation
├── connection_monitor.h         # Monitoring - header
└── connection_monitor.cpp       # Monitoring implementation
```

---

## Detailed Description of Implementation Files (.cpp)

### 1. `esp32_mqtt_controller.ino` - Main File

**Purpose:** Main entry point of the application, contains `setup()` and `loop()` functions.

**What it does:**
- **Watchdog Timer Initialization** - Sets up watchdog with 30s timeout for automatic restart on freeze
- **Initialization Function Calls** - Sequentially initializes hardware, WiFi, and MQTT
- **Main Loop** - Continuously monitors connections, maintains WiFi and MQTT connection
- **Watchdog Reset** - Resets watchdog timer in each cycle

**Key Functions:**
```cpp
void setup()    // One-time initialization at startup
void loop()     // Infinite loop - main logic
```

**Dependencies:** Uses all other modules.

---

### 2. `config.cpp` - Configuration Values

**Purpose:** Centralized storage of all configuration constants.

**What it contains:**
- **WiFi Credentials** - SSID and password for WiFi network
- **MQTT Settings** - Broker IP address, port, client ID, topic prefix
- **Hardware Definitions** - GPIO pin numbers for motor, light, and steam
- **Timing Constants** - Intervals for reconnect, status publishing, monitoring
- **Limits** - Maximum connection attempts, timeout values

**Why it's important:**
- All settings in one place
- Easy modification without searching through code
- Consistent use of values throughout the project

---

### 3. `debug.cpp` - Debug System

**Purpose:** Provides unified system for debug outputs.

**What it does:**
- **Conditional Outputs** - Shows debug messages only if `DEBUG = true`
- **Timestamp** - Adds time in milliseconds to each message
- **Formatting** - Uniform format: `[DEBUG] 12345ms - message`

**Implementation:**
```cpp
void debugPrint(const String& message) {
  if (DEBUG) {
    Serial.print("[DEBUG] ");
    Serial.print(millis());
    Serial.print("ms - ");
    Serial.println(message);
  }
}
```

**Advantages:**
- Easy debug output toggling
- Consistent formatting
- Performance optimization (no outputs in release version)

---

### 4. `hardware.cpp` - Hardware Control

**Purpose:** Centralized control of all hardware components.

**Components:**
- **Motor** - GPIO pin 4, commands: START/STOP
- **Light** - GPIO pin 5, commands: ON/OFF  
- **Steam** - GPIO pin 14, commands: ON/OFF

**Key Functions:**
```cpp
void initializeHardware()     // Pin setup, turn everything off
void controlMotor(command)    // Motor control
void controlLight(command)    // Light control
void controlSteam(command)    // Steam control
void turnOffHardware()        // Safety shutdown of everything
```

**Safety Features:**
- **Automatic shutdown** on MQTT connection loss
- **hardwareOff state** - tracks if hardware is safety-disabled
- **Command validation** - checks for unknown commands

**Logic:**
- When any device is turned on, `hardwareOff = false` is set
- On connection loss, everything turns off and `hardwareOff = true` is set
- Prevents repeated shutdown operations

---

### 5. `wifi_manager.cpp` - WiFi Management

**Purpose:** Complete WiFi connection management with advanced features.

**Main Functions:**
```cpp
bool initializeWiFi()     // Initial WiFi connection
void reconnectWiFi()      // Automatic reconnection
bool isWiFiConnected()    // Connection status check
```

**Advanced Features:**
- **Exponential Backoff** - Gradually increases intervals between attempts
- **Maximum Attempts** - After 5 failed attempts, restarts ESP32
- **Automatic Detection** - Recognizes connection loss and recovery
- **Status Tracking** - Maintains global `wifiConnected` state

**Retry Logic:**
1. First attempt: immediately
2. Second attempt: after 5 seconds  
3. Third attempt: after 10 seconds
4. Fourth attempt: after 20 seconds
5. Fifth attempt: after 40 seconds
6. If all fail: ESP32 restart

**Advantages:**
- Resilience against temporary WiFi outages
- Power saving (no constant attempts)
- Automatic recovery

---

### 6. `mqtt_manager.cpp` - MQTT Management

**Purpose:** Comprehensive MQTT client with automatic connection and message processing.

**Main Components:**
- **PubSubClient Object** - Main MQTT client
- **Callback System** - Processing incoming messages
- **Status Publishing** - Regular "online" status announcements
- **Topic Management** - MQTT topic structure management

**Key Functions:**
```cpp
void initializeMqtt()        // Server setup and callback
void connectToMqtt()         // Connection with retry logic
void mqttCallback()          // Incoming message processing
void publishStatus()         // Device status publishing
void mqttLoop()              // MQTT connection maintenance
```

**Topic Structure:**
- **Commands:** `room1/motor`, `room1/light`, `room1/steam`
- **Status:** `devices/esp32_wifi_controller/status`
- **Will Message:** "offline" on unexpected disconnection

**Callback Logic:**
```
Message arrival → Topic parsing → Device identification → Command execution
```

**Retry Mechanism:**
- Similar to WiFi - exponential backoff
- Last Will Testament for disconnection indication
- Automatic topic resubscription

**Security:**
- WiFi connection check before MQTT attempts
- Automatic hardware shutdown on MQTT loss
- Keep-alive mechanism (15 seconds)

---

### 7. `connection_monitor.cpp` - Connection Monitoring

**Purpose:** Central monitoring of all connection states and diagnostics.

**What it monitors:**
- **WiFi State** - `WiFi.status() == WL_CONNECTED`
- **MQTT State** - `client.connected()`
- **State Changes** - Detection of connection loss and recovery

**Implementation:**
```cpp
void monitorConnections() {
    // Every 10 seconds check
    if (currentTime - lastConnectionCheck >= CONNECTION_CHECK_INTERVAL) {
        // Log current state
        debugPrint("Status - WiFi: OK/FAIL, MQTT: OK/FAIL");
        
        // Detect state changes
        // Update global variables
    }
}
```

**Diagnostic Information:**
- Regular status logs every 10 seconds
- Detection and logging of state changes
- Global state variable synchronization

**Advantages:**
- System state overview
- Early problem detection  
- Debug information for troubleshooting

---

## Global Variables and State

### State Variables:
```cpp
bool wifiConnected = false;        // WiFi connection state
bool mqttConnected = false;        // MQTT connection state  
bool hardwareOff = false;          // Hardware state (safety disabled)
```

### Timing Variables:
```cpp
unsigned long lastWifiAttempt = 0;      // Time of last WiFi attempt
unsigned long lastMqttAttempt = 0;      // Time of last MQTT attempt
unsigned long lastStatusPublish = 0;    // Time of last status publish
unsigned long lastConnectionCheck = 0;  // Time of last connection check
```

---

## Program Flow

### Initialization (setup):
1. **Serial Communication** (115200 baud)
2. **Watchdog Timer** (30s timeout)  
3. **Hardware Initialization** (pin setup, shutdown)
4. **WiFi Connection** (initial attempt)
5. **MQTT Configuration** (server, callback)

### Main Cycle (loop):
1. **Watchdog Reset** - prevent restart
2. **Connection Monitor** - check states every 10s
3. **WiFi Management** - reconnect if needed
4. **MQTT Management** - connect if WiFi OK
5. **MQTT Loop** - message processing and status publish
6. **Hardware Safety** - shutdown on MQTT loss
7. **Delay 50ms** - CPU saving

---

## Safety Mechanisms

### 1. Watchdog Timer
- **Timeout:** 30 seconds
- **Function:** Automatic restart on freeze
- **Reset:** In each loop cycle

### 2. Hardware Safety
- **Trigger:** MQTT connection loss
- **Action:** Shutdown all devices
- **Protection:** Against uncontrolled operation

### 3. Connection Retry Limits
- **WiFi:** Max 5 attempts → restart
- **MQTT:** Max 5 attempts → restart  
- **Prevention:** Infinite retry loops

### 4. Exponential Backoff
- **Purpose:** Resource conservation
- **Logic:** Progressively longer pauses
- **Maximum:** 60 seconds between attempts

---

## Extensibility

### Adding New Device:
1. **Configuration:** Add pin to `config.h/cpp`
2. **Hardware:** Add control function to `hardware.cpp`
3. **MQTT:** Add case to `mqttCallback` function
4. **Topic:** Extend topic structure

### Adding New Sensor:
1. **Hardware:** Read values in `hardware.cpp`
2. **MQTT:** Publishing in `mqtt_manager.cpp`
3. **Timing:** New interval in config

### Adding WiFi Portal:
1. **New Module:** `wifi_portal.h/cpp`
2. **Integration:** Call from `wifi_manager.cpp`
3. **Fallback:** On standard connection failure

The project is designed modularly, so adding new features is simple without disrupting existing code.