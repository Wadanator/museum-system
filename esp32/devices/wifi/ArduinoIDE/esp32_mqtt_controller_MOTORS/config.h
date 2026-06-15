#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Diagnostic output.
extern const bool DEBUG;

// PWM telemetry for Serial Plotter.
extern const bool PWM_TELEMETRY;
extern const unsigned long PWM_TELEMETRY_INTERVAL;

// WiFi configuration.
extern const char* WIFI_SSID;
extern const char* WIFI_PASSWORD;

// MQTT broker and topic configuration.
extern const char* MQTT_SERVER;
extern const int MQTT_PORT;
extern const char* BASE_TOPIC_PREFIX;
extern const char* CLIENT_ID;

// PWM motor driver pins.
extern const int MOTOR1_LEFT_PIN;
extern const int MOTOR1_RIGHT_PIN;
extern const int MOTOR1_ENABLE_PIN;
extern const int MOTOR2_LEFT_PIN;
extern const int MOTOR2_RIGHT_PIN;
extern const int MOTOR2_ENABLE_PIN;

// PWM output settings.
extern const int PWM_FREQUENCY;
extern const int PWM_RESOLUTION;

// Smooth motor control settings.
extern const int SMOOTH_STEP;
extern const int SMOOTH_DELAY;

// Connection management.
extern const unsigned long WIFI_RETRY_INTERVAL;
extern const unsigned long MQTT_RETRY_INTERVAL;
extern const unsigned long MAX_RETRY_INTERVAL;
extern const unsigned long STATUS_PUBLISH_INTERVAL;
extern const unsigned long CONNECTION_CHECK_INTERVAL;
extern const int MAX_WIFI_ATTEMPTS;
extern const int MAX_MQTT_ATTEMPTS;
extern const int MQTT_KEEP_ALIVE;
extern const unsigned long NO_COMMAND_TIMEOUT;

// Watchdog timer configuration.
extern const unsigned long WDT_TIMEOUT;

// OTA configuration.
extern const char* OTA_HOSTNAME;
extern const char* OTA_PASSWORD;
extern const bool OTA_ENABLED;

#endif
