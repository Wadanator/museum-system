#include "wifi_manager.h"
#include "config.h"
#include "debug.h"

// Global WiFi state
bool wifiConnected = false;
unsigned long lastWifiAttempt = 0;

bool initializeWiFi() {
  debugPrint("Connecting to WiFi: " + String(WIFI_SSID));
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 20) {
    delay(500);
    timeout++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected - IP: ");
    Serial.println(WiFi.localIP());
    debugPrint("WiFi connected: " + WiFi.localIP().toString());
    wifiConnected = true;
    lastWifiAttempt = 0;
    return true;
  }

  wifiConnected = false;
  debugPrint("WiFi connection failed");
  return false;
}

void reconnectWiFi() {
  unsigned long currentTime = millis();
  static int wifiAttempts = 0;
  static unsigned long wifiRetryInterval = WIFI_RETRY_INTERVAL;

  if (WiFi.status() != WL_CONNECTED && (currentTime - lastWifiAttempt >= wifiRetryInterval)) {
    debugPrint("WiFi reconnect attempt " + String(wifiAttempts + 1) + "/" + String(MAX_WIFI_ATTEMPTS));
    lastWifiAttempt = currentTime;
    wifiAttempts++;

    WiFi.disconnect();
    delay(100);

    if (initializeWiFi()) {
      Serial.println("WiFi reconnected");
      debugPrint("WiFi reconnected successfully");
      wifiAttempts = 0;
      wifiRetryInterval = WIFI_RETRY_INTERVAL;
    } else {
      wifiRetryInterval = min(wifiRetryInterval * 2, MAX_RETRY_INTERVAL);
      debugPrint("WiFi failed - retry in " + String(wifiRetryInterval) + "ms");

      if (wifiAttempts >= MAX_WIFI_ATTEMPTS) {
        debugPrint("Max WiFi attempts - restarting");
        ESP.restart();
      }
    }
  }
}

bool isWiFiConnected() {
  return WiFi.status() == WL_CONNECTED;
}