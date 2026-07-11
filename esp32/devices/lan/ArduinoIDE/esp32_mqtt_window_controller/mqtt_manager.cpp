#include "mqtt_manager.h"
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include <ctype.h>
#include <string.h>
#include <stdio.h>

NetworkClient networkClient;
PubSubClient client(networkClient);
bool mqttConnected = false;
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusPublish = 0;
String STATUS_TOPIC = String("devices/") + CLIENT_ID + "/status";
NetworkTransport mqttTransport = NETWORK_NONE;

unsigned long lastCommandTime = 0;
static WindowState lastPublishedWindowStates[8];
static int lastPublishedWindowSpeeds[8] = {-1, -1, -1, -1, -1, -1, -1, -1};
static bool lastPublishedWindowStateValid[8] = {false};
static int mqttAttempts = 0;
static unsigned long mqttRetryInterval = 0;

static void resetMqttRetryState() {
  mqttAttempts = 0;
  mqttRetryInterval = MQTT_RETRY_INTERVAL;
}

static bool isValidWindowSideIndex(int sideIndex) {
  return sideIndex >= 0 && sideIndex < WINDOW_SIDE_COUNT && sideIndex < 8 &&
         WINDOW_SIDES[sideIndex].enabled;
}

void publishWindowState(int sideIndex, const char* source, bool force) {
  if (!mqttConnected || !client.connected()) return;
  if (!isValidWindowSideIndex(sideIndex)) return;

  WindowState state = getWindowState(sideIndex);
  int speed = getWindowSpeed(sideIndex);
  if (!force && lastPublishedWindowStateValid[sideIndex] &&
      lastPublishedWindowStates[sideIndex] == state &&
      lastPublishedWindowSpeeds[sideIndex] == speed) {
    return;
  }

  char stateTopic[96];
  snprintf(stateTopic, sizeof(stateTopic), "%s%s/state", BASE_TOPIC_PREFIX, WINDOW_SIDES[sideIndex].topicName);

  char payload[192];
  snprintf(
    payload,
    sizeof(payload),
    "{\"state\":\"%s\",\"direction\":\"%s\",\"speed\":%d,\"node_id\":\"%s\",\"source\":\"%s\",\"ts_ms\":%lu}",
    getWindowStateText(sideIndex),
    getWindowDirectionText(sideIndex),
    speed,
    CLIENT_ID,
    source,
    millis()
  );

  if (client.publish(stateTopic, payload, true)) {
    lastPublishedWindowStates[sideIndex] = state;
    lastPublishedWindowSpeeds[sideIndex] = speed;
    lastPublishedWindowStateValid[sideIndex] = true;
    debugPrint("State: " + String(stateTopic) + " = " + String(payload));
  } else {
    debugPrint("Failed to publish state: " + String(stateTopic));
  }
}

void publishAllWindowStates(const char* source) {
  for (int i = 0; i < WINDOW_SIDE_COUNT && i < 8; i++) {
    publishWindowState(i, source, true);
  }
}

void publishWindowFeedback(int sideIndex, const char* feedback) {
  if (!mqttConnected || !client.connected()) return;
  if (!isValidWindowSideIndex(sideIndex) || feedback == nullptr) return;

  char feedbackTopic[96];
  snprintf(feedbackTopic, sizeof(feedbackTopic), "%s%s/feedback", BASE_TOPIC_PREFIX, WINDOW_SIDES[sideIndex].topicName);

  if (client.publish(feedbackTopic, feedback, false)) {
    debugPrint("Feedback: " + String(feedback) + " -> " + String(feedbackTopic));
  }
}

static const char* mqttTransportName(NetworkTransport transport) {
  switch (transport) {
    case NETWORK_LAN:
      return "LAN";
    case NETWORK_WIFI:
      return "WiFi fallback";
    default:
      return "none";
  }
}

