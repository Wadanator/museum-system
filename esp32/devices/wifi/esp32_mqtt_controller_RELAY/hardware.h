#ifndef HARDWARE_H
#define HARDWARE_H

#include <Arduino.h>

// Stav zariadení
extern bool deviceStates[];
extern bool allDevicesOff;

void initializeHardware();
void setDevice(int deviceIndex, bool state);
void turnOffAllDevices();
String getDeviceStatus();

#endif