#include "mqtt_manager.h"
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "effects_manager.h"
#include "effects_config.h"
#include "espnow_bridge.h"

// MQTT state is kept module-wide because PubSubClient owns the network session.
NetworkClient networkClient;
PubSubClient client(networkClient);
bool mqttConnected    = false;
unsigned long lastMqttAttempt   = 0;
unsigned long lastStatusPublish = 0;
String STATUS_TOPIC = String("devices/") + CLIENT_ID + "/status";
NetworkTransport mqttTransport = NETWORK_NONE;

unsigned long lastCommandTime = 0;
static bool lastPublishedDeviceStates[20] = {false};
static bool lastPublishedDeviceStateValid[20] = {false};
static int mqttAttempts = 0;
static unsigned long mqttRetryInterval = 0;

static void resetMqttRetryState() {
  mqttAttempts = 0;
  mqttRetryInterval = MQTT_RETRY_INTERVAL;
}

void publishDeviceState(int deviceIndex, const char* source, bool force) {
  (void)source;
  if (!mqttConnected || !client.connected()) return;
  if (deviceIndex < 0 || deviceIndex >= DEVICE_COUNT) return;

  bool state = deviceStates[deviceIndex];
  if (!force && lastPublishedDeviceStateValid[deviceIndex] &&
      lastPublishedDeviceStates[deviceIndex] == state) {
    return;
  }

  char stateTopic[96];
  snprintf(stateTopic, sizeof(stateTopic), "%s%s/state", BASE_TOPIC_PREFIX, DEVICES[deviceIndex].name);

  const char* payload = state ? "ON" : "OFF";
  if (client.publish(stateTopic, payload, true)) {
    lastPublishedDeviceStates[deviceIndex] = state;
    lastPublishedDeviceStateValid[deviceIndex] = true;
    debugPrint("State: " + String(stateTopic) + " = " + String(payload));
  } else {
    debugPrint("Failed to publish state: " + String(stateTopic));
  }
}

void publishAllDeviceStates(const char* source) {
  for (int i = 0; i < DEVICE_COUNT; i++) {
    publishDeviceState(i, source, true);
  }
}

void publishEffectState(const char* groupName, const char* state, const char* source, bool force) {
  (void)source;
  (void)force;
  if (!mqttConnected || !client.connected()) return;
  if (groupName == nullptr || state == nullptr) return;

  char stateTopic[96];
  snprintf(stateTopic, sizeof(stateTopic), "%seffects/%s/state", BASE_TOPIC_PREFIX, groupName);

  if (client.publish(stateTopic, state, true)) {
    debugPrint("Effect state: " + String(stateTopic) + " = " + String(state));
  } else {
    debugPrint("Failed to publish effect state: " + String(stateTopic));
  }
}

