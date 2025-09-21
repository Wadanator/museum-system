#include "mqtt_manager.h"
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"

// Global MQTT objects and state
WiFiClient wifiClient;
PubSubClient client(wifiClient);
bool mqttConnected = false;
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusPublish = 0;
String STATUS_TOPIC = String("devices/") + CLIENT_ID + "/status";

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  char message[length + 1];
  for (unsigned int i = 0; i < length; i++) {
    message[i] = (char)payload[i];
  }
  message[length] = '\0';

  debugPrint("MQTT topic: " + String(topic));
  debugPrint("MQTT message: " + String(message));

  String topicStr(topic);
  String basePrefix(BASE_TOPIC_PREFIX);

  // Ignore messages on status topic to prevent feedback loop
  if (topicStr.endsWith("/status")) {
    debugPrint("Ignoring message on status topic: " + topicStr);
    return;
  }

  // Derive status topic for feedback (e.g., room1/motor -> room1/status)
  String statusTopic = basePrefix + "status";

  if (topicStr.startsWith(basePrefix)) {
    String deviceType = topicStr.substring(basePrefix.length());

    bool commandSuccessful = false;
    String feedbackMessage = "ERROR";

    if (deviceType == "motor") {
      if (strcmp(message, "START") == 0 || strcmp(message, "STOP") == 0) {
        controlMotor(message);
        commandSuccessful = true;
        feedbackMessage = "OK";
      } else {
        feedbackMessage = "ERROR: Unknown motor command: " + String(message);
      }
    } else if (deviceType == "light") {
      if (strcmp(message, "ON") == 0 || strcmp(message, "OFF") == 0) {
        controlLight(message);
        commandSuccessful = true;
        feedbackMessage = "OK";
      } else {
        feedbackMessage = "ERROR: Unknown light command: " + String(message);
      }
    } else if (deviceType == "steam") {
      if (strcmp(message, "ON") == 0 || strcmp(message, "OFF") == 0) {
        controlSteam(message);
        commandSuccessful = true;
        feedbackMessage = "OK";
      } else {
        feedbackMessage = "ERROR: Unknown steam command: " + String(message);
      }
    } else {
      debugPrint("Unknown device in topic: " + deviceType);
      feedbackMessage = "ERROR: Unknown device: " + deviceType;
    }

    // Always publish feedback to status topic
    if (client.connected()) {
      client.publish(statusTopic.c_str(), feedbackMessage.c_str(), true);
      debugPrint("Published feedback to " + statusTopic + ": " + feedbackMessage);
    } else {
      debugPrint("Failed to publish feedback: MQTT not connected");
    }
  } else {
    debugPrint("Unknown topic prefix");
    // Publish error feedback to status topic
    if (client.connected()) {
      String errorMessage = "ERROR: Unknown topic prefix: " + topicStr;
      client.publish(statusTopic.c_str(), errorMessage.c_str(), true);
      debugPrint("Published feedback to " + statusTopic + ": " + errorMessage);
    } else {
      debugPrint("Failed to publish feedback: MQTT not connected");
    }
  }
}

void initializeMqtt() {
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setKeepAlive(MQTT_KEEP_ALIVE);
  client.setCallback(mqttCallback);
  debugPrint("MQTT configured");
}

void connectToMqtt() {
  if (!wifiConnected || !isWiFiConnected()) return;

  unsigned long currentTime = millis();
  static int mqttAttempts = 0;
  static unsigned long mqttRetryInterval = MQTT_RETRY_INTERVAL;

  if (!client.connected() && (currentTime - lastMqttAttempt >= mqttRetryInterval)) {
    debugPrint("MQTT connect attempt " + String(mqttAttempts + 1) + "/" + String(MAX_MQTT_ATTEMPTS));
    lastMqttAttempt = currentTime;
    mqttAttempts++;

    // IMPROVED: Set Last Will Testament to notify when device goes offline unexpectedly
    if (client.connect(CLIENT_ID, NULL, NULL, STATUS_TOPIC.c_str(), 0, true, "offline")) {
      Serial.println("MQTT connected");
      debugPrint("MQTT connected successfully");
      mqttConnected = true;
      mqttAttempts = 0;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;

      String topicFilter = String(BASE_TOPIC_PREFIX) + "#";
      client.subscribe(topicFilter.c_str());
      debugPrint("Subscribed to: " + topicFilter);

      client.publish(STATUS_TOPIC.c_str(), "online", true);
      debugPrint("Published status: online to " + STATUS_TOPIC);
      lastStatusPublish = currentTime;
      hardwareOff = false; // Reset hardware state on successful connection
    } else {
      mqttRetryInterval = min(mqttRetryInterval * 2, MAX_RETRY_INTERVAL);
      mqttConnected = false;
      debugPrint("MQTT failed - error: " + String(client.state()));

      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Max MQTT attempts - restarting");
        ESP.restart();
      }
    }
  }
}

void publishStatus() {
  unsigned long currentTime = millis();
  // IMPROVED: Send status more frequently (every 30 seconds)
  if (mqttConnected && client.connected() && (currentTime - lastStatusPublish >= 30000)) {
    client.publish(STATUS_TOPIC.c_str(), "online", true);
    debugPrint("Published status: online to " + STATUS_TOPIC);
    lastStatusPublish = currentTime;
  }
}

bool isMqttConnected() {
  return mqttConnected && client.connected();
}

void mqttLoop() {
  if (isMqttConnected()) {
    client.loop();
    publishStatus();
  }
}