static void handleNetworkTransportChange() {
  NetworkTransport activeTransport = getActiveNetworkTransport();
  if (activeTransport == mqttTransport) return;

  debugPrint(
    "MQTT transport switch: " +
    String(mqttTransportName(mqttTransport)) +
    " -> " +
    String(mqttTransportName(activeTransport))
  );

  if (client.connected()) {
    client.disconnect();
  }

  mqttConnected = false;
  mqttTransport = activeTransport;
  lastMqttAttempt = 0;
  resetMqttRetryState();
}

static int findWindowSideByTopicName(const char* deviceName) {
  for (int i = 0; i < WINDOW_SIDE_COUNT && i < 8; i++) {
    if (!WINDOW_SIDES[i].enabled) continue;
    if (strcmp(WINDOW_SIDES[i].topicName, deviceName) == 0) return i;
  }
  return -1;
}

static void uppercaseInPlace(char* value) {
  for (int i = 0; value[i]; i++) {
    value[i] = (char)toupper((unsigned char)value[i]);
  }
}

static void trimAsciiInPlace(char* value) {
  char* start = value;
  while (*start && isspace((unsigned char)*start)) start++;

  char* end = start + strlen(start);
  while (end > start && isspace((unsigned char)*(end - 1))) end--;
  *end = '\0';

  if (start != value) {
    memmove(value, start, strlen(start) + 1);
  }
}

static bool commandHasOptionalValue(const char* message, const char* command, const char** value) {
  size_t len = strlen(command);
  if (strncmp(message, command, len) != 0) return false;
  if (message[len] == '\0') {
    *value = nullptr;
    return true;
  }
  if (message[len] == ':') {
    *value = message + len + 1;
    return true;
  }
  return false;
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  if (strstr(topic, "/feedback") != nullptr ||
      strstr(topic, "/status") != nullptr ||
      strstr(topic, "/state") != nullptr) {
    return;
  }

  if (length >= 64) {
    debugPrint("MQTT: Payload too long, ignoring");
    return;
  }

  char message[64];
  memcpy(message, payload, length);
  message[length] = '\0';
  trimAsciiInPlace(message);
  uppercaseInPlace(message);

  if (DEBUG) {
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT topic: "); Serial.println(topic);
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT message: "); Serial.println(message);
  }

  size_t prefixLen = strlen(BASE_TOPIC_PREFIX);
  if (strncmp(topic, BASE_TOPIC_PREFIX, prefixLen) != 0) {
    return;
  }

  const char* deviceName = topic + prefixLen;

  char feedbackTopic[128];
  snprintf(feedbackTopic, sizeof(feedbackTopic), "%s/feedback", topic);

  const char* feedback = "ERROR";

  if (strcmp(deviceName, "STOP") == 0 || strcmp(deviceName, "window/STOP") == 0) {
    stopAllWindows("room_stop");
    publishAllWindowStates("room_stop");
    for (int i = 0; i < WINDOW_SIDE_COUNT && i < 8; i++) {
      if (!WINDOW_SIDES[i].enabled) continue;
      publishWindowFeedback(i, getWindowState(i) == WINDOW_STATE_ERROR ? "ERROR:HARDWARE" : "OK");
    }
    feedback = "OK";
    debugPrint("Global STOP command executed for all windows");
  } else {
    int sideIndex = findWindowSideByTopicName(deviceName);
    if (sideIndex >= 0) {
      const char* speedValue = nullptr;
      if (commandHasOptionalValue(message, "OPEN", &speedValue)) {
        feedback = commandWindowOpen(sideIndex, speedValue);
      } else if (commandHasOptionalValue(message, "CLOSE", &speedValue)) {
        feedback = commandWindowClose(sideIndex, speedValue);
      } else if (strcmp(message, "STOP") == 0 || strcmp(message, "OFF") == 0) {
        feedback = commandWindowStop(sideIndex);
      } else if (strncmp(message, "SPEED:", 6) == 0) {
        feedback = commandWindowSpeed(sideIndex, message + 6);
      } else {
        debugPrint("Unknown window command: " + String(message));
      }
    } else {
      debugPrint("Unknown window topic: " + String(deviceName));
      return;
    }
  }

  if (strcmp(feedback, "OK") == 0) {
    lastCommandTime = millis();
  }

  if (client.publish(feedbackTopic, feedback, false)) {
    debugPrint("Feedback: " + String(feedback) + " -> " + String(feedbackTopic));
  }
}

