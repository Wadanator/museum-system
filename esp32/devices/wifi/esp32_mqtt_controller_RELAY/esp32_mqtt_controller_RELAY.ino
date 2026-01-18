#include <esp_task_wdt.h>
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "connection_monitor.h"

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println("\n------------------------------------------");
  Serial.println(" ESP32 MQTT Relay Controller v2.2");
  Serial.println("------------------------------------------");
  debugPrint("=== System startuje ===");
  
  // FIX PRE WATCHDOG
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
  
  Serial.println("\n--- WiFi pripojenie ---");
  if (!initializeWiFi()) {
    Serial.println("WiFi zlyhalo, skusim znovu...");
  }

  Serial.println("\n--- MQTT konfiguracia ---");
  initializeMqtt();
  
  lastCommandTime = millis();

  Serial.println("\n------------------------------------------");
  Serial.println(" Setup dokonceny");
  Serial.println(" Pocuvam na: " + String(BASE_TOPIC_PREFIX) + "*");
  Serial.println("------------------------------------------");
}

void loop() {
  // 1. Reset Watchdog
  esp_task_wdt_reset();

  // 2. MQTT Logika
  if (isMqttConnected()) {
    mqttLoop();
  }

  // 3. NOVÉ: Kontrola časovačov pre dymostroj a iné limitované veci
  // Toto zabezpečí, že sa dymostroj vypne po 5 sekundách, aj keď spadne WiFi
  handleAutoOff();

  static unsigned long lastQuickCheck = 0;
  unsigned long currentTime = millis();

  // 4. Rýchla kontrola spojenia (100ms)
  if (currentTime - lastQuickCheck >= 100) {
    lastQuickCheck = currentTime;

    if (!isWiFiConnected()) {
      reconnectWiFi();
    }

    if (wifiConnected && !isMqttConnected()) {
      connectToMqtt();
    }
  }

  // 5. Detailná kontrola (10s)
  static unsigned long lastDetailedCheck = 0;
  if (currentTime - lastDetailedCheck >= 10000) {
    lastDetailedCheck = currentTime;
    monitorConnections();
  }

  // 6. Bezpečnostné ochrany
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