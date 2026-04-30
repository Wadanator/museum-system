#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <Arduino.h>

enum NetworkTransport {
  NETWORK_NONE,
  NETWORK_LAN,
  NETWORK_WIFI
};

// Compatibility names retained so the rest of the firmware stays unchanged.
// In this hybrid build they represent "some network is connected".
extern bool wifiConnected;
extern unsigned long lastWifiAttempt;

bool initializeWiFi();
void reconnectWiFi();
bool isWiFiConnected();
bool isLanConnected();
bool isFallbackWifiConnected();
NetworkTransport getActiveNetworkTransport();
const char* getActiveNetworkName();

#endif