void initializeMqtt() {
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setKeepAlive(MQTT_KEEP_ALIVE);
  client.setCallback(mqttCallback);
  debugPrint("MQTT configured: " + String(MQTT_SERVER) + ":" + String(MQTT_PORT));
}

void connectToMqtt() {
  if (!wifiConnected || !isWiFiConnected()) {
    mqttConnected = false;
    resetMqttRetryState();
    return;
  }

  handleNetworkTransportChange();

  unsigned long currentTime = millis();
  if (mqttRetryInterval == 0) {
    mqttRetryInterval = MQTT_RETRY_INTERVAL;
  }

  if (!client.connected() && (currentTime - lastMqttAttempt >= mqttRetryInterval)) {
    debugPrint("Connecting to MQTT broker...");
    String willTopic = "devices/" + String(CLIENT_ID) + "/status";

    if (client.connect(CLIENT_ID, willTopic.c_str(), 0, true, "offline")) {
      Serial.println("MQTT connected");
      debugPrint("MQTT connected successfully");
      mqttConnected = true;
      resetMqttRetryState();

      for (int i = 0; i < WINDOW_SIDE_COUNT && i < 8; i++) {
        if (!WINDOW_SIDES[i].enabled) continue;
        char topicBuf[64];
        snprintf(topicBuf, sizeof(topicBuf), "%s%s", BASE_TOPIC_PREFIX, WINDOW_SIDES[i].topicName);
        client.subscribe(topicBuf, 0);
        debugPrint("Subscribed: " + String(topicBuf));
      }

      char windowStopTopic[64];
      snprintf(windowStopTopic, sizeof(windowStopTopic), "%swindow/STOP", BASE_TOPIC_PREFIX);
      client.subscribe(windowStopTopic, 0);
      debugPrint("Subscribed: " + String(windowStopTopic));

      char stopTopic[64];
      snprintf(stopTopic, sizeof(stopTopic), "%sSTOP", BASE_TOPIC_PREFIX);
      client.subscribe(stopTopic, 0);
      debugPrint("Subscribed: " + String(stopTopic));

      publishAllWindowStates("reconnect");
      if (client.publish(STATUS_TOPIC.c_str(), "online", true)) {
        debugPrint("Status: online");
      }

      lastStatusPublish = 0;
      lastCommandTime = currentTime;
    } else {
      mqttAttempts++;
      Serial.println("MQTT connection failed. Attempt: " + String(mqttAttempts));
      debugPrint("MQTT connection failed. RC=" + String(client.state()));

      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Maximum MQTT retry count reached - restarting");
        delay(1000);
        ESP.restart();
      } else {
        mqttRetryInterval = min(mqttRetryInterval * 2, MAX_RETRY_INTERVAL);
      }
    }

    lastMqttAttempt = currentTime;
  }
}

void mqttLoop() {
  if (!wifiConnected || !isWiFiConnected()) {
    mqttConnected = false;
    return;
  }

  handleNetworkTransportChange();
  if (!client.connected()) {
    mqttConnected = false;
    return;
  }

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
  }
}

bool isMqttConnected() {
  NetworkTransport activeTransport = getActiveNetworkTransport();
  return (
    wifiConnected &&
    activeTransport != NETWORK_NONE &&
    activeTransport == mqttTransport &&
    mqttConnected &&
    client.connected()
  );
}
