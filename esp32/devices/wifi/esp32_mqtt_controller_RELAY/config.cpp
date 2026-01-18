#include "config.h"

// =============================================================================
// IMPLEMENTACIA KONSTANT
// =============================================================================

const bool USE_RELAY_MODULE = true;

// I2C Konfiguracia
const int I2C_SDA_PIN = 42;
const int I2C_SCL_PIN = 41;
const int I2C_EXPANDER_ADDR = 0x20; 

// =============================================================================
// DEFINICIA ZARIADENI
// =============================================================================

const Device DEVICES[] = {
  // Nazov topicu          Pin/Bit   Inverted  AutoOff(ms)
  {"effect/smoke",         0,        false,    5000},  // <--- LIMIT 5 SEKÚND PRE DYM
  {"light/1",              1,        false,    0},     // 0 = bez limitu (trvale zapnutie)
  {"light/2",              2,        false,    0},
  {"light/3",              3,        false,    0},
  {"light/4",              4,        false,    0},
  {"light/5",              5,        false,    0},
  {"light/6",              6,        false} 
  // Rele 8 (bit 7) ostava volne
};

const int DEVICE_COUNT = sizeof(DEVICES) / sizeof(Device);

// =============================================================================
// OSTATNA KONFIGURACIA
// =============================================================================

// Debug
const bool DEBUG = true;

// WiFi
//const char* WIFI_SSID = "Museum-Room1";
//const char* WIFI_PASSWORD = "88888888";

const char* WIFI_SSID = "Majo-home";
const char* WIFI_PASSWORD = "Mmajcher7680home";

// MQTT
const char* MQTT_SERVER = "TechMuzeumRoom1.local";
const int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "esp32_relay_controller";

// Connection Management
const unsigned long WIFI_RETRY_INTERVAL = 3000;
const unsigned long MQTT_RETRY_INTERVAL = 2000;
const unsigned long MAX_RETRY_INTERVAL = 30000;
const unsigned long STATUS_PUBLISH_INTERVAL = 15000;
const unsigned long CONNECTION_CHECK_INTERVAL = 5000;
const int MAX_WIFI_ATTEMPTS = 3;
const int MAX_MQTT_ATTEMPTS = 3;
const int MQTT_KEEP_ALIVE = 10;

// 10 minut timeout pre necinnost
const unsigned long NO_COMMAND_TIMEOUT = 600000;

// Watchdog Timer
const unsigned long WDT_TIMEOUT = 60;

// OTA Configuration
const char* OTA_HOSTNAME = "ESP32-Room1-Relay"; // Zmen si nazov ak chces
const char* OTA_PASSWORD = "room1"; // Zmen si heslo
const bool OTA_ENABLED = true;