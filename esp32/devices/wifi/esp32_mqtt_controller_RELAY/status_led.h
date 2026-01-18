#ifndef STATUS_LED_H
#define STATUS_LED_H

// Inicializácia LED (len ak je povolená)
void initializeStatusLed();

// Hlavná slučka pre blikanie podľa stavu WiFi/MQTT
void handleStatusLed(bool wifiOk, bool mqttOk);

// Nastavenie farby počas OTA update
void setOtaLedState(bool active);

#endif