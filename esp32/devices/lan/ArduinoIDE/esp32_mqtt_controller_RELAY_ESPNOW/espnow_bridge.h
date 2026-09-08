#pragma once

#include <Arduino.h>
void initializeEspNowBridge();
void espNowBridgeLoop();
void subscribeEspNowMotorTopics();
bool routeEspNowMotorCommand(const char* topic, const uint8_t* payload, size_t length);
void stopEspNowMotors(bool feedback);
void suspendEspNowBridge();
