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
  delay(100);

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

  // Initialize hardware and Wi-Fi
  initializeHardware();
  if (!initializeWiFi()) {
    Serial.println("WiFi failed, will retry...");
    debugPrint("Initial WiFi failed");
  }

  // Initialize OTA ONLY after WiFi is connected
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
  // Handle OTA first
  if (wifiConnected) {
    handleOTA();
    // If OTA upload is happening, do nothing else
    if (isOTAInProgress()) {
      delay(10);
      return;
    }
  }

  // MQTT loop must be first for fast feedback
  if (isMqttConnected()) {
    client.loop();
  }

  // Smooth motor update
  updateMotorSmoothly();

  // Watchdog reset (only if not doing an OTA update)
  if (!isOTAInProgress()) {
    esp_task_wdt_reset();
  }

  static unsigned long lastQuickCheck = 0;
  unsigned long currentTime = millis();

  // Handle Wi-Fi and MQTT reconnections more frequently
  if (currentTime - lastQuickCheck >= 100) {
    lastQuickCheck = currentTime;
    if (!isWiFiConnected()) {
      reconnectWiFi();
      // Re-initialize OTA after Wi-Fi reconnect
      if (wifiConnected) {
        reinitializeOTAAfterWiFiReconnect();
      }
    }

    if (wifiConnected && !isMqttConnected()) {
      connectToMqtt();
    }
  }

  // Detailed connection monitoring (less frequent)
  static unsigned long lastDetailedCheck = 0;
  if (currentTime - lastDetailedCheck >= 10000) {
    lastDetailedCheck = currentTime;
    monitorConnections();
  }

  // Hardware safety check
  if (!isMqttConnected() && !hardwareOff) {
    turnOffHardware();
  }

  delay(10);
}