#include <esp_task_wdt.h>
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "connection_monitor.h"

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 MQTT Controller Starting...");
  debugPrint("=== ESP32 MQTT Controller Starting ===");

  // Initialize Watchdog Timer
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000, // Convert seconds to milliseconds
    .idle_core_mask = 0,              // Watchdog monitors all cores
    .trigger_panic = true             // Trigger panic on timeout
  };
  esp_task_wdt_init(&wdt_config);     // Initialize Watchdog with config
  esp_task_wdt_add(NULL);             // Add current task to Watchdog
  debugPrint("Watchdog Timer initialized with " + String(WDT_TIMEOUT) + "s timeout");

  // Initialize hardware
  initializeHardware();

  // Initialize WiFi
  if (!initializeWiFi()) {
    Serial.println("WiFi failed, will retry...");
    debugPrint("Initial WiFi failed");
  }

  // Initialize MQTT
  initializeMqtt();

  Serial.println("Ready - Listening on: room1/#");
  debugPrint("=== Setup completed ===");
}

void loop() {
  esp_task_wdt_reset(); // Reset Watchdog Timer
  monitorConnections();

  // Handle WiFi connection
  if (!isWiFiConnected()) {
    reconnectWiFi();
  }

  // Handle MQTT connection
  if (wifiConnected && !isMqttConnected()) {
    connectToMqtt();
  }

  // Handle MQTT loop and status publishing
  if (isMqttConnected()) {
    mqttLoop();
  } else if (!hardwareOff) { // Only turn off hardware if not already off
    turnOffHardware();
  }

  delay(50);
}