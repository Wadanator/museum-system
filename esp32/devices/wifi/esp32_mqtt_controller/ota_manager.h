#ifndef OTA_MANAGER_H
#define OTA_MANAGER_H

// Jednoduché OTA funkcie
void initializeOTA();
void handleOTA();

// OTA stav
extern bool otaInProgress;

#endif // OTA_MANAGER_H