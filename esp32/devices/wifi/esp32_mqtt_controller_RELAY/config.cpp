#include "config.h"

// =============================================================================
// IMPLEMENTACIA KONSTANT
// =============================================================================

// !!! HLAVNY PREPINAC REZIMU !!!
// true  = Pre Waveshare Industrial 8-Channel Relay Module (ovladanie cez I2C)
// false = Pre bezne ESP32 (priame ovladanie GPIO pinov)
const bool USE_RELAY_MODULE = true;

// I2C Konfiguracia pre Waveshare ESP32-S3-ETH-8DI-8RO
const int I2C_SDA_PIN = 42;
const int I2C_SCL_PIN = 41;
const int I2C_EXPANDER_ADDR = 0x20; // Standardna adresa TCA9554

// =============================================================================
// DEFINICIA ZARIADENI
// =============================================================================
// POZOR: Ak je USE_RELAY_MODULE = true, 'pin' znamena cislo bitu expandera (0-7)

const Device DEVICES[] = {
  // Nazov topicu          Pin/Bit   Inverted
  {"effect/smoke",         0,        false},   // Rele 1
  {"light/1",              1,        false},   // Rele 2
  {"light/2",              2,        false},   // Rele 3
  {"light/3",              3,        false},   // Rele 4
  {"light/4",              4,        false},   // Rele 5
  {"light/5",              5,        false},   // Rele 6
  {"light/6",              6,        false}    // Rele 7
  // Rele 8 (bit 7) ostava volne
};

const int DEVICE_COUNT = sizeof(DEVICES) / sizeof(Device);

// =============================================================================
// OSTATNA KONFIGURACIA
// =============================================================================

// Debug
const bool DEBUG = true;

// WiFi
const char* WIFI_SSID = "Museum-Room1";
const char* WIFI_PASSWORD = "88888888";

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

// 10 minut * 60 sekund * 1000 milisekund = 600000
const unsigned long NO_COMMAND_TIMEOUT = 600000;

// Watchdog Timer
const unsigned long WDT_TIMEOUT = 60;