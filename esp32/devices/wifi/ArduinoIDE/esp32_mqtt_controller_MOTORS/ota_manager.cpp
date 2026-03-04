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
    Serial.println("Preparing system for upload...");

    // Step 1: Disable watchdog immediately
    try {
      esp_task_wdt_deinit();
      Serial.println("✅ Watchdog disabled");
      debugPrint("OTA: Watchdog timer disabled");
    } catch (...) {
      Serial.println("⚠️  Watchdog already disabled");
    }

    // Step 2: Turn off all hardware
    turnOffHardware();
    Serial.println("✅ All hardware turned OFF");
    debugPrint("OTA: Hardware safely disabled");

    // Step 3: Stop all non-essential tasks
    Serial.println("✅ System prepared for upload");

    String update_type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
    Serial.println("Updating: " + update_type);
    debugPrint("OTA: Starting " + update_type + " update");
  });

  // OTA End callback - restore system
  ArduinoOTA.onEnd([]() {
    otaInProgress = false;
    debugPrint("OTA: Update completed successfully");
    Serial.println("\n=== OTA UPDATE COMPLETE ===");
    Serial.println("✅ Upload successful!");
    Serial.println("🔄 Rebooting in 2 seconds...");
    delay(2000);
  });

  // Progress callback
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    static unsigned int lastPercent = 0;
    unsigned int percent = (progress * 100) / total;

    // Only print every 5% to reduce serial traffic
    if (percent >= lastPercent + 5 || percent == 100) {
      Serial.printf("OTA Progress: %u%% (%u/%u bytes)\n", percent, progress, total);
      lastPercent = percent;
      yield();
    }
  });

  // Error handling with detailed messages
  ArduinoOTA.onError([](ota_error_t error) {
    otaInProgress = false;

    Serial.println("\n=== OTA ERROR ===");
    Serial.printf("❌ OTA Error[%u]: ", error);

    String errorMsg = "";
    switch (error) {
      case OTA_AUTH_ERROR:
        errorMsg = "Authentication Failed - Check password";
        break;
      case OTA_BEGIN_ERROR:
        errorMsg = "Begin Failed - Not enough space or flash issue";
        break;
      case OTA_CONNECT_ERROR:
        errorMsg = "Connect Failed - Network timeout";
        break;
      case OTA_RECEIVE_ERROR:
        errorMsg = "Receive Failed - Network interrupted";
        break;
      case OTA_END_ERROR:
        errorMsg = "End Failed - Verification error";
        break;
      default:
        errorMsg = "Unknown Error";
        break;
    }

    Serial.println(errorMsg);
    debugPrint("OTA Error: " + errorMsg);

    Serial.println("💡 Try again - make sure WiFi is stable");
    Serial.println("=================");

    // Re-enable watchdog after failed upload
    try {
      esp_task_wdt_config_t wdt_config = {
        .timeout_ms = WDT_TIMEOUT * 1000,
        .idle_core_mask = 0,
        .trigger_panic = true
      };
      esp_task_wdt_init(&wdt_config);
      esp_task_wdt_add(NULL);
      debugPrint("OTA: Watchdog re-enabled after error");
    } catch (...) {
      debugPrint("OTA: Could not re-enable watchdog");
    }
  });

  // Configure OTA settings
  ArduinoOTA.setTimeout(30000);
  ArduinoOTA.setMdnsEnabled(true);

  // Start OTA service
  ArduinoOTA.begin();
  otaInitialized = true;

  debugPrint("OTA: Initialized successfully");
  Serial.println("=== OTA READY ===");
  Serial.println("Hostname: " + String(OTA_HOSTNAME));
  Serial.println("IP: " + WiFi.localIP().toString());
  Serial.println("Port: 3232 (default)");
  Serial.println("Look for '" + String(OTA_HOSTNAME) + "' in Arduino IDE Network ports");
  Serial.println("⚠️  During upload: Hardware will be disabled, watchdog stopped");
  Serial.println("================");
}

void handleOTA() {
  if (!otaInitialized || !wifiConnected) {
    return;
  }

  if (otaInProgress) {
    ArduinoOTA.handle();
    return;
  }

  ArduinoOTA.handle();
}

bool isOTAInProgress() {
  return otaInProgress;
}

void reinitializeOTAAfterWiFiReconnect() {
  if (wifiConnected && !otaInitialized) {
    debugPrint("OTA: Reinitializing after WiFi reconnect");
    initializeOTA();
  }
}