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

  debugPrint("📩 MQTT topic: " + String(topic));
  debugPrint("📩 MQTT správa: " + String(message));

  String topicStr(topic);
  String basePrefix(BASE_TOPIC_PREFIX);

  // Ignoruj feedback a status topics aby sa predišlo slučkám
  if (topicStr.endsWith("/feedback") || topicStr.endsWith("/status")) {
    debugPrint("Ignorujem feedback/status topic");
    return;
  }

  String feedbackTopic = topicStr + "/feedback";
  bool commandSuccessful = false;
  
  if (topicStr.startsWith(basePrefix)) {
    String deviceName = topicStr.substring(basePrefix.length());

    // STOP príkaz - vypne všetko
    if (deviceName == "STOP") {
      turnOffAllDevices();
      commandSuccessful = true;
      debugPrint("⚠️  STOP príkaz vykonaný");
    }
    // Príkazy pre jednotlivé zariadenia
    else {
      // Nájdi zariadenie podľa názvu
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
          debugPrint("❌ Neznámy príkaz: " + cmd + " (použite ON/OFF alebo 1/0)");
        }
      } else {
        debugPrint("❌ Neznáme zariadenie: " + deviceName);
      }
    }

    // Pošli feedback
    if (commandSuccessful) {
      if (client.publish(feedbackTopic.c_str(), "OK", false)) {
        debugPrint("✅ Feedback: OK -> " + feedbackTopic);
      }
    } else {
      if (client.publish(feedbackTopic.c_str(), "ERROR", false)) {
        debugPrint("❌ Feedback: ERROR -> " + feedbackTopic);
      }
    }
  }
}

void initializeMqtt() {
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setKeepAlive(MQTT_KEEP_ALIVE);
  client.setCallback(mqttCallback);
  debugPrint("MQTT nakonfigurované: " + String(MQTT_SERVER) + ":" + String(MQTT_PORT));
}

void connectToMqtt() {
  if (!wifiConnected || !isWiFiConnected()) return;

  unsigned long currentTime = millis();
  static int mqttAttempts = 0;
  static unsigned long mqttRetryInterval = MQTT_RETRY_INTERVAL;

  if (!client.connected() && (currentTime - lastMqttAttempt >= mqttRetryInterval)) {
    debugPrint("🔌 Pripájam sa na MQTT broker...");
    String willTopic = "devices/" + String(CLIENT_ID) + "/status";

    // Pripoj sa s will message
    if (client.connect(CLIENT_ID, willTopic.c_str(), 0, true, "offline")) {
      Serial.println("✅ MQTT pripojené");
      debugPrint("MQTT úspešne pripojené");
      mqttConnected = true;
      mqttAttempts = 0;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;

      // Subscribe na všetky zariadenia
      String basePrefix = String(BASE_TOPIC_PREFIX);
      for (int i = 0; i < DEVICE_COUNT; i++) {
        String topic = basePrefix + String(DEVICES[i].name);
        client.subscribe(topic.c_str(), 0);
        debugPrint("📡 Subscribed: " + topic);
      }

      // Subscribe na STOP príkaz
      client.subscribe((basePrefix + "STOP").c_str(), 0);
      debugPrint("📡 Subscribed: " + basePrefix + "STOP");

      // Publikuj online status okamžite
      if (client.publish(STATUS_TOPIC.c_str(), "online", true)) {
        debugPrint("📤 Status: online");
      }

      lastStatusPublish = currentTime;

    } else {
      mqttAttempts++;
      Serial.println("❌ MQTT pripojenie zlyhalo. Pokus: " + String(mqttAttempts));
      debugPrint("MQTT pripojenie zlyhalo. Pokus: " + String(mqttAttempts));

      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Max MQTT pokusov dosiahnutý - reštartujem ESP32");
        Serial.println("🔄 Reštartujem ESP32...");
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
    debugPrint("📤 Status publikovaný: online");
    lastStatusPublish = currentTime;
  } else {
    debugPrint("❌ Nepodarilo sa publikovať status");
  }
}

bool isMqttConnected() {
  return mqttConnected && client.connected();
}