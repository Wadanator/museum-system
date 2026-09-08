#include "wifi_manager.h"
#include "config.h"
#include "debug.h"
#include <ETH.h>
#include <Network.h>
#include <SPI.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <atomic>

// Network state shared with the rest of the firmware.
// These values represent LAN or fallback WiFi availability.
bool wifiConnected = false;
unsigned long lastWifiAttempt = 0;

static bool networkEventsRegistered = false;
static std::atomic<bool> ethernetStarted{false};
static bool fallbackWifiStarted = false;
static std::atomic<bool> lanConnected{false};
static std::atomic<bool> lanChanged{false};
static std::atomic<bool> fallbackGotIp{false};
static bool fallbackWifiConnected = false;
static bool channelRestorePending = false;
static unsigned long fallbackStartedAt = 0;
static unsigned long channelRestoreAttempt = 0;
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
  } else if (fallbackWifiConnected && fallbackGotIp &&
             (!ESPNOW_ENABLED || WiFi.channel() == ESPNOW_CHANNEL)) {
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
  WiFi.setAutoReconnect(false);
  WiFi.disconnect(!ESPNOW_ENABLED, false);
  fallbackWifiStarted = false;
  fallbackWifiConnected = false;
  fallbackGotIp = false;
  channelRestorePending = ESPNOW_ENABLED;
  channelRestoreAttempt = millis();
  updateActiveTransport();
}

static void serviceFallbackWiFi() {
  const unsigned long now = millis();
  if (fallbackGotIp) {
    wifi_ap_record_t ap = {};
    if (esp_wifi_sta_get_ap_info(&ap) == ESP_OK) {
      if (!fallbackWifiStarted || lanConnected) {
        stopFallbackWiFi();
      } else if (ESPNOW_ENABLED && ap.primary != ESPNOW_CHANNEL) {
        Serial.printf("WiFi fallback rejected: AP channel %u, ESP-NOW channel %u. Fix the router channel.\n",
                      unsigned(ap.primary), unsigned(ESPNOW_CHANNEL));
        stopFallbackWiFi();
        lastWifiAttempt = now;
      } else if (!fallbackWifiConnected) {
        fallbackWifiConnected = true;
        Serial.print("WiFi fallback connected - IP: ");
        Serial.println(WiFi.localIP());
      }
    } else {
      fallbackGotIp = false;
    }
  } else if (fallbackWifiConnected) {
    Serial.println("WiFi fallback lost connection");
    stopFallbackWiFi();
    lastWifiAttempt = now;
  }

  // Bound an association/DHCP attempt, including the core's first automatic retry.
  if (fallbackWifiStarted && !fallbackWifiConnected &&
      now - fallbackStartedAt >= RELAY_WIFI_CONNECT_TIMEOUT_MS) {
    Serial.println("WiFi fallback connection timed out; retrying with backoff");
    stopFallbackWiFi();
    lastWifiAttempt = now;
  }

  // Channel changes must happen after disconnect, never during an association.
  if (channelRestorePending && !fallbackWifiStarted && now - channelRestoreAttempt >= 100) {
    channelRestoreAttempt = now;
    if (WiFi.status() == WL_CONNECTED) {
      WiFi.disconnect(false, false);
    } else if (esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE) == ESP_OK) {
      channelRestorePending = false;
    }
  }
}

static void startFallbackWiFi() {
  if (!RELAY_WIFI_FALLBACK_ENABLED) return;
  if (fallbackWifiStarted || fallbackWifiConnected || channelRestorePending) return;

  Serial.print("Starting WiFi fallback: ");
  Serial.println(WIFI_SSID);
  debugPrint("Starting WiFi fallback: " + String(WIFI_SSID));

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);
  WiFi.setSleep(false);
  WiFi.setHostname(OTA_HOSTNAME);
  fallbackStartedAt = millis();
  fallbackWifiStarted = true;
  // The channel argument is a search hint, not a lock: verify the AP on GOT_IP.
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, ESPNOW_ENABLED ? ESPNOW_CHANNEL : 0);
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
      lanChanged = true;
      Serial.print("LAN connected - IP: ");
      Serial.println(ETH.localIP());
      debugPrint("LAN connected: " + ETH.localIP().toString());
      break;

    case ARDUINO_EVENT_ETH_LOST_IP:
      Serial.println("LAN lost IP");
      lanConnected = false;
      lanChanged = true;
      break;

    case ARDUINO_EVENT_ETH_DISCONNECTED:
      Serial.println("LAN disconnected");
      lanConnected = false;
      lanChanged = true;
      break;

    case ARDUINO_EVENT_ETH_STOP:
      Serial.println("LAN stopped");
      lanConnected = false;
      ethernetStarted = false;
      lanChanged = true;
      break;

    case ARDUINO_EVENT_WIFI_STA_CONNECTED:
      Serial.println("WiFi fallback associated");
      break;

    case ARDUINO_EVENT_WIFI_STA_GOT_IP:
      fallbackGotIp = true;
      break;

    case ARDUINO_EVENT_WIFI_STA_LOST_IP:
      fallbackGotIp = false;
      break;

    case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
      fallbackGotIp = false;
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
    serviceFallbackWiFi();
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
  static int networkAttempts = 0;
  static unsigned long networkRetryInterval = NETWORK_RETRY_INTERVAL;
  serviceFallbackWiFi();
  const unsigned long currentTime = millis();
  if (lanChanged.exchange(false)) {
    networkAttempts = 0;
    networkRetryInterval = NETWORK_RETRY_INTERVAL;
    lastWifiAttempt = currentTime - networkRetryInterval;
  }

  if (!ethernetStarted) {
    startEthernet();
  }

  if (lanConnected) {
    if (fallbackWifiStarted || fallbackWifiConnected || fallbackGotIp) {
      Serial.println("LAN restored: stopping WiFi fallback, keeping ESP-NOW radio on");
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

  if (!RELAY_WIFI_FALLBACK_ENABLED || fallbackWifiStarted || channelRestorePending) {
    updateActiveTransport();
    return;
  }

  if (currentTime - lastWifiAttempt < networkRetryInterval) {
    return;
  }

  lastWifiAttempt = currentTime;
  if (networkAttempts < MAX_NETWORK_ATTEMPTS) ++networkAttempts;
  debugPrint(
    "Network reconnect check " +
    String(networkAttempts) +
    "/" +
    String(MAX_NETWORK_ATTEMPTS)
  );

  startFallbackWiFi();
  networkRetryInterval = min(networkRetryInterval * 2, MAX_RETRY_INTERVAL);

  if (!ESPNOW_ENABLED && networkAttempts >= MAX_NETWORK_ATTEMPTS) {
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
  return fallbackWifiConnected && fallbackGotIp;
}

bool isEspNowNetworkReady() {
  return !channelRestorePending && !(fallbackWifiStarted && !fallbackWifiConnected);
}

NetworkTransport getActiveNetworkTransport() {
  updateActiveTransport();
  return activeTransport;
}

const char* getActiveNetworkName() {
  updateActiveTransport();
  return transportName(activeTransport);
}
