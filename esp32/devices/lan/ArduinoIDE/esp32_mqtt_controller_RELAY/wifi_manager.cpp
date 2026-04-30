#include "wifi_manager.h"
#include "config.h"
#include "debug.h"
#include <ETH.h>
#include <Network.h>
#include <SPI.h>
#include <WiFi.h>

// Compatibility names retained so the rest of the firmware stays unchanged.
// In this hybrid build they represent "some network is connected".
bool wifiConnected = false;
unsigned long lastWifiAttempt = 0;

static bool networkEventsRegistered = false;
static bool ethernetStarted = false;
static bool fallbackWifiStarted = false;
static bool lanConnected = false;
static bool fallbackWifiConnected = false;
static bool fallbackStopRequested = false;
static NetworkTransport activeTransport = NETWORK_NONE;

static const char* transportName(NetworkTransport transport) {
  switch (transport) {
    case NETWORK_LAN:
      return "LAN";
    case NETWORK_WIFI:
      return "WiFi fallback";
    default:
      return "none";
  }
}

static void updateActiveTransport() {
  NetworkTransport nextTransport = NETWORK_NONE;

  if (lanConnected) {
    nextTransport = NETWORK_LAN;
  } else if (fallbackWifiConnected) {
    nextTransport = NETWORK_WIFI;
  }

  if (nextTransport != activeTransport) {
    Serial.print("Network transport: ");
    Serial.print(transportName(activeTransport));
    Serial.print(" -> ");
    Serial.println(transportName(nextTransport));
    debugPrint(
      "Network transport: " +
      String(transportName(activeTransport)) +
      " -> " +
      String(transportName(nextTransport))
    );
    activeTransport = nextTransport;
  }

  wifiConnected = (activeTransport != NETWORK_NONE);
}

static void stopFallbackWiFi() {
  if (!fallbackWifiStarted && !fallbackWifiConnected) {
    fallbackStopRequested = false;
    return;
  }

  Serial.println("Stopping WiFi fallback because LAN is active");
  debugPrint("Stopping WiFi fallback because LAN is active");
  WiFi.disconnect(true);
  fallbackWifiStarted = false;
  fallbackWifiConnected = false;
  fallbackStopRequested = false;
  updateActiveTransport();
}

static void startFallbackWiFi() {
  if (fallbackWifiStarted || fallbackWifiConnected) return;

  Serial.print("Starting WiFi fallback: ");
  Serial.println(WIFI_SSID);
  debugPrint("Starting WiFi fallback: " + String(WIFI_SSID));

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(OTA_HOSTNAME);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  fallbackWifiStarted = true;
}

static void onNetworkEvent(arduino_event_id_t event, arduino_event_info_t info) {
  (void)info;

  switch (event) {
    case ARDUINO_EVENT_ETH_START:
      Serial.println("LAN started");
      ETH.setHostname(OTA_HOSTNAME);
      break;

    case ARDUINO_EVENT_ETH_CONNECTED:
      Serial.println("LAN cable connected");
      break;

    case ARDUINO_EVENT_ETH_GOT_IP:
      lanConnected = true;
      lastWifiAttempt = 0;
      Serial.print("LAN connected - IP: ");
      Serial.println(ETH.localIP());
      debugPrint("LAN connected: " + ETH.localIP().toString());
      updateActiveTransport();
      fallbackStopRequested = true;
      break;

    case ARDUINO_EVENT_ETH_LOST_IP:
      Serial.println("LAN lost IP");
      lanConnected = false;
      lastWifiAttempt = 0;
      updateActiveTransport();
      break;

    case ARDUINO_EVENT_ETH_DISCONNECTED:
      Serial.println("LAN disconnected");
      lanConnected = false;
      lastWifiAttempt = 0;
      updateActiveTransport();
      break;

    case ARDUINO_EVENT_ETH_STOP:
      Serial.println("LAN stopped");
      lanConnected = false;
      ethernetStarted = false;
      lastWifiAttempt = 0;
      updateActiveTransport();
      break;

    case ARDUINO_EVENT_WIFI_STA_CONNECTED:
      Serial.println("WiFi fallback associated");
      break;

    case ARDUINO_EVENT_WIFI_STA_GOT_IP:
      fallbackWifiConnected = true;
      lastWifiAttempt = 0;
      Serial.print("WiFi fallback connected - IP: ");
      Serial.println(WiFi.localIP());
      debugPrint("WiFi fallback connected: " + WiFi.localIP().toString());
      updateActiveTransport();
      break;

    case ARDUINO_EVENT_WIFI_STA_LOST_IP:
      Serial.println("WiFi fallback lost IP");
      fallbackWifiConnected = false;
      updateActiveTransport();
      break;

    case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
      Serial.println("WiFi fallback disconnected");
      fallbackWifiConnected = false;
      fallbackWifiStarted = false;
      updateActiveTransport();
      break;

    default:
      break;
  }
}

