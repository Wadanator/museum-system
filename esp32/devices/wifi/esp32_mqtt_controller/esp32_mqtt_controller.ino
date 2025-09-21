#include <esp_task_wdt.h>
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "connection_monitor.h"
#include "ota_manager.h"  // Jednoduchý OTA

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 MQTT Controller Starting...");
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

  // ⭐ INITIALIZE OTA - JEDNODUCHO!
  if (wifiConnected) {
    initializeOTA();  // Automaticky sa aktivuje!
  }

  // Initialize MQTT
  initializeMqtt();

  Serial.println("Ready - Listening on: room1/#");
  debugPrint("=== Setup completed ===");
}

void loop() {
  esp_task_wdt_reset(); // Reset Watchdog Timer
  
  // ⭐ HANDLE OTA - JEDNODUCHO!
  if (wifiConnected) {
    handleOTA();  // Neustále aktívny
    
    // Ak prebieha OTA, zredukuj ostatné operácie
    if (otaInProgress) {
      delay(100);
      return;
    }
  }

  // Štandardné operácie
  monitorConnections();

  // Handle WiFi connection
  if (!isWiFiConnected()) {
    reconnectWiFi();
    
    // Po obnovení WiFi, aktivuj OTA znovu
    if (wifiConnected) {
      initializeOTA();
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

  delay(50);
}