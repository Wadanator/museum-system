#include "wifi_manager.h"
#include "config.h"
#include "debug.h"
#include <ETH.h>
#include <SPI.h>

// Compatibility names retained so the rest of the firmware stays unchanged.
// In this LAN build they represent Ethernet/W5500 state, not WiFi state.
bool wifiConnected = false;
unsigned long lastWifiAttempt = 0;

static bool ethernetStarted = false;

static void onEthernetEvent(arduino_event_id_t event, arduino_event_info_t info) {
  switch (event) {
    case ARDUINO_EVENT_ETH_START:
      Serial.println("LAN started");
      ETH.setHostname(OTA_HOSTNAME);
      break;

    case ARDUINO_EVENT_ETH_CONNECTED:
      Serial.println("LAN cable connected");
      break;

    case ARDUINO_EVENT_ETH_GOT_IP:
      wifiConnected = true;
      lastWifiAttempt = 0;
      Serial.print("LAN connected - IP: ");
      Serial.println(ETH.localIP());
      debugPrint("LAN connected: " + ETH.localIP().toString());
      break;

    case ARDUINO_EVENT_ETH_LOST_IP:
      Serial.println("LAN lost IP");
      wifiConnected = false;
      break;

    case ARDUINO_EVENT_ETH_DISCONNECTED:
      Serial.println("LAN disconnected");
      wifiConnected = false;
      break;

    case ARDUINO_EVENT_ETH_STOP:
      Serial.println("LAN stopped");
      wifiConnected = false;
      ethernetStarted = false;
      break;

    default:
      break;
  }
}

static void startEthernet() {
  if (ethernetStarted) return;

  debugPrint("Starting LAN Ethernet (W5500)");
  Network.onEvent(onEthernetEvent);
  SPI.begin(ETH_SPI_SCK_PIN, ETH_SPI_MISO_PIN, ETH_SPI_MOSI_PIN);
  ETH.begin(
    ETH_PHY_W5500,
    ETH_PHY_ADDR,
    ETH_PHY_CS_PIN,
    ETH_PHY_IRQ_PIN,
    ETH_PHY_RST_PIN,
    SPI
  );
  ethernetStarted = true;
}

bool initializeWiFi() {
  startEthernet();

  unsigned long startedAt = millis();
  while (!wifiConnected && (millis() - startedAt < NETWORK_CONNECT_TIMEOUT)) {
    delay(100);
  }

  if (wifiConnected) {
    lastWifiAttempt = 0;
    return true;
  }

  Serial.println("LAN not connected yet");
  debugPrint("LAN connection not ready");
  return false;
}

void reconnectWiFi() {
  unsigned long currentTime = millis();
  static int networkAttempts = 0;
  static unsigned long networkRetryInterval = NETWORK_RETRY_INTERVAL;

  if (!isWiFiConnected() && (currentTime - lastWifiAttempt >= networkRetryInterval)) {
    debugPrint("LAN reconnect check " + String(networkAttempts + 1) + "/" + String(MAX_NETWORK_ATTEMPTS));
    lastWifiAttempt = currentTime;
    networkAttempts++;

    if (!ethernetStarted) {
      startEthernet();
    }

    if (isWiFiConnected()) {
      Serial.println("LAN reconnected");
      debugPrint("LAN reconnected");
      networkAttempts = 0;
      networkRetryInterval = NETWORK_RETRY_INTERVAL;
    } else {
      networkRetryInterval = min(networkRetryInterval * 2, MAX_RETRY_INTERVAL);
      debugPrint("LAN still disconnected - retry in " + String(networkRetryInterval) + "ms");

      if (networkAttempts >= MAX_NETWORK_ATTEMPTS) {
        debugPrint("Max LAN reconnect checks reached - restarting ESP32");
        Serial.println("Restarting ESP32...");
        delay(1000);
        ESP.restart();
      }
    }
  }
}

bool isWiFiConnected() {
  return wifiConnected;
}
