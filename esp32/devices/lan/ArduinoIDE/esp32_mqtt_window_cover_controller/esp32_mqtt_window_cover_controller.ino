#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "connection_monitor.h"
#include "ota_manager.h"
#include "status_led.h"
#include "wdt_manager.h"

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n------------------------------------------------");
  Serial.println(" ESP32 LAN+WiFi MQTT Window Cover Controller");
  Serial.println(" 2 DC motors + 4 PWM channels + end-stop safety");
  Serial.println("------------------------------------------------");
  debugPrint("=== System startup ===");

  initializeWatchdog();

  Serial.println("\n--- Hardware initialization ---");
  initializeHardware();
  initializeStatusLed();

  Serial.println("\n--- Network connection (LAN primary, WiFi fallback) ---");
  if (!initializeWiFi()) {
    Serial.println("Network is not connected yet; retrying in the main loop...");
  }

  if (wifiConnected) {
    initializeOTA();
  }

  Serial.println("\n--- MQTT configuration ---");
  initializeMqtt();
  lastCommandTime = millis();

  Serial.println("\n------------------------------------------------");
  Serial.println(" Setup complete");
  Serial.println("------------------------------------------------");
}

void loop() {
  if (wifiConnected) {
    handleOTA();
    if (isOTAInProgress()) {
      delay(10);
      return;
    }
  }

  handleStatusLed(isWiFiConnected(), isMqttConnected());
  resetWatchdog();

  if (isMqttConnected()) {
    mqttLoop();
  }

  handleCovers();

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

  static unsigned long lastDetailedCheck = 0;
  if (currentTime - lastDetailedCheck >= 10000) {
    lastDetailedCheck = currentTime;
    monitorConnections();
  }

  static unsigned long mqttDisconnectedSince = 0;
  if (!isMqttConnected()) {
    if (mqttDisconnectedSince == 0) {
      mqttDisconnectedSince = currentTime;
    }

    if (!allCoversStopped && (currentTime - mqttDisconnectedSince > NETWORK_FAILOVER_GRACE)) {
      debugPrint("MQTT connection lost after failover grace -> stopping covers");
      stopAllCovers("mqtt_disconnect");
    }
  } else {
    mqttDisconnectedSince = 0;
  }

  if (!allCoversStopped && (currentTime - lastCommandTime > NO_COMMAND_TIMEOUT)) {
     debugPrint("TIMEOUT: stopping covers due to command inactivity");
     stopAllCovers("inactivity_timeout");
     publishAllCoverStates("inactivity_timeout");
     lastCommandTime = currentTime;
  }

  delay(1);
}