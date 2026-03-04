#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

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
extern const char* SCENE_TOPIC_SUFFIX;
extern const char* SCENE_PAYLOAD;

// Hardware - Button
extern const int BUTTON_PIN;           
extern const unsigned long DEBOUNCE_DELAY;
extern const unsigned long BUTTON_COOLDOWN; // NOVÉ: Čas medzi stlačeniami

// Connection Management
extern const unsigned long WIFI_RETRY_INTERVAL;
extern const unsigned long MQTT_RETRY_INTERVAL;
extern const unsigned long MAX_RETRY_INTERVAL;
extern const unsigned long STATUS_PUBLISH_INTERVAL;
extern const unsigned long CONNECTION_CHECK_INTERVAL;
extern const int MAX_WIFI_ATTEMPTS;
extern const int MAX_MQTT_ATTEMPTS;
extern const int MQTT_KEEP_ALIVE;

// Watchdog & OTA
extern const unsigned long WDT_TIMEOUT;
extern const char* OTA_HOSTNAME;
extern const char* OTA_PASSWORD;
extern const bool OTA_ENABLED;

#endif