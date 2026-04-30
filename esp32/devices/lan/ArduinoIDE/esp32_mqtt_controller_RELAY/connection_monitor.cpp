#include "connection_monitor.h"
#include "config.h"
#include "debug.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"

// Global monitoring state
unsigned long lastConnectionCheck = 0;

void monitorConnections() {
  unsigned long currentTime = millis();

  if (currentTime - lastConnectionCheck >= CONNECTION_CHECK_INTERVAL) {
    lastConnectionCheck = currentTime;

    String networkStatus = isWiFiConnected() ? getActiveNetworkName() : "FAIL";
    String mqttStatus = client.connected() ? "OK" : "FAIL";

    debugPrint("Status - Network: " + networkStatus + ", MQTT: " + mqttStatus);

    if (!isWiFiConnected() && mqttConnected) {
      mqttConnected = false;
    }
  }
}
