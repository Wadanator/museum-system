#include "ota_manager.h"
#include <ArduinoOTA.h>
#include <esp_task_wdt.h>
#include "config.h"
#include "debug.h"
#include "wifi_manager.h"
#include "hardware.h"

// OTA state
bool otaInProgress = false;
bool otaInitialized = false;

void initializeOTA() {
  if (!wifiConnected || !isWiFiConnected()) {
    debugPrint("OTA: WiFi not connected, skipping OTA setup");
    return;
  }

  if (otaInitialized) {
    debugPrint("OTA: Already initialized");
    return;
  }

  ArduinoOTA.setHostname(OTA_HOSTNAME);

  if (strlen(OTA_PASSWORD) > 0) {
    ArduinoOTA.setPassword(OTA_PASSWORD);
  }

  // OTA Start callback - prepare for upload
  ArduinoOTA.onStart([]() {
    otaInProgress = true;
    debugPrint("OTA: Update starting - preparing system...");
    Serial.println("=== OTA UPDATE STARTING ===");

    // Step 1: Disable watchdog immediately
    try {
      esp_task_wdt_deinit();
      Serial.println("✅ Watchdog disabled");
    } catch (...) {
      Serial.println("⚠️  Watchdog already disabled");
    }

    // Step 2: Turn off all hardware
    turnOffAllDevices(); 
    Serial.println("✅ All hardware turned OFF");
    debugPrint("OTA: Hardware safely disabled");

    String update_type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
    Serial.println("Updating: " + update_type);
  });

  // OTA End callback
  ArduinoOTA.onEnd([]() {
    otaInProgress = false;
    Serial.println("\n=== OTA UPDATE COMPLETE ===");
    Serial.println("🔄 Rebooting...");
    delay(1000);
  });

  // Progress callback
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    static unsigned int lastPercent = 0;
    unsigned int percent = (progress * 100) / total;
    if (percent >= lastPercent + 10 || percent == 100) {
      Serial.printf("OTA Progress: %u%%\n", percent);
      lastPercent = percent;
    }
  });

  // Error handling
  ArduinoOTA.onError([](ota_error_t error) {
    otaInProgress = false;
    Serial.printf("❌ OTA Error[%u]\n", error);
    // Re-enable watchdog after failed upload
    try {
      esp_task_wdt_config_t wdt_config = {
        .timeout_ms = WDT_TIMEOUT * 1000,
        .idle_core_mask = 0,
        .trigger_panic = true
      };
      esp_task_wdt_init(&wdt_config);
      esp_task_wdt_add(NULL);
    } catch (...) {}
  });

  ArduinoOTA.setTimeout(30000);
  ArduinoOTA.begin();
  otaInitialized = true;

  debugPrint("OTA: Initialized successfully");
  Serial.println("OTA READY: " + String(OTA_HOSTNAME));
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