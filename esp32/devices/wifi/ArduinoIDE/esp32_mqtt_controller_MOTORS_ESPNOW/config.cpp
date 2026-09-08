#include "config.h"

const museum::RadioPeer ESPNOW_MASTER_PEER[1] = {
  {ESPNOW_MASTER_MAC, ESPNOW_MASTER_NODE, ESPNOW_ENCRYPTION_ENABLED, ESPNOW_LMK_BYTES}
};
const uint8_t ESPNOW_PMK[16] = ESPNOW_PMK_BYTES;
const museum::Timing ESPNOW_TIMING = {};

// Diagnostic output.
const bool DEBUG = true;

// PWM telemetry.
const bool PWM_TELEMETRY = false;
const unsigned long PWM_TELEMETRY_INTERVAL = 100;

// WiFi configuration.
const char* WIFI_SSID = "kastielhome";
const char* WIFI_PASSWORD = "Kastiel18";

// MQTT broker and topic configuration.
const char* MQTT_SERVER = "TechMuzeumRoom1.local";
const int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "Room1_ESP_Motory";

// PWM motor driver pins.
const int MOTOR1_LEFT_PIN = 18;
const int MOTOR1_RIGHT_PIN = 19;
const int MOTOR1_ENABLE_PIN = 21;
const int MOTOR2_LEFT_PIN = 27;
const int MOTOR2_RIGHT_PIN = 26;
const int MOTOR2_ENABLE_PIN = 25;



// PWM output settings.
const int PWM_FREQUENCY = 20000;
const int PWM_RESOLUTION = 8;

// Smooth motor control settings.
const int SMOOTH_STEP = 2;
const int SMOOTH_DELAY = 100;

// Connection management settings.
const unsigned long WIFI_RETRY_INTERVAL = 3000;
const unsigned long MQTT_RETRY_INTERVAL = 2000;
const unsigned long MAX_RETRY_INTERVAL = 30000;
const unsigned long STATUS_PUBLISH_INTERVAL = 5000;
const unsigned long CONNECTION_CHECK_INTERVAL = 5000;
const int MAX_WIFI_ATTEMPTS = 10;
const int MAX_MQTT_ATTEMPTS = 10;
const int MQTT_KEEP_ALIVE = 5;
const unsigned long NO_COMMAND_TIMEOUT = 180000;

// Watchdog timer configuration.
const unsigned long WDT_TIMEOUT = 60;

// OTA configuration.
const char* OTA_HOSTNAME = "ESP32-Museum-Room1";
const char* OTA_PASSWORD = "room1";
const bool OTA_ENABLED = true;
