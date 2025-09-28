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
  if (topicStr.endsWith("/status") || topicStr.endsWith("/feedback")) {
    debugPrint("Ignoring message on status/feedback topic: " + topicStr);
    return;
  }

  // Derive feedback topic (e.g., room1/motor -> room1/motor/feedback)
  String feedbackTopic = topicStr + "/feedback";
  bool commandSuccessful = false;
  
  if (topicStr.startsWith(basePrefix)) {
    String deviceType = topicStr.substring(basePrefix.length());

    if (deviceType.startsWith("motor")) {
      // Handle motor commands (e.g., room1/motor1, room1/motor2)
      String motorCommand = String(message);
      if (motorCommand == "ON" || motorCommand == "OFF" || motorCommand.startsWith("ON:") || motorCommand.startsWith("OFF:") || motorCommand.startsWith("DIR:")) {
        commandSuccessful = true;
        // In a real scenario, you would call a function to control the specific motor
        // For now, we assume success for valid commands
        debugPrint("Motor command processed successfully.");
      } else {
        debugPrint("ERROR: Unknown motor command: " + motorCommand);
      }
    } else if (deviceType.startsWith("light")) {
      // Handle light commands (e.g., room1/light)
      String lightCommand = String(message);
      if (lightCommand == "ON" || lightCommand == "OFF" || lightCommand.startsWith("ON:")) {
        commandSuccessful = true;
        debugPrint("Light command processed successfully.");
      } else {
        debugPrint("ERROR: Unknown light command: " + lightCommand);
      }
    } else {
      debugPrint("ERROR: Unknown device type: " + deviceType);
    }
  }

  // Publish feedback based on command success
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
        debugPrint("Max MQTT attempts reached. Restarting...");
        ESP.restart();
      }
      mqttRetryInterval = min(mqttRetryInterval * 2, MAX_RETRY_INTERVAL);
      mqttConnected = false;
    }

    lastMqttAttempt = currentTime;
  }
}

// Publish status immediately
void publishStatusImmediate() {
  if (client.connected()) {
    bool result = client.publish(STATUS_TOPIC.c_str(), "online", false);
    if (result) {
      client.loop();
      debugPrint("✅ Status published immediately: online");
    } else {
      debugPrint("❌ Failed to publish status");
    }
    lastStatusPublish = millis();
  }
}

// Publish status periodically
void publishStatus() {
  if (client.connected()) {
    unsigned long currentTime = millis();
    if (currentTime - lastStatusPublish >= STATUS_PUBLISH_INTERVAL) {
      publishStatusImmediate();
    }
  }
}

bool isMqttConnected() {
  return client.connected();
}

// Unused function - main loop calls client.loop() directly
void mqttLoop() {
  if (client.connected()) {
    client.loop();
    static unsigned long lastStatusCheck = 0;
    if (millis() - lastStatusCheck >= STATUS_PUBLISH_INTERVAL) {
      lastStatusCheck = millis();
      publishStatus();
    }
  } else {
    mqttConnected = false;
  }
}