// esp32_mqtt_controller.ino - OPTIMALIZOVANÁ VERZIA pre rýchly feedback
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
  // KRITICKÉ: Handle OTA first
  if (wifiConnected) {
    handleOTA();
    
    // If OTA upload is happening, do NOTHING else
    if (isOTAInProgress()) {
      delay(10);
      return;
    }
  }

  // PRIORITA 1: MQTT loop - MUSÍ byť prvé pre rýchly feedback
  if (isMqttConnected()) {
    client.loop(); // Spracuj prijaté správy a odoši feedback OKAMŽITE
  }

  // PRIORITA 2: Smooth motor update - rýchle, bez delay
  updateMotorSmoothly();

  // PRIORITA 3: Watchdog reset (iba ak nie je OTA)
  if (!isOTAInProgress()) {
    esp_task_wdt_reset();
  }

  // PRIORITA 4: Connection monitoring (menej často)
  static unsigned long lastQuickCheck = 0;
  unsigned long currentTime = millis();
  
  // Rýchla kontrola každých 100ms namiesto connection monitor
  if (currentTime - lastQuickCheck >= 100) {
    lastQuickCheck = currentTime;
    
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
  }

  // PRIORITA 5: Detailné monitorovanie (menej často)
  static unsigned long lastDetailedCheck = 0;
  if (currentTime - lastDetailedCheck >= 10000) { // Každých 5 sekúnd
    lastDetailedCheck = currentTime;
    monitorConnections();
  }

  // PRIORITA 6: Hardware safety check
  if (!isMqttConnected() && !hardwareOff) {
    turnOffHardware();
  }

  delay(10); // Znížené z 50ms na 10ms pre rýchlejší feedback
}