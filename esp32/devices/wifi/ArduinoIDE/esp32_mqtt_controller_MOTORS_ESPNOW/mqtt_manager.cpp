#include "mqtt_manager.h"
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "motor_commands.h"

// MQTT state is kept module-wide because PubSubClient owns the WiFi session.
WiFiClient wifiClient;
PubSubClient client(wifiClient);
bool mqttConnected = false;
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusPublish = 0;
String STATUS_TOPIC = String("devices/") + CLIENT_ID + "/status";
static int mqttAttempts = 0;
static unsigned long mqttRetryInterval = 0;

static void resetMqttRetryState() {
  mqttAttempts = 0;
  mqttRetryInterval = MQTT_RETRY_INTERVAL;
}

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
  speed = constrain(speed, 0, 100);
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
  if (!MOTOR_DIRECT_MQTT_COMMANDS_ENABLED) return;
  const size_t prefixLen = strlen(BASE_TOPIC_PREFIX);
  if (strncmp(topic, BASE_TOPIC_PREFIX, prefixLen) != 0) return;
  const char* name = topic + prefixLen;
  museum::Target target;
  if (!strcmp(name, "motor1")) target = museum::Target::Motor1;
  else if (!strcmp(name, "motor2")) target = museum::Target::Motor2;
  else if (!strcmp(name, "STOP")) target = museum::Target::All;
  else return;

  bool ok = false;
  if (target == museum::Target::All) {
    // Preserve the legacy room STOP topic semantics for any payload.
    ok = executeMotorCommand(target, "STOP");
  } else if (length > 0 && length < museum::PayloadSize && !memchr(payload, 0, length)) {
    char command[museum::PayloadSize];
    memcpy(command, payload, length); command[length] = 0;
    ok = executeMotorCommand(target, command);
  }
  if (ok) {
    if (target == museum::Target::All) publishAllMotorStates("stop");
    else publishMotorState(int(target), "command", true);
  }
  char feedbackTopic[128];
  snprintf(feedbackTopic, sizeof(feedbackTopic), "%s/feedback", topic);
  client.publish(feedbackTopic, ok ? "OK" : "ERROR", false);
}


void initializeMqtt() {
  if (!MOTOR_DIRECT_MQTT_COMMANDS_ENABLED) return;
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setKeepAlive(MQTT_KEEP_ALIVE);
  client.setCallback(mqttCallback);
  debugPrint("MQTT configured");
}

void connectToMqtt() {
  if (!MOTOR_DIRECT_MQTT_COMMANDS_ENABLED) return;
  if (!wifiConnected || !isWiFiConnected()) {
    mqttConnected = false;
    resetMqttRetryState();
    return;
  }

  unsigned long currentTime = millis();
  if (mqttRetryInterval == 0) {
    mqttRetryInterval = MQTT_RETRY_INTERVAL;
  }

  if (!client.connected() && (currentTime - lastMqttAttempt >= mqttRetryInterval)) {
    debugPrint("MQTT connecting...");
    String willTopic = "devices/" + String(CLIENT_ID) + "/status";

    if (client.connect(CLIENT_ID, willTopic.c_str(), 0, true, "offline")) {
      debugPrint("MQTT connected successfully");
      mqttConnected = true;
      resetMqttRetryState();

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
