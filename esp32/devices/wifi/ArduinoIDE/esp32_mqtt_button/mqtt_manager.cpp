#include "mqtt_manager.h"
#include "config.h"
#include "debug.h"
#include "wifi_manager.h"

WiFiClient wifiClient;
PubSubClient client(wifiClient);
bool mqttConnected = false;
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusPublish = 0;
String STATUS_TOPIC;

// Callback nepotrebujeme, pretože nič nepočúvame, ale knižnica ho vyžaduje
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Prázdny callback
}

void initializeMqtt() {
  STATUS_TOPIC = "devices/" + String(CLIENT_ID) + "/status";
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setKeepAlive(MQTT_KEEP_ALIVE);
  client.setCallback(mqttCallback);
  debugPrint("MQTT initialized");
}

void publishSceneTrigger() {
  if (!isMqttConnected()) return;

  String topic = String(BASE_TOPIC_PREFIX) + String(SCENE_TOPIC_SUFFIX);
  // Výsledok: "room1/scene" -> "START"
  
  if (client.publish(topic.c_str(), SCENE_PAYLOAD, false)) {
    debugPrint(">>> SCENE TRIGGER SENT: " + topic + " -> " + String(SCENE_PAYLOAD));
  } else {
    debugPrint("!!! Failed to send scene trigger");
  }
}

void connectToMqtt() {
  if (!wifiConnected || !isWiFiConnected()) return;

  unsigned long currentTime = millis();
  static unsigned long mqttRetryInterval = MQTT_RETRY_INTERVAL;

  if (!client.connected() && (currentTime - lastMqttAttempt >= mqttRetryInterval)) {
    debugPrint("MQTT connecting...");
    
    // Last Will: "offline"
    if (client.connect(CLIENT_ID, STATUS_TOPIC.c_str(), 0, true, "offline")) {
      debugPrint("MQTT Connected!");
      mqttConnected = true;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;

      // Nepotrebujeme subscribe, lebo nič nepočúvame
      
      // Oznámime, že sme online
      client.publish(STATUS_TOPIC.c_str(), "online", true);

    } else {
      debugPrint("MQTT Failed rc=" + String(client.state()));
      mqttRetryInterval = min(mqttRetryInterval * 2, MAX_RETRY_INTERVAL);
    }
    lastMqttAttempt = currentTime;
  }
}

void mqttLoop() {
  if (!wifiConnected) return;
  client.loop(); // Udržiava spojenie (ping)

  // Pravidelný status update
  unsigned long currentTime = millis();
  if (currentTime - lastStatusPublish >= STATUS_PUBLISH_INTERVAL) {
    if (isMqttConnected()) {
      client.publish(STATUS_TOPIC.c_str(), "online", true);
    }
    lastStatusPublish = currentTime;
  }
}

bool isMqttConnected() {
  return mqttConnected && client.connected();
}