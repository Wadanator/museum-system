#include "config.h"

// Debug Mode
const bool DEBUG = true;

// WiFi Configuration
const char* WIFI_SSID = "Museum-Room1"; // Upravte podľa potreby
const char* WIFI_PASSWORD = "88888888"; // Upravte podľa potreby

// MQTT Configuration
const char* MQTT_SERVER = "TechMuzeumRoom1.local";
const int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "Room1_ESP_Trigger";

// Scene Configuration
const char* SCENE_TOPIC_SUFFIX = "scene";
const char* SCENE_PAYLOAD = "START";

// Hardware - Button Input
const int BUTTON_PIN = 32;
const unsigned long DEBOUNCE_DELAY = 60;    
const unsigned long BUTTON_COOLDOWN = 4000; // 4 sekundy pauza medzi odoslaním

// Connection Management Settings
const unsigned long WIFI_RETRY_INTERVAL = 3000;
const unsigned long MQTT_RETRY_INTERVAL = 2000;
const unsigned long MAX_RETRY_INTERVAL = 30000;
const unsigned long STATUS_PUBLISH_INTERVAL = 15000;
const unsigned long CONNECTION_CHECK_INTERVAL = 5000;
const int MAX_WIFI_ATTEMPTS = 5;
const int MAX_MQTT_ATTEMPTS = 5;
const int MQTT_KEEP_ALIVE = 15;

// Watchdog & OTA
const unsigned long WDT_TIMEOUT = 30; // 30s reset ak kód úplne zamrzne
const char* OTA_HOSTNAME = "ESP32-Room1-Trigger";
const char* OTA_PASSWORD = "room1";
const bool OTA_ENABLED = true;