#include "mqtt_manager.h"
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "effects_manager.h"

// Global MQTT objects and state
WiFiClient wifiClient;
PubSubClient client(wifiClient);
bool mqttConnected    = false;
unsigned long lastMqttAttempt   = 0;
unsigned long lastStatusPublish = 0;
String STATUS_TOPIC = String("devices/") + CLIENT_ID + "/status";

unsigned long lastCommandTime = 0;
void mqttCallback(char* topic, byte* payload, unsigned int length) {

  // --- Guard: payload size limit ---
  if (length >= 32) {
    debugPrint("MQTT: Payload too long, ignoring");
    return;
  }

  // Stack-allocated buffers – no heap involvement
  char message[32];
  memcpy(message, payload, length);
  message[length] = '\0';

  // Use Serial directly here – topic and message are already char*, no String needed
  if (DEBUG) {
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT topic: ");  Serial.println(topic);
    Serial.print("[DEBUG] "); Serial.print(millis()); Serial.print("ms - MQTT sprava: "); Serial.println(message);
  }

  // --- Ignore feedback / status topics ---
  if (strstr(topic, "/feedback") != nullptr || strstr(topic, "/status") != nullptr) {
    return;
  }

  // --- Verify topic prefix ---
  size_t prefixLen = strlen(BASE_TOPIC_PREFIX);
  if (strncmp(topic, BASE_TOPIC_PREFIX, prefixLen) != 0) {
    return;
  }

  // Reset inactivity timer on every valid command
  lastCommandTime = millis();

  // feedbackTopic built on stack
  char feedbackTopic[128];
  snprintf(feedbackTopic, sizeof(feedbackTopic), "%s/feedback", topic);

  bool commandSuccessful = false;

  // deviceName = everything after the prefix  e.g. "light/4", "effects/group1", "STOP"
  const char* deviceName = topic + prefixLen;

  // -------------------------------------------------------------------------
  // Effects:  room1/effects/<groupName>
  // -------------------------------------------------------------------------
  if (strncmp(deviceName, "effects/", 8) == 0) {
    const char* effectName = deviceName + 8;   // pointer into original topic

    // Uppercase the command in-place on our stack copy
    char cmd[32];
    strncpy(cmd, message, sizeof(cmd) - 1);
    cmd[sizeof(cmd) - 1] = '\0';
    for (int i = 0; cmd[i]; i++) cmd[i] = toupper(cmd[i]);

    debugPrint("EFEKT Prikaz: " + String(effectName) + " -> " + String(cmd));

    if (strcmp(cmd, "ON") == 0 || strcmp(cmd, "1") == 0 || strcmp(cmd, "START") == 0) {
      startEffect(String(effectName));
      client.publish(feedbackTopic, "ACTIVE", false);
    } else if (strcmp(cmd, "OFF") == 0 || strcmp(cmd, "0") == 0 || strcmp(cmd, "STOP") == 0) {
      stopEffect(String(effectName));
      client.publish(feedbackTopic, "INACTIVE", false);
    } else {
      debugPrint("Neznamy prikaz pre efekt");
    }
    return;
  }

  // -------------------------------------------------------------------------
  // STOP
  // -------------------------------------------------------------------------
  if (strcmp(deviceName, "STOP") == 0) {
    turnOffAllDevices();
    stopAllEffects();
    commandSuccessful = true;
    debugPrint("STOP prikaz vykonany (vratane efektov)");
  }

  // -------------------------------------------------------------------------
  // Individual device:  room1/<device_name>
  // -------------------------------------------------------------------------
  else {
    // Find matching device in DEVICES[]
    int deviceIndex = -1;
    for (int i = 0; i < DEVICE_COUNT; i++) {
      if (strcmp(DEVICES[i].name, deviceName) == 0) {
        deviceIndex = i;
        break;
      }
    }

    if (deviceIndex >= 0) {
      // Uppercase command on stack copy
      char cmd[32];
      strncpy(cmd, message, sizeof(cmd) - 1);
      cmd[sizeof(cmd) - 1] = '\0';
      for (int i = 0; cmd[i]; i++) cmd[i] = toupper(cmd[i]);

      if (strcmp(cmd, "ON") == 0 || strcmp(cmd, "1") == 0) {
        setDevice(deviceIndex, true);
        commandSuccessful = true;
      } else if (strcmp(cmd, "OFF") == 0 || strcmp(cmd, "0") == 0) {
        setDevice(deviceIndex, false);
        commandSuccessful = true;
      } else {
        debugPrint("Neznamy prikaz: " + String(cmd));
      }
    } else {
      debugPrint("Nezname zariadenie: " + String(deviceName));
    }
  }

  // --- Publish feedback ---
  const char* feedback = commandSuccessful ? "OK" : "ERROR";
  if (client.publish(feedbackTopic, feedback, false)) {
    debugPrint("Feedback: " + String(feedback) + " -> " + String(feedbackTopic));
  }
}

void initializeMqtt() {
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setKeepAlive(MQTT_KEEP_ALIVE);
  client.setCallback(mqttCallback);
  debugPrint("MQTT nakonfigurovane: " + String(MQTT_SERVER) + ":" + String(MQTT_PORT));
}

void connectToMqtt() {
  if (!wifiConnected || !isWiFiConnected()) return;

  unsigned long currentTime = millis();
  static int mqttAttempts = 0;
  static unsigned long mqttRetryInterval = MQTT_RETRY_INTERVAL;

  if (!client.connected() && (currentTime - lastMqttAttempt >= mqttRetryInterval)) {
    debugPrint("Pripajam sa na MQTT broker...");
    String willTopic = "devices/" + String(CLIENT_ID) + "/status";

    if (client.connect(CLIENT_ID, willTopic.c_str(), 0, true, "offline")) {
      Serial.println("MQTT pripojene");
      debugPrint("MQTT uspesne pripojene");
      mqttConnected = true;
      mqttAttempts  = 0;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;

      // Subscribe to all device topics
      String basePrefix = String(BASE_TOPIC_PREFIX);
      for (int i = 0; i < DEVICE_COUNT; i++) {
        char topicBuf[64];
        snprintf(topicBuf, sizeof(topicBuf), "%s%s", BASE_TOPIC_PREFIX, DEVICES[i].name);
        client.subscribe(topicBuf, 0);
        debugPrint("Subscribed: " + String(topicBuf));
      }

      // Wildcard for all effect groups
      char effectsTopic[64];
      snprintf(effectsTopic, sizeof(effectsTopic), "%seffects/#", BASE_TOPIC_PREFIX);
      client.subscribe(effectsTopic, 0);
      debugPrint("Subscribed: " + String(effectsTopic));

      // STOP command
      char stopTopic[64];
      snprintf(stopTopic, sizeof(stopTopic), "%sSTOP", BASE_TOPIC_PREFIX);
      client.subscribe(stopTopic, 0);
      debugPrint("Subscribed: " + String(stopTopic));

      // Publish online status
      if (client.publish(STATUS_TOPIC.c_str(), "online", true)) {
        debugPrint("Status: online");
      }

      lastStatusPublish = currentTime;
      lastCommandTime   = currentTime;

    } else {
      mqttAttempts++;
      Serial.println("MQTT zlyhalo. Pokus: " + String(mqttAttempts));
      debugPrint("MQTT zlyhalo. RC=" + String(client.state()));

      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Max MQTT pokusov – restartujem");
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
    debugPrint("Status publikovany: online");
    lastStatusPublish = currentTime;
  }
}

bool isMqttConnected() {
  return mqttConnected && client.connected();
}