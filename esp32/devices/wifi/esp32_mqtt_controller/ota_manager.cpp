#include "ota_manager.h"
#include <ArduinoOTA.h>
#include "config.h"     // ⭐ Použije OTA_HOSTNAME z config.h
#include "debug.h"
#include "wifi_manager.h"
#include "hardware.h"


// OTA stav
bool otaInProgress = false;

void initializeOTA() {
  if (!wifiConnected || !isWiFiConnected()) {
    debugPrint("OTA: WiFi not connected, skipping OTA setup");
    return;
  }

  ArduinoOTA.setHostname(OTA_HOSTNAME);
  
  if (strlen(OTA_PASSWORD) > 0) {
    ArduinoOTA.setPassword(OTA_PASSWORD);
  }

  // OTA začína
  ArduinoOTA.onStart([]() {
    otaInProgress = true;
    
    // Vypni hardware pre bezpečnosť
    turnOffHardware();
    
    debugPrint("OTA: Update starting...");
    Serial.println("OTA Update Starting...");
  });

  // OTA skončilo
  ArduinoOTA.onEnd([]() {
    otaInProgress = false;
    debugPrint("OTA: Update completed");
    Serial.println("\nOTA Update Complete! Rebooting...");
  });

  // Progress info
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    int percent = (progress / (total / 100));
    Serial.printf("OTA Progress: %u%%\r", percent);
  });

  // Error handling
  ArduinoOTA.onError([](ota_error_t error) {
    otaInProgress = false;
    debugPrint("OTA Error: " + String(error));
    
    Serial.printf("OTA Error[%u]: ", error);
    if (error == OTA_AUTH_ERROR) {
      Serial.println("Auth Failed");
    } else if (error == OTA_BEGIN_ERROR) {
      Serial.println("Begin Failed");
    } else if (error == OTA_CONNECT_ERROR) {
      Serial.println("Connect Failed");
    } else if (error == OTA_RECEIVE_ERROR) {
      Serial.println("Receive Failed");
    } else if (error == OTA_END_ERROR) {
      Serial.println("End Failed");
    }
  });

  // Štart OTA
  ArduinoOTA.begin();
  
  debugPrint("OTA: Ready! Hostname: " + String(OTA_HOSTNAME));
  Serial.println("=== OTA READY ===");
  Serial.println("Hostname: " + String(OTA_HOSTNAME));
  Serial.println("IP: " + WiFi.localIP().toString());
  Serial.println("Look for '" + String(OTA_HOSTNAME) + "' in Arduino IDE Network ports");
  Serial.println("================");
}

void handleOTA() {
  // Jednoducho spracuj OTA
  ArduinoOTA.handle();
}