#ifndef STATUS_LED_H
#define STATUS_LED_H

#include <Arduino.h>

void initializeStatusLed();
void handleStatusLed(bool wifiOk, bool mqttOk);
void setOtaLedState(bool active);

#endif