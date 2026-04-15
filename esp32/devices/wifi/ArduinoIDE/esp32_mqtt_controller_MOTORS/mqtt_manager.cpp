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
unsigned long lastCommandTime = 0;
String STATUS_TOPIC = String("devices/") + CLIENT_ID + "/status";

void mqttCallback(char* topic, byte* payload, unsigned int length) {

  // --- Guard: message size limit ---
  if (length >= 64) {
    debugPrint("MQTT: Payload too long, ignoring");
    return;
  }

  // Stack-allocated message buffer – no heap
  char message[64];
  memcpy(message, payload, length);
  message[length] = '\0';

  // Use Serial directly here – topic and message are already char*, no String needed
  if (DEBUG) {
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT topic: ");   Serial.println(topic);
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT message: "); Serial.println(message);
  }

  // --- Ignore feedback / status topics to prevent loops ---
  if (strstr(topic, "/feedback") != nullptr || strstr(topic, "/status") != nullptr) {
    debugPrint("Ignoring feedback/status topic");
    return;
  }

  // --- Verify topic starts with BASE_TOPIC_PREFIX ---
  size_t prefixLen = strlen(BASE_TOPIC_PREFIX);
  if (strncmp(topic, BASE_TOPIC_PREFIX, prefixLen) != 0) {
    debugPrint("Ignoring out-of-prefix topic");
    return;
  }

  // feedbackTopic = topic + "/feedback" – stack only
  char feedbackTopic[128];
  snprintf(feedbackTopic, sizeof(feedbackTopic), "%s/feedback", topic);

  // deviceType = everything after the prefix  e.g. "motor1", "STOP"
  const char* deviceType = topic + prefixLen;

  bool commandSuccessful = false;

  // -------------------------------------------------------------------------
  // STOP
  // -------------------------------------------------------------------------
  if (strcmp(deviceType, "STOP") == 0) {
    turnOffHardware();
    commandSuccessful = true;
    debugPrint("STOP command executed");
  }

  // -------------------------------------------------------------------------
  // motor1 / motor2
  // -------------------------------------------------------------------------
  else if (strcmp(deviceType, "motor1") == 0 || strcmp(deviceType, "motor2") == 0) {

    int motorNum = (strcmp(deviceType, "motor1") == 0) ? 1 : 2;

    // --- ON:<speed>:<direction>[:<rampTime>] ---
    if (strncmp(message, "ON:", 3) == 0) {
      char speed[8]     = "50";
      char direction[4] = "L";
      char rampTime[16] = "0";

      // p points to first digit of speed
      char* p = message + 3;
      char* col1 = strchr(p, ':');

      if (col1 != nullptr) {
        // Extract speed
        size_t speedLen = col1 - p;
        if (speedLen > 0 && speedLen < sizeof(speed)) {
          memcpy(speed, p, speedLen);
          speed[speedLen] = '\0';
        }

        char* col2 = strchr(col1 + 1, ':');
        if (col2 != nullptr) {
          // Format with rampTime: ON:<speed>:<dir>:<ramp>
          size_t dirLen = col2 - col1 - 1;
          if (dirLen > 0 && dirLen < sizeof(direction)) {
            memcpy(direction, col1 + 1, dirLen);
            direction[dirLen] = '\0';
          }
          strncpy(rampTime, col2 + 1, sizeof(rampTime) - 1);
          rampTime[sizeof(rampTime) - 1] = '\0';
        } else {
          // Format without rampTime: ON:<speed>:<dir>
          strncpy(direction, col1 + 1, sizeof(direction) - 1);
          direction[sizeof(direction) - 1] = '\0';
        }

        if (motorNum == 1) controlMotor1("ON", speed, direction, rampTime);
        else               controlMotor2("ON", speed, direction, rampTime);
        commandSuccessful = true;
      } else {
        debugPrint("ERROR: Malformed ON command – missing speed/direction");
      }
    }

    // --- OFF ---
    else if (strcmp(message, "OFF") == 0) {
      if (motorNum == 1) controlMotor1("OFF", "0", "S", "0");
      else               controlMotor2("OFF", "0", "S", "0");
      commandSuccessful = true;
    }

    // --- SPEED:<value> ---
    else if (strncmp(message, "SPEED:", 6) == 0) {
      const char* speedVal = message + 6;
      if (motorNum == 1) controlMotor1("SPEED", speedVal, "", "0");
      else               controlMotor2("SPEED", speedVal, "", "0");
      commandSuccessful = true;
    }

    // --- DIR:<value> ---
    else if (strncmp(message, "DIR:", 4) == 0) {
      const char* dirVal = message + 4;
      if (motorNum == 1) controlMotor1("DIR", "", dirVal, "0");
      else               controlMotor2("DIR", "", dirVal, "0");
      commandSuccessful = true;
    }

    else {
      debugPrint("ERROR: Unknown motor command");
    }
  }

  // -------------------------------------------------------------------------
  // Unknown device – silently ignore, no feedback
  // -------------------------------------------------------------------------
  else {
    debugPrint("Ignoring non-motor command");
    return;
  }

  // --- Publish feedback (stack string, no heap) ---
  const char* feedback = commandSuccessful ? "OK" : "ERROR";
  if (commandSuccessful) {
    lastCommandTime = millis();
  }
  if (client.publish(feedbackTopic, feedback, false)) {
    debugPrint("Feedback: " + String(feedback) + " -> " + String(feedbackTopic));
  } else {
    debugPrint("Failed to publish feedback");
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
      debugPrint("MQTT connected successfully");
      mqttConnected = true;
      mqttAttempts = 0;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;

      String basePrefix = String(BASE_TOPIC_PREFIX);
      client.subscribe((basePrefix + "motor1").c_str(), 0);
      client.subscribe((basePrefix + "motor2").c_str(), 0);
      client.subscribe((basePrefix + "STOP").c_str(), 0);
      debugPrint("Subscribed to motor topics");

      publishStatusImmediate();
      lastCommandTime = currentTime;

    } else {
      mqttAttempts++;
      debugPrint("MQTT connection failed. Attempt: " + String(mqttAttempts));

      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Max MQTT attempts reached. Restarting...");
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