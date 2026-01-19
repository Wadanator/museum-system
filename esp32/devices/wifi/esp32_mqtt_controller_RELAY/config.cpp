#include "config.h"

// =============================================================================
// IMPLEMENTACIA KONSTANT
// =============================================================================

// FIX: Odstránené 'const', aby boli premenné viditeľné pre celý program (rieši LED)
bool USE_RELAY_MODULE = true;

// I2C Konfiguracia
// FIX: Odstránené 'const'
int I2C_SDA_PIN = 42;
int I2C_SCL_PIN = 41;
int I2C_EXPANDER_ADDR = 0x20; 

// Konfiguracia RGB LED (Waveshare používa GPIO 38)
// FIX: Odstránené 'const' - toto opraví modrú LED
int RGB_LED_PIN = 38;

// =============================================================================
// DEFINICIA ZARIADENI
// =============================================================================

const Device DEVICES[] = {
  // Nazov topicu          Pin/Bit   Inverted  AutoOff(ms)
  {"effect/smoke",         3,        false,    12000},  // Limit 12s pre dym
  {"light/1",              0,        false,    0},     
  {"light/2",              1,        false,    0},
  {"light/3",              2,        false,    0},
  {"light/4",              4,        false,    0},
  {"light/5",              5,        false,    0},
  {"light/6",              6,        false,    0},
  {"light/7",              7,        false,    0}
};

const int DEVICE_COUNT = sizeof(DEVICES) / sizeof(Device);

// =============================================================================
// OSTATNA KONFIGURACIA
// =============================================================================

// Debug
bool DEBUG = true;

// WiFi Nastavenia

// 1. Domáca WiFi (Majo)
//const char* WIFI_SSID = "Majo-home";
//const char* WIFI_PASSWORD = "Mmajcher7680home";

// 2. Múzeum WiFi (Room1)
const char* WIFI_SSID = "Museum-Room1";
const char* WIFI_PASSWORD = "88888888";


// MQTT
const char* MQTT_SERVER = "TechMuzeumRoom1.local";
int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "Room1_Relays_Ctrl";

// Connection Management
unsigned long WIFI_RETRY_INTERVAL = 3000;
unsigned long MQTT_RETRY_INTERVAL = 2000;
unsigned long MAX_RETRY_INTERVAL = 30000;
unsigned long STATUS_PUBLISH_INTERVAL = 15000;
unsigned long CONNECTION_CHECK_INTERVAL = 5000;
int MAX_WIFI_ATTEMPTS = 10;
int MAX_MQTT_ATTEMPTS = 10;
int MQTT_KEEP_ALIVE = 10;

// Timeout pre necinnost
unsigned long NO_COMMAND_TIMEOUT = 180000;

// Watchdog Timer
unsigned long WDT_TIMEOUT = 30;

// OTA Konfiguracia
const char* OTA_HOSTNAME = "ESP32-RelayModule-Room1";
const char* OTA_PASSWORD = "room1";
bool OTA_ENABLED = true;