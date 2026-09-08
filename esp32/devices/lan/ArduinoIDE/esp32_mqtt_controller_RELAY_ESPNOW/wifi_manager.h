#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <Arduino.h>

enum NetworkTransport {
  NETWORK_NONE,
  NETWORK_LAN,
  NETWORK_WIFI
};

// Network state shared with the rest of the firmware.
// These values represent LAN or fallback WiFi availability.
extern bool wifiConnected;
extern unsigned long lastWifiAttempt;

bool initializeWiFi();
void reconnectWiFi();
bool isWiFiConnected();
bool isLanConnected();
bool isFallbackWifiConnected();
bool isEspNowNetworkReady();
NetworkTransport getActiveNetworkTransport();
const char* getActiveNetworkName();

#endif
