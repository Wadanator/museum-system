#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <Arduino.h>

// Compatibility names retained so the rest of the firmware stays unchanged.
// In this LAN build they represent Ethernet/W5500 state, not WiFi state.
extern bool wifiConnected;
extern unsigned long lastWifiAttempt;

bool initializeWiFi();
void reconnectWiFi();
bool isWiFiConnected();

#endif
