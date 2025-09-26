// esp32_mqtt_controller.ino - FIXED VERSION for reliable OTA
#include <esp_task_wdt.h>
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "connection_monitor.h"
#include "ota_manager.h"

void setup() {
  Serial.begin(115200);
  delay(100);  // Give serial time to initialize
  
  Serial.println("\n=== ESP32 MQTT Controller Starting ===");
  debugPrint("=== ESP32 MQTT Controller Starting ===");

  // Initialize Watchdog Timer
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000,
    .idle_core_mask = 0,
    .trigger_panic = true
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
  debugPrint("Watchdog Timer initialized");

  // Initialize hardware
  initializeHardware();

  // Initialize WiFi
  if (!initializeWiFi()) {
    Serial.println("WiFi failed, will retry...");
    debugPrint("Initial WiFi failed");
  }

  //Initialize OTA ONLY after WiFi is connected
  if (wifiConnected) {
    initializeOTA();
  }

  // Initialize MQTT
  initializeMqtt();

  Serial.println("=== Setup Complete ===");
  Serial.println("Ready - Listening on: " + String(BASE_TOPIC_PREFIX) + "#");
  debugPrint("=== Setup completed ===");
}

void loop() {
  //CRITICAL: Handle OTA first and exit early if upload in progress
  if (wifiConnected) {
    handleOTA();
    
    //If OTA upload is happening, do NOTHING else
    if (isOTAInProgress()) {
      // During OTA: minimal delay, no watchdog reset, no other operations
      delay(10);
      return;  // EXIT IMMEDIATELY - let OTA have full control
    }
  }

  //Only reset watchdog if NOT in OTA mode
  if (!isOTAInProgress()) {
    esp_task_wdt_reset(); // Reset Watchdog Timer
  }

  // Standard operations (only when OTA not in progress)
  monitorConnections();

  // Handle WiFi connection
  if (!isWiFiConnected()) {
    reconnectWiFi();
    
    // Re-initialize OTA after WiFi reconnect
    if (wifiConnected) {
      reinitializeOTAAfterWiFiReconnect();
    }
  }

  // Handle MQTT connection
  if (wifiConnected && !isMqttConnected()) {
    connectToMqtt();
  }

  // Handle MQTT loop and status publishing
  if (isMqttConnected()) {
    mqttLoop();
  } else if (!hardwareOff) {
    turnOffHardware();
  }

  //Reduced delay when OTA might be starting
  delay(50);
}