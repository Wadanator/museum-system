/*
 * ESP32 WiFi MQTT Client for Museum Automation
 * Simplified version without LED status indicators
 */

#include <WiFi.h>
#include <PubSubClient.h>

// Debug flag
const bool DEBUG = true;

// WiFi Settings
const char* ssid = "Majo-home";
const char* password = "Mmajcher7680home";

// MQTT Settings
const char* mqtt_server = "192.168.0.127";
const int mqtt_port = 1883;
const char* mqtt_topic = "room1/wall";
const char* client_id = "esp32_wifi_controller";

// Hardware pins
const int MOTOR_PIN = 4;

// Global objects
WiFiClient wifiClient;
PubSubClient client(wifiClient);

// Connection status
bool wifi_connected = false;
bool mqtt_connected = false;

// Connection retry management
unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;
unsigned long wifiRetryInterval = 5000;
unsigned long mqttRetryInterval = 5000;
const unsigned long MAX_RETRY_INTERVAL = 60000;
int wifiAttempts = 0;
int mqttAttempts = 0;
const int MAX_WIFI_ATTEMPTS = 5;
const int MAX_MQTT_ATTEMPTS = 5;

// Debug print function
void debugPrint(String message) {
  if (DEBUG) {
    Serial.print("[DEBUG] ");
    Serial.print(millis());
    Serial.print("ms - ");
    Serial.println(message);
  }
}

// MQTT callback
void callback(char* topic, byte* payload, unsigned int length) {
  char message[length + 1];
  for (int i = 0; i < length; i++) {
    message[i] = (char)payload[i];
  }
  message[length] = '\0';
  
  debugPrint("MQTT message: " + String(message));
  Serial.print("Command: ");
  Serial.println(message);
  
  if (strcmp(message, "ON") == 0) {
    digitalWrite(MOTOR_PIN, HIGH);
    Serial.println("Motor ON");
    debugPrint("Motor state: ON");
  } else if (strcmp(message, "OFF") == 0) {
    digitalWrite(MOTOR_PIN, LOW);
    Serial.println("Motor OFF");
    debugPrint("Motor state: OFF");
  } else if (strcmp(message, "RESTART") == 0) {
    Serial.println("Restarting...");
    debugPrint("Restart command - restarting ESP32");
    delay(1000);
    ESP.restart();
  } else {
    debugPrint("Unknown command: " + String(message));
  }
}

// Initialize WiFi
bool initializeWiFi() {
  debugPrint("Connecting to WiFi: " + String(ssid));
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 20) {
    delay(500);
    timeout++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected - IP: ");
    Serial.println(WiFi.localIP());
    debugPrint("WiFi connected: " + WiFi.localIP().toString());
    wifi_connected = true;
    wifiAttempts = 0;
    wifiRetryInterval = 5000;
    return true;
  } else {
    wifi_connected = false;
    debugPrint("WiFi connection failed");
    return false;
  }
}

// WiFi reconnection
void connectToWiFi() {
  unsigned long currentTime = millis();
  
  if (WiFi.status() != WL_CONNECTED && 
      (currentTime - lastWifiAttempt > wifiRetryInterval)) {
    
    debugPrint("WiFi reconnect attempt " + String(wifiAttempts + 1) + "/" + String(MAX_WIFI_ATTEMPTS));
    
    lastWifiAttempt = currentTime;
    wifiAttempts++;
    
    WiFi.disconnect();
    delay(100);
    
    if (initializeWiFi()) {
      Serial.println("WiFi reconnected");
      debugPrint("WiFi reconnected successfully");
    } else {
      wifiRetryInterval = min(wifiRetryInterval * 2, MAX_RETRY_INTERVAL);
      debugPrint("WiFi failed - retry in " + String(wifiRetryInterval) + "ms");
      
      if (wifiAttempts >= MAX_WIFI_ATTEMPTS) {
        debugPrint("Max WiFi attempts - restarting");
        ESP.restart();
      }
    }
  }
}

// MQTT connection
void connectToMqtt() {
  if (!wifi_connected || WiFi.status() != WL_CONNECTED) {
    return;
  }
  
  unsigned long currentTime = millis();
  
  if (!client.connected() && 
      (currentTime - lastMqttAttempt > mqttRetryInterval)) {
    
    debugPrint("MQTT connect attempt " + String(mqttAttempts + 1) + "/" + String(MAX_MQTT_ATTEMPTS));
    
    lastMqttAttempt = currentTime;
    mqttAttempts++;
    
    if (client.connect(client_id)) {
      Serial.println("MQTT connected");
      debugPrint("MQTT connected successfully");
      mqtt_connected = true;
      mqttAttempts = 0;
      mqttRetryInterval = 5000;
      
      client.subscribe(mqtt_topic);
      debugPrint("Subscribed to: " + String(mqtt_topic));
      
    } else {
      mqttRetryInterval = min(mqttRetryInterval * 2, MAX_RETRY_INTERVAL);
      mqtt_connected = false;
      debugPrint("MQTT failed - error: " + String(client.state()));
      
      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Max MQTT attempts - restarting");
        ESP.restart();
      }
    }
  }
}

// Check connections
void checkConnections() {
  static unsigned long lastCheck = 0;
  unsigned long currentTime = millis();
  
  if (currentTime - lastCheck > 10000) {
    lastCheck = currentTime;
    debugPrint("Status - WiFi: " + String(WiFi.status() == WL_CONNECTED ? "OK" : "FAIL") + 
               ", MQTT: " + String(client.connected() ? "OK" : "FAIL"));
    
    if (WiFi.status() != WL_CONNECTED && wifi_connected) {
      wifi_connected = false;
      mqtt_connected = false;
      debugPrint("WiFi connection lost");
    } else if (WiFi.status() == WL_CONNECTED && !wifi_connected) {
      wifi_connected = true;
      debugPrint("WiFi restored");
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 Motor Controller Starting...");
  debugPrint("=== ESP32 Motor Controller Starting ===");
  
  pinMode(MOTOR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, LOW);
  debugPrint("Hardware initialized");
  
  if (!initializeWiFi()) {
    Serial.println("WiFi failed, will retry...");
    debugPrint("Initial WiFi failed");
  }
  
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  debugPrint("MQTT configured");
  
  Serial.println("Ready - Topic: " + String(mqtt_topic));
  debugPrint("=== Setup completed ===");
}

void loop() {
  checkConnections();
  
  if (WiFi.status() != WL_CONNECTED) {
    connectToWiFi();
  }
  
  if (wifi_connected && !client.connected()) {
    connectToMqtt();
  }
  
  if (mqtt_connected && client.connected()) {
    client.loop();
  }
  
  delay(50);
}