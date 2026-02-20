#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <PubSubClient.h>
#include <WiFi.h>

extern WiFiClient wifiClient;
extern PubSubClient client;
extern bool mqttConnected;
extern unsigned long lastCommandTime;

void initializeMqtt();
void connectToMqtt();
void mqttLoop();
void publishStatus();
bool isMqttConnected();

#endif