static void registerNetworkEvents() {
  if (networkEventsRegistered) return;
  Network.begin();
  Network.onEvent(onNetworkEvent);
  networkEventsRegistered = true;
}

static void startEthernet() {
  if (ethernetStarted) return;

  registerNetworkEvents();
  debugPrint("Starting LAN Ethernet (W5500)");
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
  bool fallbackStartedForBoot = false;

  while (!isWiFiConnected() && (millis() - startedAt < NETWORK_CONNECT_TIMEOUT)) {
    unsigned long elapsed = millis() - startedAt;

    if (!fallbackStartedForBoot && elapsed >= LAN_PRIMARY_CONNECT_GRACE) {
      startFallbackWiFi();
      fallbackStartedForBoot = true;
    }

    delay(100);
  }

  if (isWiFiConnected()) {
    lastWifiAttempt = 0;
    Serial.print("Network ready via ");
    Serial.println(getActiveNetworkName());
    return true;
  }

  Serial.println("No LAN/WiFi network connected yet");
  debugPrint("No LAN/WiFi network connected yet");
  return false;
}

void reconnectWiFi() {
  unsigned long currentTime = millis();
  static int networkAttempts = 0;
  static unsigned long networkRetryInterval = NETWORK_RETRY_INTERVAL;

  if (!ethernetStarted) {
    startEthernet();
  }

  if (lanConnected) {
    if (fallbackStopRequested || fallbackWifiStarted || fallbackWifiConnected) {
      stopFallbackWiFi();
    }
    networkAttempts = 0;
    networkRetryInterval = NETWORK_RETRY_INTERVAL;
    updateActiveTransport();
    return;
  }

  if (fallbackWifiConnected) {
    networkAttempts = 0;
    networkRetryInterval = NETWORK_RETRY_INTERVAL;
    updateActiveTransport();
    return;
  }

  if (currentTime - lastWifiAttempt < networkRetryInterval) {
    return;
  }

  lastWifiAttempt = currentTime;
  networkAttempts++;
  debugPrint(
    "Network reconnect check " +
    String(networkAttempts) +
    "/" +
    String(MAX_NETWORK_ATTEMPTS)
  );

  startFallbackWiFi();
  networkRetryInterval = min(networkRetryInterval * 2, MAX_RETRY_INTERVAL);

  if (networkAttempts >= MAX_NETWORK_ATTEMPTS) {
    debugPrint("Max network reconnect checks reached - restarting ESP32");
    Serial.println("Restarting ESP32...");
    delay(1000);
    ESP.restart();
  }
}

bool isWiFiConnected() {
  updateActiveTransport();
  return wifiConnected;
}

bool isLanConnected() {
  return lanConnected;
}

bool isFallbackWifiConnected() {
  return fallbackWifiConnected;
}

NetworkTransport getActiveNetworkTransport() {
  updateActiveTransport();
  return activeTransport;
}

const char* getActiveNetworkName() {
  updateActiveTransport();
  return transportName(activeTransport);
}
