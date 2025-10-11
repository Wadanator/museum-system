#include "wifi_manager.h"
#include "config.h"
#include "debug.h"

// Global WiFi state
bool wifiConnected = false;
unsigned long lastWifiAttempt = 0;

bool initializeWiFi() {
  debugPrint("Pripájam sa na WiFi: " + String(WIFI_SSID));
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 20) {
    delay(500);
    Serial.print(".");
    timeout++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("✅ WiFi pripojené - IP: ");
    Serial.println(WiFi.localIP());
    debugPrint("WiFi pripojené: " + WiFi.localIP().toString());
    wifiConnected = true;
    lastWifiAttempt = 0;
    return true;
  }

  Serial.println("❌ WiFi zlyhalo");
  wifiConnected = false;
  debugPrint("WiFi pripojenie zlyhalo");
  return false;
}

void reconnectWiFi() {
  unsigned long currentTime = millis();
  static int wifiAttempts = 0;
  static unsigned long wifiRetryInterval = WIFI_RETRY_INTERVAL;

  if (WiFi.status() != WL_CONNECTED && (currentTime - lastWifiAttempt >= wifiRetryInterval)) {
    debugPrint("WiFi reconnect pokus " + String(wifiAttempts + 1) + "/" + String(MAX_WIFI_ATTEMPTS));
    lastWifiAttempt = currentTime;
    wifiAttempts++;

    WiFi.disconnect();
    delay(100);

    if (initializeWiFi()) {
      Serial.println("✅ WiFi znovu pripojené");
      debugPrint("WiFi znovu pripojené");
      wifiAttempts = 0;
      wifiRetryInterval = WIFI_RETRY_INTERVAL;
    } else {
      wifiRetryInterval = min(wifiRetryInterval * 2, MAX_RETRY_INTERVAL);
      debugPrint("WiFi zlyhalo - skúsim znovu za " + String(wifiRetryInterval) + "ms");

      if (wifiAttempts >= MAX_WIFI_ATTEMPTS) {
        debugPrint("Max WiFi pokusov dosiahnutý - reštartujem ESP32");
        Serial.println("🔄 Reštartujem ESP32...");
        delay(1000);
        ESP.restart();
      }
    }
  }
}

bool isWiFiConnected() {
  return WiFi.status() == WL_CONNECTED;
}