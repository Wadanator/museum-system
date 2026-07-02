#include "ota_manager.h"
#include <ArduinoOTA.h>
#include <esp_task_wdt.h>
#include <string.h>
#include "config.h"
#include "debug.h"
#include "wifi_manager.h"
#include "hardware.h"
#include "status_led.h"
#include "wdt_manager.h"

// OTA state.
bool otaInProgress = false;
bool otaInitialized = false;

void initializeOTA() {
  if (!wifiConnected || !isWiFiConnected()) {
    debugPrint("OTA: network not connected, skipping setup");
    return;
  }

  if (otaInitialized) return;

  ArduinoOTA.setHostname(OTA_HOSTNAME);
  if (strlen(OTA_PASSWORD) > 0) {
    ArduinoOTA.setPassword(OTA_PASSWORD);
  }

  ArduinoOTA.onStart([]() {
    otaInProgress = true;
    Serial.println("=== OTA UPDATE STARTING ===");

    setOtaLedState(true);

    // Flash writes may exceed the normal watchdog service interval.
    esp_task_wdt_deinit();

    // All cover motors are stopped before firmware replacement starts.
    stopAllCovers("ota_start");
    Serial.println("[OK] Cover motors safely stopped");

    String update_type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
    Serial.println("Updating: " + update_type);
  });

  ArduinoOTA.onEnd([]() {
    otaInProgress = false;
    setOtaLedState(false);
    Serial.println("\n=== OTA UPDATE COMPLETE ===");
    Serial.println(" Rebooting...");
    delay(1000);
  });

  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    static unsigned int lastPercent = 0;
    unsigned int percent = (progress * 100) / total;
    if (percent >= lastPercent + 10 || percent == 100) {
      Serial.printf("OTA Progress: %u%%\n", percent);
      lastPercent = percent;
    }
  });

  ArduinoOTA.onError([](ota_error_t error) {
    otaInProgress = false;
    setOtaLedState(false);
    Serial.printf("[ERROR] OTA Error[%u]\n", error);

    // Restore normal watchdog protection after a failed update.
    initializeWatchdog();
  });

  ArduinoOTA.setTimeout(30000);
  ArduinoOTA.begin();
  otaInitialized = true;

  debugPrint("OTA: Initialized successfully via " + String(getActiveNetworkName()));
  Serial.println("OTA READY: " + String(OTA_HOSTNAME) + " via " + String(getActiveNetworkName()));
}

void handleOTA() {
  if (!otaInitialized || !wifiConnected) return;
  ArduinoOTA.handle();
}

bool isOTAInProgress() {
  return otaInProgress;
}

void reinitializeOTAAfterWiFiReconnect() {
  if (wifiConnected && !otaInitialized) {
    initializeOTA();
  }
}