#include <esp_task_wdt.h>
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "connection_monitor.h"
#include "ota_manager.h"
#include "status_led.h" // Includujeme modul pre LED

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println("\n------------------------------------------");
  Serial.println(" ESP32 MQTT Relay Controller v2.3");
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
  
  // --- OPRAVA: Inicializácia Status LED ---
  initializeStatusLed();
  // ----------------------------------------
  
  Serial.println("\n--- WiFi pripojenie ---");
  if (!initializeWiFi()) {
    Serial.println("WiFi zlyhalo, skusim znovu...");
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
  // (LED teraz bude reagovať na stav WiFi a MQTT)
  handleStatusLed(isWiFiConnected(), isMqttConnected());

  // 3. Reset Watchdog
  esp_task_wdt_reset();

  // 4. MQTT Logika
  if (isMqttConnected()) {
    mqttLoop();
  }

  // 5. Kontrola casovacov (auto-off)
  handleAutoOff();

  // 6. Rychla kontrola spojenia
  static unsigned long lastQuickCheck = 0;
  unsigned long currentTime = millis();

  if (currentTime - lastQuickCheck >= 100) {
    lastQuickCheck = currentTime;
    
    if (!isWiFiConnected()) {
      reconnectWiFi();
      if (wifiConnected) {
        reinitializeOTAAfterWiFiReconnect();
      }
    }

    if (wifiConnected && !isMqttConnected()) {
      connectToMqtt();
    }
  }

  // 7. Detailna kontrola a logovanie
  static unsigned long lastDetailedCheck = 0;
  if (currentTime - lastDetailedCheck >= 10000) {
    lastDetailedCheck = currentTime;
    monitorConnections();
  }

  // 8. Bezpecnostne ochrany
  if (!isMqttConnected() && !allDevicesOff) {
    debugPrint("Strata MQTT spojenia -> Vypinam zariadenia");
    turnOffAllDevices();
  }
  
  if (!allDevicesOff && (currentTime - lastCommandTime > NO_COMMAND_TIMEOUT)) {
     debugPrint("TIMEOUT: Vypinam zariadenia z dovodu necinnosti");
     turnOffAllDevices();
     lastCommandTime = currentTime;
  }

  delay(10);
}