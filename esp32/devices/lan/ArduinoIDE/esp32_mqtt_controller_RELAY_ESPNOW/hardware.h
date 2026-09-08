#ifndef HARDWARE_H
#define HARDWARE_H

#include <Arduino.h>

// Relay state shared with MQTT, effects, and safety handling.
extern bool deviceStates[];
extern bool allDevicesOff;

extern bool effectControlled[];

void initializeHardware();
void setDevice(int deviceIndex, bool state);
void turnOffAllDevices();
void handleAutoOff();
String getDeviceStatus();

#endif
