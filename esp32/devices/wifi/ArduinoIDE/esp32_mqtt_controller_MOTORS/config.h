#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Configuration Constants
// -----------------------------------------------------------------------------

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

// Hardware - PWM Motors Only
extern const int MOTOR1_LEFT_PIN;
extern const int MOTOR1_RIGHT_PIN;
extern const int MOTOR1_ENABLE_PIN;
extern const int MOTOR2_LEFT_PIN;
extern const int MOTOR2_RIGHT_PIN;
extern const int MOTOR2_ENABLE_PIN;

// PWM Settings
extern const int PWM_FREQUENCY;
extern const int PWM_RESOLUTION;

// Smooth Motor Control Settings
extern const int SMOOTH_STEP;
extern const int SMOOTH_DELAY;

// Connection Management
extern const unsigned long WIFI_RETRY_INTERVAL;
extern const unsigned long MQTT_RETRY_INTERVAL;
extern const unsigned long MAX_RETRY_INTERVAL;
extern const unsigned long STATUS_PUBLISH_INTERVAL;
extern const unsigned long CONNECTION_CHECK_INTERVAL;
extern const int MAX_WIFI_ATTEMPTS;
extern const int MAX_MQTT_ATTEMPTS;
extern const int MQTT_KEEP_ALIVE;

// Watchdog Timer Configuration
extern const unsigned long WDT_TIMEOUT;

extern const char* OTA_HOSTNAME;
extern const char* OTA_PASSWORD;
extern const bool OTA_ENABLED;

#endif