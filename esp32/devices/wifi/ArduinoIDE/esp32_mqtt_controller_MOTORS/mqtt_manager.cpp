#include "mqtt_manager.h"
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"

// MQTT state is kept module-wide because PubSubClient owns the WiFi session.
WiFiClient wifiClient;
PubSubClient client(wifiClient);
bool mqttConnected = false;
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusPublish = 0;
unsigned long lastCommandTime = 0;
String STATUS_TOPIC = String("devices/") + CLIENT_ID + "/status";

static MotorState* motorStateFor(int motorNum) {
  if (motorNum == 1) return &motor1State;
  if (motorNum == 2) return &motor2State;
  return nullptr;
}

static const char* directionLabel(char direction) {
  if (direction == 'L') return "LEFT";
  if (direction == 'R') return "RIGHT";
  return "STOP";
}

void publishMotorState(int motorNum, const char* source, bool force) {
  (void)force;
  if (!mqttConnected || !client.connected()) return;

  MotorState* state = motorStateFor(motorNum);
  if (state == nullptr) return;

  bool pendingMotion = state->pendingDirectionChange && state->savedSpeed > 0;
  bool isOn = state->enabled && (
    state->speed > 0 ||
    state->targetSpeed > 0 ||
    pendingMotion
  );
  int speed = pendingMotion ? state->savedSpeed : max(state->speed, state->targetSpeed);
  if (!isOn) speed = 0;
  char direction = state->pendingDirectionChange ? state->newDirection : state->direction;

  char stateTopic[64];
  snprintf(stateTopic, sizeof(stateTopic), "%smotor%d/state", BASE_TOPIC_PREFIX, motorNum);

  char payload[192];
  snprintf(
    payload,
    sizeof(payload),
    "{\"state\":\"%s\",\"direction\":\"%s\",\"speed\":%d,\"node_id\":\"%s\",\"source\":\"%s\",\"ts_ms\":%lu}",
    isOn ? "ON" : "OFF",
    directionLabel(direction),
    speed,
    CLIENT_ID,
    source,
    millis()
  );

  if (client.publish(stateTopic, payload, true)) {
    debugPrint("Motor state: " + String(stateTopic) + " = " + String(payload));
  } else {
    debugPrint("Failed to publish motor state: " + String(stateTopic));
  }
}

void publishAllMotorStates(const char* source) {
  publishMotorState(1, source, true);
  publishMotorState(2, source, true);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {

  // Feedback, status and state topics are ignored to prevent command loops.
  if (strstr(topic, "/feedback") != nullptr ||
      strstr(topic, "/status") != nullptr ||
      strstr(topic, "/state") != nullptr) {
    debugPrint("Ignoring feedback/status/state topic");
    return;
  }

  // Reject payloads that cannot fit the bounded command buffer.
  if (length >= 64) {
    debugPrint("MQTT: Payload too long, ignoring");
    return;
  }

  char message[64];
  memcpy(message, payload, length);
  message[length] = '\0';

  if (DEBUG) {
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT topic: ");   Serial.println(topic);
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT message: "); Serial.println(message);
  }

  // Only room-scoped motor command topics are accepted.
  size_t prefixLen = strlen(BASE_TOPIC_PREFIX);
  if (strncmp(topic, BASE_TOPIC_PREFIX, prefixLen) != 0) {
    debugPrint("Ignoring out-of-prefix topic");
    return;
  }

  char feedbackTopic[128];
  snprintf(feedbackTopic, sizeof(feedbackTopic), "%s/feedback", topic);

  const char* deviceType = topic + prefixLen;

  bool commandSuccessful = false;

  // The room-level STOP command immediately disables both motor drivers.
  if (strcmp(deviceType, "STOP") == 0) {
    turnOffHardware();
    publishAllMotorStates("stop");
    commandSuccessful = true;
    debugPrint("STOP command executed");
  }

  // Motor commands use room-scoped topics room1/motor1 and room1/motor2.
  else if (strcmp(deviceType, "motor1") == 0 || strcmp(deviceType, "motor2") == 0) {

    int motorNum = (strcmp(deviceType, "motor1") == 0) ? 1 : 2;

    // ON accepts an optional command-defined ramp time.
    if (strncmp(message, "ON:", 3) == 0) {
      char speed[8]     = "50";
      char direction[4] = "L";
      char rampTime[16] = "0";

      char* p = message + 3;
      char* col1 = strchr(p, ':');

      if (col1 != nullptr) {
        size_t speedLen = col1 - p;
        if (speedLen > 0 && speedLen < sizeof(speed)) {
          memcpy(speed, p, speedLen);
          speed[speedLen] = '\0';
        }

        char* col2 = strchr(col1 + 1, ':');
        if (col2 != nullptr) {
          size_t dirLen = col2 - col1 - 1;
          if (dirLen > 0 && dirLen < sizeof(direction)) {
            memcpy(direction, col1 + 1, dirLen);
            direction[dirLen] = '\0';
          }
          strncpy(rampTime, col2 + 1, sizeof(rampTime) - 1);
          rampTime[sizeof(rampTime) - 1] = '\0';
        } else {
          strncpy(direction, col1 + 1, sizeof(direction) - 1);
          direction[sizeof(direction) - 1] = '\0';
        }

        if (motorNum == 1) controlMotor1("ON", speed, direction, rampTime);
        else               controlMotor2("ON", speed, direction, rampTime);
        publishMotorState(motorNum, "command", false);
        commandSuccessful = true;
      } else {
        debugPrint("ERROR: Malformed ON command - missing speed/direction");
      }
    }

    else if (strcmp(message, "OFF") == 0) {
      if (motorNum == 1) controlMotor1("OFF", "0", "S", "0");
      else               controlMotor2("OFF", "0", "S", "0");
      publishMotorState(motorNum, "command", false);
      commandSuccessful = true;
    }

    else if (strncmp(message, "SPEED:", 6) == 0) {
      const char* speedVal = message + 6;
      if (motorNum == 1) controlMotor1("SPEED", speedVal, "", "0");
      else               controlMotor2("SPEED", speedVal, "", "0");
      publishMotorState(motorNum, "command", false);
      commandSuccessful = true;
    }

    else if (strncmp(message, "DIR:", 4) == 0) {
      const char* dirVal = message + 4;
      if (motorNum == 1) controlMotor1("DIR", "", dirVal, "0");
      else               controlMotor2("DIR", "", dirVal, "0");
      publishMotorState(motorNum, "command", false);
      commandSuccessful = true;
    }

    else {
      debugPrint("ERROR: Unknown motor command");
    }
  }

  // Unknown room topics are ignored without feedback.
  else {
    debugPrint("Ignoring non-motor command");
    return;
  }

  const char* feedback = commandSuccessful ? "OK" : "ERROR";
  if (commandSuccessful) {
    // Successful commands refresh the inactivity safety window.
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

      publishAllMotorStates("reconnect");
      publishStatusImmediate();
      lastStatusPublish = 0;
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
