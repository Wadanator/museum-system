#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <WiFi.h>

// WiFi management functions
bool initializeWiFi();
void reconnectWiFi();
bool isWiFiConnected();

// WiFi state
extern bool wifiConnected;
extern unsigned long lastWifiAttempt;

#endif