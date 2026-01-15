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
  Serial.println(" ESP32 MQTT Relay Controller v2.0");
  Serial.println("------------------------------------------");
  debugPrint("=== System startuje ===");
  
  // Inicializuj Watchdog Timer (60s)
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000,
    .idle_core_mask = 0,
    .trigger_panic = true
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
  debugPrint("Watchdog Timer inicializovany (" + String(WDT_TIMEOUT) + "s)");
  
  // Inicializuj hardware (rele)
  Serial.println("\n--- Inicializacia hardwaru ---");
  initializeHardware();

  // Pripoj sa na WiFi
  Serial.println("\n--- WiFi pripojenie ---");
  if (!initializeWiFi()) {
    Serial.println("WiFi zlyhalo, skusim znovu...");
    debugPrint("Pociatocne WiFi pripojenie zlyhalo");
  }

  // Inicializuj MQTT
  Serial.println("\n--- MQTT konfiguracia ---");
  initializeMqtt();
  
  // Inicializacia casovaca timeoutu
  lastCommandTime = millis();

  Serial.println("\n------------------------------------------");
  Serial.println(" Setup dokonceny");
  Serial.println("------------------------------------------");
  Serial.println("Pocuvam na: " + String(BASE_TOPIC_PREFIX) + "*");
  Serial.println("Zariadeni: " + String(DEVICE_COUNT));
  debugPrint("=== Setup dokonceny ===");
}

void loop() {
  // Reset watchdog (system bezi spravne)
  esp_task_wdt_reset();
  
  // MQTT loop - najdolezitejsie, musi byt prvy
  if (isMqttConnected()) {
    mqttLoop();
  }

  static unsigned long lastQuickCheck = 0;
  unsigned long currentTime = millis();
  
  // Rychla kontrola spojeni (kazdych 100ms)
  if (currentTime - lastQuickCheck >= 100) {
    lastQuickCheck = currentTime;
    
    // Kontrola a reconnect WiFi
    if (!isWiFiConnected()) {
      reconnectWiFi();
    }

    // Kontrola a reconnect MQTT
    if (wifiConnected && !isMqttConnected()) {
      connectToMqtt();
    }
  }

  // Detailna kontrola spojeni (kazdych 10s)
  static unsigned long lastDetailedCheck = 0;
  if (currentTime - lastDetailedCheck >= 10000) {
    lastDetailedCheck = currentTime;
    monitorConnections();
  }

  // === BEZPECNOSTNE OCHRANY ===

  // 1. Bezpecnostna kontrola - ak nie je MQTT, vypni vsetko
  if (!isMqttConnected() && !allDevicesOff) {
    debugPrint("Strata MQTT spojenia -> Vypinam zariadenia");
    turnOffAllDevices();
  }
  
  // Ak je aspon jedno zariadenie zapnute A presiel casovy limit bez prikazu
  if (!allDevicesOff && (currentTime - lastCommandTime > NO_COMMAND_TIMEOUT)) {
     Serial.println("TIMEOUT: Ziadny riadiaci signal " + String(NO_COMMAND_TIMEOUT/60000) + " minut.");
     debugPrint("TIMEOUT: Vypinam zariadenia z dovodu necinnosti");
     turnOffAllDevices();
     
     // Reset casovaca aby sa to necyklilo v logoch
     lastCommandTime = currentTime; 
  }

  delay(10);
}