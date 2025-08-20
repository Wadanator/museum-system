#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <PubSubClient.h>
#include <WiFi.h>

// MQTT management functions
void initializeMqtt();
void connectToMqtt();
void publishStatus();
void mqttCallback(char* topic, byte* payload, unsigned int length);
bool isMqttConnected();
void mqttLoop();

// MQTT state
extern WiFiClient wifiClient;
extern PubSubClient client;
extern bool mqttConnected;
extern unsigned long lastMqttAttempt;
extern unsigned long lastStatusPublish;
extern String STATUS_TOPIC;

#endif