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
  if (topicStr.endsWith("/status")) {
    debugPrint("Ignoring message on status topic: " + topicStr);
    return;
  }

  // Derive status topic for feedback
  String statusTopic = basePrefix + "status";
  String feedbackMessage = "ERROR";  // Default error response
  bool commandSuccessful = false;

  if (topicStr.startsWith(basePrefix)) {
    String deviceType = topicStr.substring(basePrefix.length());

    // NOVÉ: STOP príkaz - okamžitý feedback
    if (deviceType == "STOP") {
      debugPrint("STOP command received - turning off all hardware");
      turnOffHardware();
      feedbackMessage = "ALL_HARDWARE_STOPPED";
      commandSuccessful = true;
      
    } else {
      // Parse motor commands
      String command = String(message);
      String speed = "50";
      String direction = "L";
      
      debugPrint("Parsing command: " + command);
      
      // Parse compound commands
      int firstColon = command.indexOf(':');
      if (firstColon > 0) {
        String baseCommand = command.substring(0, firstColon);
        String params = command.substring(firstColon + 1);
        
        if (baseCommand == "ON") {
          int secondColon = params.indexOf(':');
          if (secondColon > 0) {
            speed = params.substring(0, secondColon);
            direction = params.substring(secondColon + 1);
          } else {
            speed = params;
          }
          command = baseCommand;
          
        } else if (baseCommand == "DIR") {
          direction = params;
          command = baseCommand;
          debugPrint("DIR command parsed - new direction: " + direction);
          
        } else if (baseCommand == "SPEED") {
          speed = params;
          command = baseCommand;
        }
      }

      debugPrint("Final parsed - Command: " + command + ", Speed: " + speed + ", Direction: " + direction);

      // Execute motor commands
      if (deviceType == "motor1") {
        if (command == "ON" || command == "OFF" || command == "SPEED" || command == "DIR") {
          controlMotor1(command.c_str(), speed.c_str(), direction.c_str());
          feedbackMessage = "OK";
          commandSuccessful = true;
        } else {
          feedbackMessage = "ERROR_UNKNOWN_COMMAND";
        }
      } else if (deviceType == "motor2") {
        if (command == "ON" || command == "OFF" || command == "SPEED" || command == "DIR") {
          controlMotor2(command.c_str(), speed.c_str(), direction.c_str());
          feedbackMessage = "OK";
          commandSuccessful = true;
        } else {
          feedbackMessage = "ERROR_UNKNOWN_COMMAND";
        }
      } else {
        feedbackMessage = "ERROR_UNKNOWN_DEVICE";
      }
    }
  } else {
    feedbackMessage = "ERROR_UNKNOWN_TOPIC";
  }

  // KRITICKÉ: OKAMŽITÉ odoslanie feedback - PRED akýmikoľvek inými operáciami
  if (client.connected()) {
    unsigned long feedbackStart = millis();
    
    // Synchronné odoslanie s prioritou
    bool publishResult = client.publish(statusTopic.c_str(), feedbackMessage.c_str(), false); // retained=false pre rýchlosť
    
    if (publishResult) {
      // FORCE immediate send - nevyčkávaj na batching
      client.loop(); // Immediate processing
      
      unsigned long feedbackTime = millis() - feedbackStart;
      debugPrint("✅ FAST Feedback sent in " + String(feedbackTime) + "ms: " + feedbackMessage);
    } else {
      debugPrint("❌ Feedback FAILED to send: " + feedbackMessage);
    }
  } else {
    debugPrint("❌ MQTT disconnected - cannot send feedback");
  }
}

void initializeMqtt() {
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setKeepAlive(MQTT_KEEP_ALIVE);
  
  // Optimalizácia pre nízku latenciu (ak je podporovaná)
  // client.setSocketTimeout(5);  // Zakomentované - nie je vo všetkých verziách
  
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
    
    // OPTIMALIZOVANÉ pripojenie s will message
    if (client.connect(CLIENT_ID, willTopic.c_str(), 0, true, "offline")) { // willRetain=true
      debugPrint("MQTT connected successfully");
      mqttConnected = true;
      mqttAttempts = 0;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;
      
      // Subscribe to motor control topics
      String basePrefix = String(BASE_TOPIC_PREFIX);
      
      // Subscribe s QoS 0 pre najrýchlejšie doručenie
      client.subscribe((basePrefix + "motor1").c_str(), 0);  // QoS 0
      client.subscribe((basePrefix + "motor2").c_str(), 0);  // QoS 0
      client.subscribe((basePrefix + "STOP").c_str(), 0);    // QoS 0
      
      debugPrint("Subscribed to motor topics with QoS 0 (fastest delivery)");
      
      // Okamžité odoslanie online status
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

// NOVÁ FUNKCIA: Okamžité publikovanie status
void publishStatusImmediate() {
  if (client.connected()) {
    // Publish bez retained flag pre rýchlosť
    bool result = client.publish(STATUS_TOPIC.c_str(), "online", false);
    if (result) {
      client.loop(); // Force immediate send
      debugPrint("✅ Status published immediately: online");
    } else {
      debugPrint("❌ Failed to publish status");
    }
    lastStatusPublish = millis();
  }
}

// UPRAVENÁ funkcia: Rýchlejší status publishing
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

// OPTIMALIZOVANÁ MQTT loop
void mqttLoop() {
  if (client.connected()) {
    // DÔLEŽITÉ: client.loop() volať častejšie pre rýchly feedback
    client.loop(); // Spracovanie prichádzajúcich/odchádzajúcich správ
    
    // Publikuj status menej často
    static unsigned long lastStatusCheck = 0;
    if (millis() - lastStatusCheck >= STATUS_PUBLISH_INTERVAL) {
      lastStatusCheck = millis();
      publishStatus();
    }
  } else {
    mqttConnected = false;
  }
}