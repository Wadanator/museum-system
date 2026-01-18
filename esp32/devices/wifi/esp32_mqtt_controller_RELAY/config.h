#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// =============================================================================
// KONFIGURACIA HARDVERU
// =============================================================================
extern const bool USE_RELAY_MODULE;
extern const int I2C_SDA_PIN;
extern const int I2C_SCL_PIN;
extern const int I2C_EXPANDER_ADDR;

// =============================================================================
// DEFINICIA ZARIADENI
// =============================================================================
struct Device {
  const char* name;       // Nazov pre MQTT topic
  int pin;                // GPIO pin alebo bit expandera
  bool inverted;          // true = rele je aktivne na LOW
  unsigned long autoOffMs; // NOVÉ: Cas v ms pre automaticke vypnutie (0 = vypnute)
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

// OTA Configuration
extern const char* OTA_HOSTNAME;
extern const char* OTA_PASSWORD;
extern const bool OTA_ENABLED;

#endif