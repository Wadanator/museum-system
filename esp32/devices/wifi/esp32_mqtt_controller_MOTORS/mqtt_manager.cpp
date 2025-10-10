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

  // Ignore feedback topics to prevent loops
  if (topicStr.endsWith("/feedback") || topicStr.endsWith("/status")) {
    debugPrint("Ignoring feedback/status topic: " + topicStr);
    return;
  }

  String feedbackTopic = topicStr + "/feedback";
  bool commandSuccessful = false;
  
  if (topicStr.startsWith(basePrefix)) {
    String deviceType = topicStr.substring(basePrefix.length());

    // Handle STOP command
    if (deviceType == "STOP") {
      turnOffHardware();
      commandSuccessful = true;
      debugPrint("STOP command executed");
    }
    // Handle motor commands
    else if (deviceType == "motor1" || deviceType == "motor2") {
      String motorCommand = String(message);
      
      // Parse command: ON:50:L or OFF or SPEED:50 or DIR:L
      if (motorCommand.startsWith("ON:")) {
        int firstColon = motorCommand.indexOf(':');
        int secondColon = motorCommand.indexOf(':', firstColon + 1);
        
        if (firstColon > 0 && secondColon > firstColon) {
          String speed = motorCommand.substring(firstColon + 1, secondColon);
          String direction = motorCommand.substring(secondColon + 1);
          
          if (deviceType == "motor1") {
            controlMotor1("ON", speed.c_str(), direction.c_str());
          } else {
            controlMotor2("ON", speed.c_str(), direction.c_str());
          }
          commandSuccessful = true;
        }
      }
      else if (motorCommand == "OFF") {
        if (deviceType == "motor1") {
          controlMotor1("OFF", "0", "S");
        } else {
          controlMotor2("OFF", "0", "S");
        }
        commandSuccessful = true;
      }
      else if (motorCommand.startsWith("SPEED:")) {
        String speed = motorCommand.substring(6);
        if (deviceType == "motor1") {
          controlMotor1("SPEED", speed.c_str(), "");
        } else {
          controlMotor2("SPEED", speed.c_str(), "");
        }
        commandSuccessful = true;
      }
      else if (motorCommand.startsWith("DIR:")) {
        String direction = motorCommand.substring(4);
        if (deviceType == "motor1") {
          controlMotor1("DIR", "", direction.c_str());
        } else {
          controlMotor2("DIR", "", direction.c_str());
        }
        commandSuccessful = true;
      }
      else {
        debugPrint("ERROR: Unknown motor command: " + motorCommand);
      }
    } else {
      debugPrint("Ignoring non-motor command: " + deviceType);
      return;
    }
  }

  // Send feedback
  if (commandSuccessful) {
    if (client.publish(feedbackTopic.c_str(), "OK", false)) {
      debugPrint("Published feedback: OK to " + feedbackTopic);
    } else {
      debugPrint("Failed to publish feedback: " + feedbackTopic);
    }
  } else {
    if (client.publish(feedbackTopic.c_str(), "ERROR", false)) {
      debugPrint("Published feedback: ERROR to " + feedbackTopic);
    } else {
      debugPrint("Failed to publish feedback: " + feedbackTopic);
    }
  }
}


void initializeMqtt() {
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setKeepAlive(MQTT_KEEP_ALIVE);
  client.setCallback(mqttCallback);
  debugPrint("MQTT configured with optimized settings");
}

void connectToMqtt() {
  if (!wifiConnected || !isWiFiConnected()) return;

  unsigned long currentTime = millis();
  static int mqttAttempts = 0;
  static unsigned long mqttRetryInterval = MQTT_RETRY_INTERVAL;

  if (!client.connected() && (currentTime - lastMqttAttempt >= mqttRetryInterval)) {
    debugPrint("MQTT connecting with optimized settings...");
    String willTopic = "devices/" + String(CLIENT_ID) + "/status";

    // Connect with a will message
    if (client.connect(CLIENT_ID, willTopic.c_str(), 0, true, "offline")) {
      debugPrint("MQTT connected successfully");
      mqttConnected = true;
      mqttAttempts = 0;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;

      // Subscribe to motor control topics with QoS 0 for fastest delivery
      String basePrefix = String(BASE_TOPIC_PREFIX);
      client.subscribe((basePrefix + "motor1").c_str(), 0);
      client.subscribe((basePrefix + "motor2").c_str(), 0);
      client.subscribe((basePrefix + "STOP").c_str(), 0);

      debugPrint("Subscribed to motor topics with QoS 0");

      // Publish online status immediately
      publishStatusImmediate();

    } else {
      mqttAttempts++;
      debugPrint("MQTT connection failed. Attempt: " + String(mqttAttempts));

      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Max MQTT attempts reached. Restarting ESP32...");
        ESP.restart();
      } else {
        mqttRetryInterval = min(mqttRetryInterval * 2, MAX_RETRY_INTERVAL);
      }
    }
    
    lastMqttAttempt = currentTime;
  }
}

void mqttLoop() {
  if (!wifiConnected) return;

  client.loop();
  
  static unsigned long lastStatusTime = 0;
  unsigned long currentTime = millis();
  
  if (currentTime - lastStatusTime >= STATUS_PUBLISH_INTERVAL) {
    publishStatus();
    lastStatusTime = currentTime;
  }
}

void publishStatus() {
  if (!mqttConnected || !client.connected()) return;

  unsigned long currentTime = millis();
  if (currentTime - lastStatusPublish < STATUS_PUBLISH_INTERVAL) return;

  if (client.publish(STATUS_TOPIC.c_str(), "online", true)) {
    debugPrint("Status published: online");
    lastStatusPublish = currentTime;
  } else {
    debugPrint("Failed to publish status");
  }
}

void publishStatusImmediate() {
  if (client.publish(STATUS_TOPIC.c_str(), "online", true)) {
    debugPrint("Immediate status published: online");
    lastStatusPublish = millis();
  } else {
    debugPrint("Failed to publish immediate status");
  }
}

bool isMqttConnected() {
  return mqttConnected && client.connected();
}