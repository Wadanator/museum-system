#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// =============================================================================
// KONFIGURACIA HARDVERU
// =============================================================================
// Ak je true, pouzije sa ovladanie cez I2C expander (pre Waveshare modul)
// Ak je false, pouzije sa priame ovladanie GPIO (pre klasicke ESP32)
extern const bool USE_RELAY_MODULE;

// I2C Nastavenia pre Waveshare modul
extern const int I2C_SDA_PIN;
extern const int I2C_SCL_PIN;
extern const int I2C_EXPANDER_ADDR;

// =============================================================================
// DEFINICIA ZARIADENI
// =============================================================================
struct Device {
  const char* name;  // Nazov pre MQTT topic (napr. "light1", "fan")
  int pin;           // GPIO pin (ak USE_RELAY_MODULE=false) ALEBO cislo bitu 0-7 (ak USE_RELAY_MODULE=true)
  bool inverted;     // true = rele je aktivne na LOW (bezne pre releove moduly)
};

// Zariadenia
extern const Device DEVICES[];
extern const int DEVICE_COUNT;

// =============================================================================
// SYSTEMOVA KONFIGURACIA
// =============================================================================

// Debug
extern const bool DEBUG;

// WiFi
extern const char* WIFI_SSID;
extern const char* WIFI_PASSWORD;

// MQTT
extern const char* MQTT_SERVER;
extern const int MQTT_PORT;
extern const char* BASE_TOPIC_PREFIX;
extern const char* CLIENT_ID;

// Connection Management
extern const unsigned long WIFI_RETRY_INTERVAL;
extern const unsigned long MQTT_RETRY_INTERVAL;
extern const unsigned long MAX_RETRY_INTERVAL;
extern const unsigned long STATUS_PUBLISH_INTERVAL;
extern const unsigned long CONNECTION_CHECK_INTERVAL;
extern const int MAX_WIFI_ATTEMPTS;
extern const int MAX_MQTT_ATTEMPTS;
extern const int MQTT_KEEP_ALIVE;

// Cas v ms, po ktorom sa vsetko vypne, ak nepride ziadny prikaz
extern const unsigned long NO_COMMAND_TIMEOUT;

// Watchdog Timer
extern const unsigned long WDT_TIMEOUT;

#endif