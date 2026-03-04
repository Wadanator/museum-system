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

  Serial.println("\n=== ESP32 Scene Trigger Starting ===");
  debugPrint("=== Startup ===");

  initializeWatchdog(); // Spustí WDT
  initializeHardware(); // Inicializuje pin 32 s externým rezistorom

  if (!initializeWiFi()) {
    debugPrint("Initial WiFi failed");
  }

  if (wifiConnected) {
    initializeOTA(); // Spustí OTA
  }

  initializeMqtt(); // Nastaví MQTT
  Serial.println("Ready - Waiting for button press on PIN " + String(BUTTON_PIN));
}

void loop() {
  // 1. OTA Handle (priorita pre nahrávanie kódu)
  if (wifiConnected) {
    handleOTA();
    if (isOTAInProgress()) return;
  }

  // 2. MQTT Loop (udržiavanie spojenia a ping)
  if (isMqttConnected()) {
    mqttLoop();
  }

  // 3. LOGIKA TLAČIDLA (Tu sa uplatňuje cooldown z hardware.cpp)
  if (wasButtonPressed()) {
    publishSceneTrigger(); // Odoslanie MQTT správy
  }

  // 4. Watchdog reset - kŕmenie "psa" pre stabilitu
  resetWatchdog();

  // 5. Connection Management (Automatický reconnect)
  static unsigned long lastCheck = 0;
  unsigned long currentTime = millis();

  if (currentTime - lastCheck >= 100) {
    lastCheck = currentTime;
    if (!isWiFiConnected()) {
      reconnectWiFi();
      if (wifiConnected) reinitializeOTAAfterWiFiReconnect();
    }
    if (wifiConnected && !isMqttConnected()) {
      connectToMqtt();
    }
  }

  // 6. Monitoring (Status logy do konzoly)
  monitorConnections();

  delay(10); 
}