#include "connection_monitor.h"
#include "config.h"
#include "debug.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include <WiFi.h>

// Global monitoring state
unsigned long lastConnectionCheck = 0;

void monitorConnections() {
  unsigned long currentTime = millis();

  if (currentTime - lastConnectionCheck >= CONNECTION_CHECK_INTERVAL) {
    lastConnectionCheck = currentTime;
    debugPrint("Status - WiFi: " + String(WiFi.status() == WL_CONNECTED ? "OK" : "FAIL") +
               ", MQTT: " + String(client.connected() ? "OK" : "FAIL"));

    if (WiFi.status() != WL_CONNECTED && wifiConnected) {
      wifiConnected = false;
      mqttConnected = false;
      debugPrint("WiFi connection lost");
    } else if (WiFi.status() == WL_CONNECTED && !wifiConnected) {
      wifiConnected = true;
      debugPrint("WiFi restored");
    }
  }
}