#include "mqtt_manager.h"
#include "config.h"
#include "debug.h"
#include "hardware.h"
#include "wifi_manager.h"
#include "effects_manager.h"

// Global MQTT objects and state
WiFiClient wifiClient;
PubSubClient client(wifiClient);
bool mqttConnected = false;
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusPublish = 0;
String STATUS_TOPIC = String("devices/") + CLIENT_ID + "/status";

unsigned long lastCommandTime = 0;

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  char message[length + 1];
  for (unsigned int i = 0; i < length; i++) {
    message[i] = (char)payload[i];
  }
  message[length] = '\0';

  debugPrint("MQTT topic: " + String(topic));
  debugPrint("MQTT sprava: " + String(message));

  String topicStr(topic);
  String basePrefix(BASE_TOPIC_PREFIX);

  // Ignoruj feedback a status topics
  if (topicStr.endsWith("/feedback") || topicStr.endsWith("/status")) {
    return;
  }

  String feedbackTopic = topicStr + "/feedback";
  bool commandSuccessful = false;
  
  if (topicStr.startsWith(basePrefix)) {
    
    // Reset timeout casovaca pri prijatí prikazu
    lastCommandTime = millis();

    // =========================================================================
    // OGIKA PRE EFEKTY
    // =========================================================================
    if (topicStr.indexOf("/effects/") != -1) {
      // Získame názov efektu (všetko za posledným lomítkom)
      // Očakávame: room1/effects/nazov_skupiny
      String effectName = topicStr.substring(topicStr.lastIndexOf("/") + 1);
      String cmd = String(message);
      cmd.toUpperCase();

      debugPrint("EFEKT Prikaz: " + effectName + " -> " + cmd);

      if (cmd == "ON" || cmd == "1" || cmd == "START") {
        startEffect(effectName);
        client.publish(feedbackTopic.c_str(), "ACTIVE", false);
      } 
      else if (cmd == "OFF" || cmd == "0" || cmd == "STOP") {
        stopEffect(effectName);
        client.publish(feedbackTopic.c_str(), "INACTIVE", false);
      } else {
        debugPrint("Neznamy prikaz pre efekt");
      }
      
      return; 
    }

    String deviceName = topicStr.substring(basePrefix.length());

    // STOP prikaz
    if (deviceName == "STOP") {
      turnOffAllDevices();
      stopAllEffects();
      commandSuccessful = true;
      debugPrint("STOP prikaz vykonany (vratane efektov)");
    }
    // Prikazy pre jednotlive zariadenia
    else {
      int deviceIndex = -1;
      for (int i = 0; i < DEVICE_COUNT; i++) {
        if (String(DEVICES[i].name) == deviceName) {
          deviceIndex = i;
          break;
        }
      }

      if (deviceIndex >= 0) {
        String cmd = String(message);
        cmd.toUpperCase();

        if (cmd == "ON" || cmd == "1") {
          setDevice(deviceIndex, true);
          commandSuccessful = true;
        } 
        else if (cmd == "OFF" || cmd == "0") {
          setDevice(deviceIndex, false);
          commandSuccessful = true;
        }
        else {
          debugPrint("Neznamy prikaz: " + cmd);
        }
      } else {
        debugPrint("Nezname zariadenie: " + deviceName);
      }
    }

    // Posli feedback
    if (commandSuccessful) {
      if (client.publish(feedbackTopic.c_str(), "OK", false)) {
        debugPrint("Feedback: OK -> " + feedbackTopic);
      }
    } else {
      if (client.publish(feedbackTopic.c_str(), "ERROR", false)) {
        debugPrint("Feedback: ERROR -> " + feedbackTopic);
      }
    }
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

    // Pripoj sa s will message
    if (client.connect(CLIENT_ID, willTopic.c_str(), 0, true, "offline")) {
      Serial.println("MQTT pripojene");
      debugPrint("MQTT uspesne pripojene");
      mqttConnected = true;
      mqttAttempts = 0;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;

      // Subscribe na vsetky zariadenia
      String basePrefix = String(BASE_TOPIC_PREFIX);
      for (int i = 0; i < DEVICE_COUNT; i++) {
        String topic = basePrefix + String(DEVICES[i].name);
        client.subscribe(topic.c_str(), 0);
        debugPrint("Subscribed: " + topic);
      }

      // MQTT wildcard '#' pre všetky efekty: room1/effects/#
      String effectsTopic = basePrefix + "effects/#";
      client.subscribe(effectsTopic.c_str(), 0);
      debugPrint("Subscribed: " + effectsTopic);

      // Subscribe na STOP prikaz
      client.subscribe((basePrefix + "STOP").c_str(), 0);
      debugPrint("Subscribed: " + basePrefix + "STOP");

      // Publikuj online status
      if (client.publish(STATUS_TOPIC.c_str(), "online", true)) {
        debugPrint("Status: online");
      }

      lastStatusPublish = currentTime;
      
      // Reset casovaca pri uspesnom pripojeni
      lastCommandTime = currentTime;

    } else {
      mqttAttempts++;
      Serial.println("MQTT pripojenie zlyhalo. Pokus: " + String(mqttAttempts));
      debugPrint("MQTT zlyhalo. RC=" + String(client.state()));

      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Max MQTT pokusov dosiahnuty - restartujem ESP32");
        Serial.println("Restartujem ESP32...");
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
  
  // Pravidelne publikuj status
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