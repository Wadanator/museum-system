#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "connection_monitor.h"
#include "ota_manager.h"
#include "wdt_manager.h"

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println("\n=== ESP32 MQTT Controller Starting ===");
  debugPrint("=== ESP32 MQTT Controller Starting ===");

  // The watchdog is active before hardware and network initialization.
  initializeWatchdog();

  initializeHardware();
  if (!initializeWiFi()) {
    Serial.println("WiFi failed, will retry...");
    debugPrint("Initial WiFi failed");
  }

  // OTA is enabled only after WiFi is connected.
  if (wifiConnected) {
    initializeOTA();
  }

  initializeMqtt();

  Serial.println("=== Setup Complete ===");
  Serial.println("Ready - Listening on: " + String(BASE_TOPIC_PREFIX) + "#");
  debugPrint("=== Setup completed ===");
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

  // MQTT is serviced before motor smoothing to keep command feedback responsive.
  if (isMqttConnected()) {
    mqttLoop();
  }

  updateMotorSmoothly();

  // Watchdog service is suspended while OTA owns the loop.
  if (!isOTAInProgress()) {

    resetWatchdog();
  }

  static unsigned long lastQuickCheck = 0;
  unsigned long currentTime = millis();

  // WiFi and MQTT reconnects are checked frequently for fast recovery.
  if (currentTime - lastQuickCheck >= 100) {
    lastQuickCheck = currentTime;
    if (!isWiFiConnected()) {
      reconnectWiFi();
      if (wifiConnected) {
        reinitializeOTAAfterWiFiReconnect();
      }
    }

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

  // Motors are de-energized immediately when MQTT is unavailable.
  if (!isMqttConnected() && !hardwareOff) {
    turnOffHardware();
  }

  // Deadman timeout: if no valid command arrives for too long, force motors off.
  if (!hardwareOff && lastCommandTime > 0 &&
      (currentTime - lastCommandTime > NO_COMMAND_TIMEOUT)) {
    debugPrint("Command inactivity timeout -> turning motors OFF");
    turnOffHardware();
    publishAllMotorStates("timeout");
    lastCommandTime = currentTime;
  }

  delay(10);
}
