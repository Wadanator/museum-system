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
static CoverState lastPublishedCoverStates[8];
static bool lastPublishedCoverStateValid[8] = {false};
static int mqttAttempts = 0;
static unsigned long mqttRetryInterval = 0;

static void resetMqttRetryState() {
  mqttAttempts = 0;
  mqttRetryInterval = MQTT_RETRY_INTERVAL;
}

static bool isValidCoverIndex(int coverIndex) {
  return coverIndex >= 0 && coverIndex < COVER_COUNT && coverIndex < 8 &&
         COVERS[coverIndex].enabled;
}

void publishCoverState(int coverIndex, const char* source, bool force) {
  (void)source;
  if (!mqttConnected || !client.connected()) return;
  if (!isValidCoverIndex(coverIndex)) return;

  CoverState state = getCoverState(coverIndex);
  if (!force && lastPublishedCoverStateValid[coverIndex] &&
      lastPublishedCoverStates[coverIndex] == state) {
    return;
  }

  char stateTopic[96];
  snprintf(stateTopic, sizeof(stateTopic), "%s%s/state", BASE_TOPIC_PREFIX, COVERS[coverIndex].topicName);

  const char* payload = getCoverStateText(coverIndex);
  if (client.publish(stateTopic, payload, true)) {
    lastPublishedCoverStates[coverIndex] = state;
    lastPublishedCoverStateValid[coverIndex] = true;
    debugPrint("State: " + String(stateTopic) + " = " + String(payload));
  } else {
    debugPrint("Failed to publish state: " + String(stateTopic));
  }
}

void publishAllCoverStates(const char* source) {
  for (int i = 0; i < COVER_COUNT && i < 8; i++) {
    publishCoverState(i, source, true);
  }
}

void publishCoverFeedback(int coverIndex, const char* feedback) {
  if (!mqttConnected || !client.connected()) return;
  if (!isValidCoverIndex(coverIndex) || feedback == nullptr) return;

  char feedbackTopic[96];
  snprintf(feedbackTopic, sizeof(feedbackTopic), "%s%s/feedback", BASE_TOPIC_PREFIX, COVERS[coverIndex].topicName);

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

static int findCoverByTopicName(const char* deviceName) {
  for (int i = 0; i < COVER_COUNT && i < 8; i++) {
    if (!COVERS[i].enabled) continue;
    if (strcmp(COVERS[i].topicName, deviceName) == 0) return i;
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

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  if (strstr(topic, "/feedback") != nullptr ||
      strstr(topic, "/status") != nullptr ||
      strstr(topic, "/state") != nullptr) {
    return;
  }

  if (length >= 32) {
    debugPrint("MQTT: Payload too long, ignoring");
    return;
  }

  char message[32];
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

  if (strcmp(deviceName, HEARTBEAT_TOPIC_SUFFIX) == 0) {
    markHeartbeatReceived();
    return;
  }

  lastCommandTime = millis();

  char feedbackTopic[128];
  snprintf(feedbackTopic, sizeof(feedbackTopic), "%s/feedback", topic);

  const char* feedback = "ERROR";

  if (strcmp(deviceName, "STOP") == 0) {
    stopAllCovers("room_stop");
    publishAllCoverStates("room_stop");
    for (int i = 0; i < COVER_COUNT && i < 8; i++) {
      if (!COVERS[i].enabled) continue;
      publishCoverFeedback(i, getCoverState(i) == COVER_STATE_ERROR ? "ERROR:HARDWARE" : "OK");
    }
    feedback = "OK";
    debugPrint("Global STOP command executed for all covers");
  } else {
    int coverIndex = findCoverByTopicName(deviceName);
    if (coverIndex >= 0) {
      if (strcmp(message, "OPEN") == 0) {
        feedback = commandCoverOpen(coverIndex);
      } else if (strcmp(message, "CLOSE") == 0) {
        feedback = commandCoverClose(coverIndex);
      } else if (strcmp(message, "STOP") == 0) {
        feedback = commandCoverStop(coverIndex);
      } else {
        debugPrint("Unknown cover command: " + String(message));
      }
    } else {
      debugPrint("Unknown cover topic: " + String(deviceName));
    }
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

      for (int i = 0; i < COVER_COUNT && i < 8; i++) {
        if (!COVERS[i].enabled) continue;
        char topicBuf[64];
        snprintf(topicBuf, sizeof(topicBuf), "%s%s", BASE_TOPIC_PREFIX, COVERS[i].topicName);
        client.subscribe(topicBuf, 0);
        debugPrint("Subscribed: " + String(topicBuf));
      }

      char stopTopic[64];
      snprintf(stopTopic, sizeof(stopTopic), "%sSTOP", BASE_TOPIC_PREFIX);
      client.subscribe(stopTopic, 0);
      debugPrint("Subscribed: " + String(stopTopic));

      char heartbeatTopic[96];
      snprintf(heartbeatTopic, sizeof(heartbeatTopic), "%s%s", BASE_TOPIC_PREFIX, HEARTBEAT_TOPIC_SUFFIX);
      client.subscribe(heartbeatTopic, 0);
      debugPrint("Subscribed: " + String(heartbeatTopic));

      publishAllCoverStates("reconnect");
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