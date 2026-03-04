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
    
    String wifiStatus = WiFi.status() == WL_CONNECTED ? "OK" : "FAIL";
    String mqttStatus = client.connected() ? "OK" : "FAIL";
    
    debugPrint("📊 Status - WiFi: " + wifiStatus + ", MQTT: " + mqttStatus);

    // Detekcia straty WiFi spojenia
    if (WiFi.status() != WL_CONNECTED && wifiConnected) {
      wifiConnected = false;
      mqttConnected = false;
      Serial.println("⚠️  WiFi spojenie stratené");
      debugPrint("WiFi spojenie stratené");
    } 
    // Detekcia obnovy WiFi spojenia
    else if (WiFi.status() == WL_CONNECTED && !wifiConnected) {
      wifiConnected = true;
      Serial.println("✅ WiFi spojenie obnovené");
      debugPrint("WiFi spojenie obnovené");
    }
  }
}