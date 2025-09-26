#include "config.h"

// Configuration Constants Implementation
// -----------------------------------------------------------------------------

// Debug
const bool DEBUG = true;

// WiFi
const char* WIFI_SSID = "Museum-Room1";
const char* WIFI_PASSWORD = "88888888";

// MQTT
const char* MQTT_SERVER = "192.168.0.127";
const int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "esp32_wifi_controller";

// Hardware - PWM Motors Only
const int MOTOR1_LEFT_PIN = 27;    // Motor 1 left direction
const int MOTOR1_RIGHT_PIN = 26;   // Motor 1 right direction
const int MOTOR1_ENABLE_PIN = 25;  // Motor 1 enable
const int MOTOR2_LEFT_PIN = 33;    // Motor 2 left direction
const int MOTOR2_RIGHT_PIN = 32;   // Motor 2 right direction
const int MOTOR2_ENABLE_PIN = 14;  // Motor 2 enable

// PWM Settings
const int PWM_FREQUENCY = 20000;   // 20kHz
const int PWM_RESOLUTION = 8;      // 8-bit (0-255)

// Smooth Motor Control Settings
const int SMOOTH_STEP = 5;         // PWM step per update (1-10, higher = faster)
const int SMOOTH_DELAY = 20;       // Delay between steps in ms (10-50, lower = smoother)

// Connection Management
const unsigned long WIFI_RETRY_INTERVAL = 5000;
const unsigned long MQTT_RETRY_INTERVAL = 5000;
const unsigned long MAX_RETRY_INTERVAL = 60000;
const unsigned long STATUS_PUBLISH_INTERVAL = 30000;
const unsigned long CONNECTION_CHECK_INTERVAL = 10000;
const int MAX_WIFI_ATTEMPTS = 5;
const int MAX_MQTT_ATTEMPTS = 5;
const int MQTT_KEEP_ALIVE = 15;

// Watchdog Timer Configuration
const unsigned long WDT_TIMEOUT = 120;

const char* OTA_HOSTNAME = "ESP32-Museum-Room1";
const char* OTA_PASSWORD = "room1";
const bool OTA_ENABLED = true;