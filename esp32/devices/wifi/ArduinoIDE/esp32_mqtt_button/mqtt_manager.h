#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <PubSubClient.h>
#include <WiFi.h>

void initializeMqtt();
void connectToMqtt();
void mqttLoop();

// Odoslanie triggeru scény
void publishSceneTrigger();

// Status
void publishStatus();
bool isMqttConnected();

extern WiFiClient wifiClient;
extern PubSubClient client;
extern bool mqttConnected;

#endif