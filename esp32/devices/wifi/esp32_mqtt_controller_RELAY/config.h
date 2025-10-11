#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// =============================================================================
// DEFINÍCIA ZARIADENÍ - UPRAVIŤ PODĽA POTREBY
// =============================================================================
struct Device {
  const char* name;  // Názov pre MQTT topic (napr. "light1", "fan", "pump")
  int pin;           // GPIO pin
  bool inverted;     // true = relé je aktívne na LOW (bežné pre reléové moduly)
};

// Tu pridávaj/upravuj svoje zariadenia
const Device DEVICES[] = {
  {"light1", 27, true},   // room1/light1 -> GPIO 27, aktívne LOW
  {"light2", 26, true},   // room1/light2 -> GPIO 26, aktívne LOW
  {"fan", 25, true},      // room1/fan -> GPIO 25, aktívne LOW
  {"pump", 33, true}      // room1/pump -> GPIO 33, aktívne LOW
};

const int DEVICE_COUNT = sizeof(DEVICES) / sizeof(Device);

// =============================================================================
// SYSTÉMOVÁ KONFIGURÁCIA
// =============================================================================

// Debug
extern const bool DEBUG;

// WiFi
extern const char* WIFI_SSID;
extern const char* WIFI_PASSWORD;

// MQTT
extern const char* MQTT_SERVER;
extern const int MQTT_PORT;
extern const char* BASE_TOPIC_PREFIX;  // "room1/"
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

// Watchdog Timer
extern const unsigned long WDT_TIMEOUT;

#endif