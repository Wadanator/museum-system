#include <esp_task_wdt.h>
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "connection_monitor.h"
#include "ota_manager.h"
#include "status_led.h"
#include "effects_manager.h"

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n------------------------------------------");
  Serial.println(" ESP32 LAN+WiFi MQTT Relay Controller v2.4 + Effects");
  Serial.println("------------------------------------------");
  debugPrint("=== System startup ===");
  
  // The watchdog is active before hardware and network initialization.
  esp_task_wdt_deinit();
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000,
    .idle_core_mask = 0,
    .trigger_panic = true
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
  debugPrint("Watchdog timer initialized (" + String(WDT_TIMEOUT) + "s)");
  
  Serial.println("\n--- Hardware initialization ---");
  initializeHardware();
  
  // Status indication is available during network and MQTT startup.
  initializeStatusLed();

  initializeEffects();
  
  Serial.println("\n--- Network connection (LAN primary, WiFi fallback) ---");
  if (!initializeWiFi()) {
    Serial.println("Network is not connected yet; retrying in the main loop...");
  }

  // OTA is enabled only after a network transport is available.
  if (wifiConnected) {
    initializeOTA();
  }

  Serial.println("\n--- MQTT configuration ---");
  initializeMqtt();
  lastCommandTime = millis();
  
  Serial.println("\n------------------------------------------");
  Serial.println(" Setup complete");
  Serial.println("------------------------------------------");
}

void loop() {
  // OTA handling runs before normal work so updates stay responsive.
  if (wifiConnected) {
    handleOTA();
    if (isOTAInProgress()) {
      delay(10);
      return;
    }
  }

  handleStatusLed(isWiFiConnected(), isMqttConnected());

  esp_task_wdt_reset();

  if (isMqttConnected()) {
    mqttLoop();
  }

  handleEffects();

  handleAutoOff();

  // Network and MQTT reconnects are checked frequently for fast recovery.
  static unsigned long lastQuickCheck = 0;
  unsigned long currentTime = millis();

  if (currentTime - lastQuickCheck >= 100) {
    lastQuickCheck = currentTime;
    static bool previousNetworkConnected = false;
    reconnectWiFi();

    if (wifiConnected && !previousNetworkConnected) {
      reinitializeOTAAfterWiFiReconnect();
    }
    previousNetworkConnected = wifiConnected;

    if (wifiConnected && !isMqttConnected()) {
      connectToMqtt();
    }
  }

  // Connection diagnostics are rate-limited to keep serial output readable.
  static unsigned long lastDetailedCheck = 0;
  if (currentTime - lastDetailedCheck >= 10000) {
    lastDetailedCheck = currentTime;
    monitorConnections();
  }

  // Safety protection de-energizes outputs when MQTT is unavailable.
  static unsigned long mqttDisconnectedSince = 0;
  if (!isMqttConnected()) {
    if (mqttDisconnectedSince == 0) {
      mqttDisconnectedSince = currentTime;
    }

    if (!allDevicesOff && (currentTime - mqttDisconnectedSince > NETWORK_FAILOVER_GRACE)) {
      debugPrint("MQTT connection lost after failover grace -> turning devices off");
      turnOffAllDevices();
      stopAllEffects();
    }
  } else {
    mqttDisconnectedSince = 0;
  }
  
  if (!allDevicesOff && (currentTime - lastCommandTime > NO_COMMAND_TIMEOUT)) {
     debugPrint("TIMEOUT: turning devices off due to inactivity");
     turnOffAllDevices();
     stopAllEffects();
     lastCommandTime = currentTime;
  }

  delay(1);
}
