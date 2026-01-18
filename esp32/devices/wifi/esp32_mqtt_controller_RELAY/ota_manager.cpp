#include "ota_manager.h"
#include <ArduinoOTA.h>
#include <esp_task_wdt.h>
#include "config.h"
#include "debug.h"
#include "wifi_manager.h"
#include "hardware.h"   // Pre funkciu turnOffAllDevices()
#include "status_led.h" // Pre ovládanie LED počas update

// OTA stav
bool otaInProgress = false;
bool otaInitialized = false;

void initializeOTA() {
  if (!wifiConnected || !isWiFiConnected()) {
    debugPrint("OTA: WiFi not connected, skipping setup");
    return;
  }

  if (otaInitialized) return;

  ArduinoOTA.setHostname(OTA_HOSTNAME);
  if (strlen(OTA_PASSWORD) > 0) {
    ArduinoOTA.setPassword(OTA_PASSWORD);
  }

  // Callback pri štarte nahrávania
  ArduinoOTA.onStart([]() {
    otaInProgress = true;
    Serial.println("=== OTA UPDATE STARTING ===");

    // 1. Zapnutie modrej LED (ak je podporovaná)
    setOtaLedState(true);

    // 2. Vypnutie Watchdogu
    try {
      esp_task_wdt_deinit();
    } catch (...) {}

    // 3. Bezpečné vypnutie všetkých relé
    turnOffAllDevices(); 
    Serial.println("✅ Hardware safely disabled");

    String update_type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
    Serial.println("Updating: " + update_type);
  });

  // Callback pri ukončení
  ArduinoOTA.onEnd([]() {
    otaInProgress = false;
    setOtaLedState(false); // Vypnutie LED
    Serial.println("\n=== OTA UPDATE COMPLETE ===");
    Serial.println("🔄 Rebooting...");
    delay(1000);
  });

  // Callback počas nahrávania
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    static unsigned int lastPercent = 0;
    unsigned int percent = (progress * 100) / total;
    if (percent >= lastPercent + 10 || percent == 100) {
      Serial.printf("OTA Progress: %u%%\n", percent);
      lastPercent = percent;
    }
  });

  // Callback pri chybe
  ArduinoOTA.onError([](ota_error_t error) {
    otaInProgress = false;
    setOtaLedState(false);
    Serial.printf("❌ OTA Error[%u]\n", error);
    
    // Obnova Watchdogu
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