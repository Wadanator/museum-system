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
void publishCoverState(int coverIndex, const char* source = "command", bool force = false);
void publishAllCoverStates(const char* source = "snapshot");
void publishCoverFeedback(int coverIndex, const char* feedback);
bool isMqttConnected();

#endif
