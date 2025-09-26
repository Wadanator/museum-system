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

  // Derive status topic for feedback (e.g., room1/motor1 -> room1/status)
  String statusTopic = basePrefix + "status";

  if (topicStr.startsWith(basePrefix)) {
    String deviceType = topicStr.substring(basePrefix.length());

    bool commandSuccessful = false;
    String feedbackMessage = "ERROR";

    // NOVÉ: STOP príkaz - vypne všetok hardware
    if (deviceType == "STOP") {
      debugPrint("STOP command received - turning off all hardware");
      turnOffHardware();
      commandSuccessful = true;
      feedbackMessage = "ALL_HARDWARE_STOPPED";
      
    } else {
      // Parse message for motor commands: "ON:50:L" or "SPEED:75" or "DIR:R" or "OFF"
      String command = String(message);
      String speed = "50";  // default speed
      String direction = "L"; // default direction
      
      // Parse compound commands like "ON:75:R"
      int firstColon = command.indexOf(':');
      int secondColon = command.indexOf(':', firstColon + 1);
      
      if (firstColon > 0) {
        String baseCommand = command.substring(0, firstColon);
        if (secondColon > 0) {
          speed = command.substring(firstColon + 1, secondColon);
          direction = command.substring(secondColon + 1);
        } else {
          speed = command.substring(firstColon + 1);
        }
        command = baseCommand;
      }

      if (deviceType == "motor1") {
        if (command == "ON" || command == "OFF" || command == "SPEED" || command == "DIR") {
          controlMotor1(command.c_str(), speed.c_str(), direction.c_str());
          commandSuccessful = true;
          feedbackMessage = "OK";
        } else {
          feedbackMessage = "ERROR: Unknown motor1 command: " + command;
        }
      } else if (deviceType == "motor2") {
        if (command == "ON" || command == "OFF" || command == "SPEED" || command == "DIR") {
          controlMotor2(command.c_str(), speed.c_str(), direction.c_str());
          commandSuccessful = true;
          feedbackMessage = "OK";
        } else {
          feedbackMessage = "ERROR: Unknown motor2 command: " + command;
        }
      } else {
        debugPrint("Unknown device in topic: " + deviceType);
        feedbackMessage = "ERROR: Unknown device: " + deviceType;
      }
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
    debugPrint("MQTT connecting...");
    String willTopic = "devices/" + String(CLIENT_ID) + "/status";
    
    if (client.connect(CLIENT_ID, willTopic.c_str(), 0, true, "offline")) {
      debugPrint("MQTT connected");
      mqttConnected = true;
      mqttAttempts = 0;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;
      
      // Subscribe to motor control topics AND STOP topic
      String basePrefix = String(BASE_TOPIC_PREFIX);
      client.subscribe((basePrefix + "motor1").c_str());
      client.subscribe((basePrefix + "motor2").c_str());
      client.subscribe((basePrefix + "STOP").c_str());  // NOVÉ: Subscribe na STOP
      
      debugPrint("Subscribed to motor and STOP MQTT topics");
      
      // Publish online status
      publishStatus();
    } else {
      mqttAttempts++;
      debugPrint("MQTT connection failed. Attempt: " + String(mqttAttempts));
      
      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Max MQTT attempts reached. Restarting...");
        ESP.restart();
      }
      
      mqttRetryInterval = min(mqttRetryInterval * 2, MAX_RETRY_INTERVAL);
      mqttConnected = false;
    }
    
    lastMqttAttempt = currentTime;
  }
}

void publishStatus() {
  if (client.connected()) {
    unsigned long currentTime = millis();
    if (currentTime - lastStatusPublish >= STATUS_PUBLISH_INTERVAL) {
      client.publish(STATUS_TOPIC.c_str(), "online", true);
      debugPrint("Status published: online");
      lastStatusPublish = currentTime;
    }
  }
}

bool isMqttConnected() {
  return client.connected();
}

void mqttLoop() {
  if (client.connected()) {
    client.loop();
    publishStatus();
  } else {
    mqttConnected = false;
  }
}