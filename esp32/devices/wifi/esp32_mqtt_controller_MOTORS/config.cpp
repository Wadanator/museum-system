#include "config.h"

// Configuration Constants Implementation
// -----------------------------------------------------------------------------

// Debug
const bool DEBUG = true;

// WiFi
const char* WIFI_SSID = "Museum-Room1";
const char* WIFI_PASSWORD = "88888888";

// MQTT
const char* MQTT_SERVER = "TechMuzeumRoom1.local";
const int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "esp32_wifi_controller";

// Hardware - PWM Motors Only
const int MOTOR1_LEFT_PIN = 27;
const int MOTOR1_RIGHT_PIN = 26;
const int MOTOR1_ENABLE_PIN = 25;
const int MOTOR2_LEFT_PIN = 33;
const int MOTOR2_RIGHT_PIN = 32;
const int MOTOR2_ENABLE_PIN = 14;

// PWM Settings
const int PWM_FREQUENCY = 20000;
const int PWM_RESOLUTION = 8;

// Smooth Motor Control Settings
const int SMOOTH_STEP = 8;
const int SMOOTH_DELAY = 15;

// Connection Management
const unsigned long WIFI_RETRY_INTERVAL = 3000;
const unsigned long MQTT_RETRY_INTERVAL = 2000;
const unsigned long MAX_RETRY_INTERVAL = 30000;
const unsigned long STATUS_PUBLISH_INTERVAL = 15000;
const unsigned long CONNECTION_CHECK_INTERVAL = 5000;
const int MAX_WIFI_ATTEMPTS = 3;
const int MAX_MQTT_ATTEMPTS = 3;
const int MQTT_KEEP_ALIVE = 10;

// Watchdog Timer Configuration
const unsigned long WDT_TIMEOUT = 60;

// OTA Configuration
const char* OTA_HOSTNAME = "ESP32-Museum-Room1";
const char* OTA_PASSWORD = "room1";
const bool OTA_ENABLED = true;