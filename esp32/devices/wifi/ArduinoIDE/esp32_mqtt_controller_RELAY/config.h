#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// =============================================================================
// KONFIGURACIA HARDVERU
// =============================================================================
extern bool USE_RELAY_MODULE;

extern int I2C_SDA_PIN;
extern int I2C_SCL_PIN;
extern int I2C_EXPANDER_ADDR;

extern int RGB_LED_PIN;

// =============================================================================
// DEFINICIA ZARIADENI
// =============================================================================
struct Device {
  const char* name;
  int pin;
  bool inverted;
  unsigned long autoOffMs;
};

extern const Device DEVICES[];
extern const int DEVICE_COUNT;

// =============================================================================
// SYSTEMOVA KONFIGURACIA
// =============================================================================

// Debug
extern bool DEBUG;

// WiFi
extern const char* WIFI_SSID;
extern const char* WIFI_PASSWORD;

// MQTT
extern const char* MQTT_SERVER;
extern int MQTT_PORT;
extern const char* BASE_TOPIC_PREFIX;
extern const char* CLIENT_ID;

// Connection Management
extern unsigned long WIFI_RETRY_INTERVAL;
extern unsigned long MQTT_RETRY_INTERVAL;
extern unsigned long MAX_RETRY_INTERVAL;
extern unsigned long STATUS_PUBLISH_INTERVAL;
extern unsigned long CONNECTION_CHECK_INTERVAL;
extern int MAX_WIFI_ATTEMPTS;
extern int MAX_MQTT_ATTEMPTS;
extern int MQTT_KEEP_ALIVE;

// Timeout
extern unsigned long NO_COMMAND_TIMEOUT;

// Watchdog
extern unsigned long WDT_TIMEOUT;

// OTA
extern const char* OTA_HOSTNAME;
extern const char* OTA_PASSWORD;
extern bool OTA_ENABLED;

#endif