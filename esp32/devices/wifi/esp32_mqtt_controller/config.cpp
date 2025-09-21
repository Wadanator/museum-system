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

// Hardware
const int MOTOR_PIN = 4;
const int LIGHT_PIN = 5;
const int STEAM_PIN = 14;

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

const char* OTA_HOSTNAME = "ESP32-Museum-Room1";  // Meno pre Arduino IDE
const char* OTA_PASSWORD = "room1";               // Žiadne heslo pre jednoduchost
const bool OTA_ENABLED = true;                    // Povoliť OTA