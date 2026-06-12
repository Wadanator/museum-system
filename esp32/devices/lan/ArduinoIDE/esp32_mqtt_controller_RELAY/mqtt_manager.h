#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

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
void publishDeviceState(int deviceIndex, const char* source = "command", bool force = false);
void publishAllDeviceStates(const char* source = "snapshot");
void publishEffectState(const char* groupName, const char* state, const char* source = "effect", bool force = false);
void publishAllEffectStates(const char* source = "snapshot");
bool isMqttConnected();

#endif
