#pragma once

#include <PubSubClient.h>
#include <NetworkClient.h>

extern NetworkClient networkClient;
extern PubSubClient client;
extern bool mqttConnected;
extern unsigned long lastCommandTime;

void initializeMqtt();
void connectToMqtt();
void mqttLoop();
void publishStatus();
void publishWindowState(int sideIndex, const char* source = "command", bool force = false);
void publishAllWindowStates(const char* source = "snapshot");
void publishWindowFeedback(int sideIndex, const char* feedback);
bool isMqttConnected();

