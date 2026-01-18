#ifndef OTA_MANAGER_H
#define OTA_MANAGER_H

// OTA management functions
void initializeOTA();
void handleOTA();
bool isOTAInProgress();
void reinitializeOTAAfterWiFiReconnect();

// OTA state
extern bool otaInProgress;
extern bool otaInitialized;

#endif // OTA_MANAGER_H