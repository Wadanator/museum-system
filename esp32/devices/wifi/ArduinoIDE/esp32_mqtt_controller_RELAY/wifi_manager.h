#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <WiFi.h>

extern bool wifiConnected;
extern unsigned long lastWifiAttempt;

bool initializeWiFi();
void reconnectWiFi();
bool isWiFiConnected();

#endif