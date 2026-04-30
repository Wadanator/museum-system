#include <esp_task_wdt.h>
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "connection_monitor.h"
#include "ota_manager.h"
#include "status_led.h"
#include "effects_manager.h"

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n------------------------------------------");
  Serial.println(" ESP32 LAN+WiFi MQTT Relay Controller v2.4 + Effects");
  Serial.println("------------------------------------------");
  debugPrint("=== System startuje ===");
  
  // Watchdog konfiguracia
  esp_task_wdt_deinit();
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000,
    .idle_core_mask = 0,
    .trigger_panic = true
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
  debugPrint("Watchdog Timer inicializovany (" + String(WDT_TIMEOUT) + "s)");
  
  Serial.println("\n--- Inicializacia hardwaru ---");
  initializeHardware();
  
  // Inicializácia Status LED
  initializeStatusLed();

  initializeEffects();
  
  Serial.println("\n--- Network pripojenie (LAN primary, WiFi fallback) ---");
  if (!initializeWiFi()) {
    Serial.println("Network zatial nepripojene, budem skusat dalej...");
  }

  // OTA inicializacia
  if (wifiConnected) {
    initializeOTA();
  }

  Serial.println("\n--- MQTT konfiguracia ---");
  initializeMqtt();
  lastCommandTime = millis();
  
  Serial.println("\n------------------------------------------");
  Serial.println(" Setup dokonceny");
  Serial.println("------------------------------------------");
}

void loop() {
  // 1. OTA Handle (musi byt prve)
  if (wifiConnected) {
    handleOTA();
    if (isOTAInProgress()) {
      delay(10);
      return; // Ak bezi update, prerusime loop
    }
  }

  // 2. Obsluha Status LED
  handleStatusLed(isWiFiConnected(), isMqttConnected());

  // 3. Reset Watchdog
  esp_task_wdt_reset();

  // 4. MQTT Logika
  if (isMqttConnected()) {
    mqttLoop();
  }

  handleEffects();

  // 6. Kontrola casovacov (auto-off pre bežné zariadenia)
  handleAutoOff();

  // 7. Rychla kontrola spojenia
  static unsigned long lastQuickCheck = 0;
  unsigned long currentTime = millis();

  if (currentTime - lastQuickCheck >= 100) {
    lastQuickCheck = currentTime;
    static bool previousNetworkConnected = false;
    reconnectWiFi();

    if (wifiConnected && !previousNetworkConnected) {
      reinitializeOTAAfterWiFiReconnect();
    }
    previousNetworkConnected = wifiConnected;

    if (wifiConnected && !isMqttConnected()) {
      connectToMqtt();
    }
  }

  // 8. Detailna kontrola a logovanie
  static unsigned long lastDetailedCheck = 0;
  if (currentTime - lastDetailedCheck >= 10000) {
    lastDetailedCheck = currentTime;
    monitorConnections();
  }

  // 9. Bezpecnostne ochrany
  static unsigned long mqttDisconnectedSince = 0;
  if (!isMqttConnected()) {
    if (mqttDisconnectedSince == 0) {
      mqttDisconnectedSince = currentTime;
    }

    if (!allDevicesOff && (currentTime - mqttDisconnectedSince > NETWORK_FAILOVER_GRACE)) {
      debugPrint("Strata MQTT spojenia po failover grace -> Vypinam zariadenia");
      turnOffAllDevices();
      stopAllEffects();
    }
  } else {
    mqttDisconnectedSince = 0;
  }
  
  if (!allDevicesOff && (currentTime - lastCommandTime > NO_COMMAND_TIMEOUT)) {
     debugPrint("TIMEOUT: Vypinam zariadenia z dovodu necinnosti");
     turnOffAllDevices();
     stopAllEffects();
     lastCommandTime = currentTime;
  }

  delay(1);
}
