#ifndef OTA_MANAGER_H
#define OTA_MANAGER_H

// OTA funkcionalita
void initializeOTA();
void handleOTA();
bool isOTAInProgress();
void reinitializeOTAAfterWiFiReconnect();

// OTA stav
extern bool otaInProgress;
extern bool otaInitialized;

#endif