void publishAllEffectStates(const char* source) {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    const char* state = isEffectActive(String(EFFECT_GROUPS[i].name)) ? "ACTIVE" : "INACTIVE";
    publishEffectState(EFFECT_GROUPS[i].name, state, source, true);
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

void mqttCallback(char* topic, byte* payload, unsigned int length) {

  if (routeEspNowMotorCommand(topic, payload, length)) return;

  // Feedback, status and state topics are not relay commands.
  if (strstr(topic, "/feedback") != nullptr ||
      strstr(topic, "/status") != nullptr ||
      strstr(topic, "/state") != nullptr) {
    return;
  }

  // Reject oversized payloads before storing them in a bounded buffer.
  if (length >= 32) {
    debugPrint("MQTT: Payload too long, ignoring");
    return;
  }

  char message[32];
  memcpy(message, payload, length);
  message[length] = '\0';

  if (DEBUG) {
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT topic: ");  Serial.println(topic);
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT message: "); Serial.println(message);
  }

  // Only room-scoped command topics are accepted.
  size_t prefixLen = strlen(BASE_TOPIC_PREFIX);
  if (strncmp(topic, BASE_TOPIC_PREFIX, prefixLen) != 0) {
    return;
  }

  // Every valid command extends the inactivity safety window.
  lastCommandTime = millis();

  char feedbackTopic[128];
  snprintf(feedbackTopic, sizeof(feedbackTopic), "%s/feedback", topic);

  bool commandSuccessful = false;

  const char* deviceName = topic + prefixLen;

  // Effect commands use the room-scoped topic room1/effects/<groupName>.
  if (strncmp(deviceName, "effects/", 8) == 0) {
    const char* effectName = deviceName + 8;

    char cmd[32];
    strncpy(cmd, message, sizeof(cmd) - 1);
    cmd[sizeof(cmd) - 1] = '\0';
    for (int i = 0; cmd[i]; i++) cmd[i] = toupper(cmd[i]);

    debugPrint("Effect command: " + String(effectName) + " -> " + String(cmd));

    if (strcmp(cmd, "ON") == 0 || strcmp(cmd, "1") == 0 || strcmp(cmd, "START") == 0) {
      startEffect(String(effectName));
      client.publish(feedbackTopic, "ACTIVE", false);
      publishEffectState(effectName, "ACTIVE", "command", true);
    } else if (strcmp(cmd, "OFF") == 0 || strcmp(cmd, "0") == 0 || strcmp(cmd, "STOP") == 0) {
      stopEffect(String(effectName));
      client.publish(feedbackTopic, "INACTIVE", false);
      publishEffectState(effectName, "INACTIVE", "command", true);
    } else {
      debugPrint("Unknown effect command");
    }
    return;
  }

  // The room-level STOP command immediately clears all relay outputs.
  if (strcmp(deviceName, "STOP") == 0) {
    turnOffAllDevices();
    stopAllEffects();
    if (RELAY_MOTOR_BRIDGE_ENABLED) stopEspNowMotors(true);
    publishAllDeviceStates("stop");
    publishAllEffectStates("stop");
    commandSuccessful = true;
    debugPrint("STOP command executed, including effects");
    if (RELAY_MOTOR_BRIDGE_ENABLED) return;  // Aggregate feedback waits for the motor ACKs.
  }

  // Individual relay commands use the room-scoped topic room1/<device_name>.
  else {
    int deviceIndex = -1;
    for (int i = 0; i < DEVICE_COUNT; i++) {
      if (strcmp(DEVICES[i].name, deviceName) == 0) {
        deviceIndex = i;
        break;
      }
    }

    if (deviceIndex >= 0) {
      char cmd[32];
      strncpy(cmd, message, sizeof(cmd) - 1);
      cmd[sizeof(cmd) - 1] = '\0';
      for (int i = 0; cmd[i]; i++) cmd[i] = toupper(cmd[i]);

      if (strcmp(cmd, "ON") == 0 || strcmp(cmd, "1") == 0) {
        setDevice(deviceIndex, true);
        publishDeviceState(deviceIndex, "command", false);
        commandSuccessful = true;
      } else if (strcmp(cmd, "OFF") == 0 || strcmp(cmd, "0") == 0) {
        setDevice(deviceIndex, false);
        publishDeviceState(deviceIndex, "command", false);
        commandSuccessful = true;
      } else {
        debugPrint("Unknown command: " + String(cmd));
      }
    } else {
      debugPrint("Unknown device: " + String(deviceName));
    }
  }

  const char* feedback = commandSuccessful ? "OK" : "ERROR";
  if (client.publish(feedbackTopic, feedback, false)) {
    debugPrint("Feedback: " + String(feedback) + " -> " + String(feedbackTopic));
  }
}

void initializeMqtt() {
  client.setBufferSize(512);
  client.setSocketTimeout(1);
  networkClient.setConnectionTimeout(300);
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

      // Subscribe to every configured relay command topic.
      String basePrefix = String(BASE_TOPIC_PREFIX);
      for (int i = 0; i < DEVICE_COUNT; i++) {
        char topicBuf[64];
        snprintf(topicBuf, sizeof(topicBuf), "%s%s", BASE_TOPIC_PREFIX, DEVICES[i].name);
        client.subscribe(topicBuf, 0);
        debugPrint("Subscribed: " + String(topicBuf));
      }

      // Subscribe to all configured and future effect group topics.
      char effectsTopic[64];
      snprintf(effectsTopic, sizeof(effectsTopic), "%seffects/#", BASE_TOPIC_PREFIX);
      client.subscribe(effectsTopic, 0);
      debugPrint("Subscribed: " + String(effectsTopic));

      // Subscribe to the room-level safety stop command.
      char stopTopic[64];
      snprintf(stopTopic, sizeof(stopTopic), "%sSTOP", BASE_TOPIC_PREFIX);
      client.subscribe(stopTopic, 0);
      debugPrint("Subscribed: " + String(stopTopic));

      subscribeEspNowMotorTopics();

      publishAllDeviceStates("reconnect");
      publishAllEffectStates("reconnect");
      if (client.publish(STATUS_TOPIC.c_str(), "online", true)) {
        debugPrint("Status: online");
      }

      // Force the next heartbeat to publish immediately after reconnect.
      lastStatusPublish = 0;
      lastCommandTime   = currentTime;

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
