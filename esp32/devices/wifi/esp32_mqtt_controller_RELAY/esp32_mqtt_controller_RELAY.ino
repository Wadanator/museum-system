/*
 * ESP32 Univerzálny MQTT Relay Controller
 * ========================================
 * 
 * Univerzálny kontrolér pre reléové zariadenia s MQTT komunikáciou.
 * Robustný, jednoduchý a spoľahlivý.
 * 
 * MQTT Príkazy:
 * - room1/[device_name] -> "ON" alebo "OFF" (prípadne "1" alebo "0")
 * - room1/STOP -> vypne všetky zariadenia
 * 
 * Feedback:
 * - room1/[device_name]/feedback -> "OK" alebo "ERROR"
 * 
 * Status:
 * - devices/esp32_relay_controller/status -> "online" alebo "offline"
 * 
 * Konfigurácia zariadení je v config.h
 */

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

  Serial.println("\n╔════════════════════════════════════════╗");
  Serial.println("║ ESP32 MQTT Relay Controller v1.0      ║");
  Serial.println("╚════════════════════════════════════════╝");
  debugPrint("=== System štartuje ===");

  // Inicializuj Watchdog Timer (60s)
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000,
    .idle_core_mask = 0,
    .trigger_panic = true
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
  debugPrint("⏱️  Watchdog Timer inicializovaný (" + String(WDT_TIMEOUT) + "s)");

  // Inicializuj hardware (relé)
  Serial.println("\n--- Inicializácia hardwaru ---");
  initializeHardware();

  // Pripoj sa na WiFi
  Serial.println("\n--- WiFi pripojenie ---");
  if (!initializeWiFi()) {
    Serial.println("⚠️  WiFi zlyhalo, skúsim znovu...");
    debugPrint("Počiatočné WiFi pripojenie zlyhalo");
  }

  // Inicializuj MQTT
  Serial.println("\n--- MQTT konfigurácia ---");
  initializeMqtt();

  Serial.println("\n╔════════════════════════════════════════╗");
  Serial.println("║ ✅ Setup dokončený                     ║");
  Serial.println("╠════════════════════════════════════════╣");
  Serial.println("║ Počúvam na: " + String(BASE_TOPIC_PREFIX) + "*" + String("                ║").substring(String(BASE_TOPIC_PREFIX).length() + 1));
  Serial.println("║ Zariadení: " + String(DEVICE_COUNT) + String("                             ║").substring(String(DEVICE_COUNT).length()));
  Serial.println("╚════════════════════════════════════════╝\n");
  debugPrint("=== Setup dokončený ===");
}

void loop() {
  // Reset watchdog (systém beží správne)
  esp_task_wdt_reset();

  // MQTT loop - najdôležitejšie, musí byť prvý
  if (isMqttConnected()) {
    mqttLoop();
  }

  static unsigned long lastQuickCheck = 0;
  unsigned long currentTime = millis();

  // Rýchla kontrola spojení (každých 100ms)
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

  // Detailná kontrola spojení (každých 10s)
  static unsigned long lastDetailedCheck = 0;
  if (currentTime - lastDetailedCheck >= 10000) {
    lastDetailedCheck = currentTime;
    monitorConnections();
  }

  // Bezpečnostná kontrola - ak nie je MQTT, vypni všetko
  if (!isMqttConnected() && !allDevicesOff) {
    turnOffAllDevices();
  }

  delay(10);
}