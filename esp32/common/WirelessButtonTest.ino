/*
 * ESP32 Wireless Button Test
 * 
 * Simple test to verify wireless button signal works.
 * Type "START" in Serial Monitor to send button press signal.
 * 
 * Features:
 * - Connects to WiFi and MQTT
 * - Sends button press signal when "START" typed in console
 * - Shows connection status
 * - Simple debug output
 */

#include <WiFi.h>
#include <PubSubClient.h>

// ===== CONFIGURATION =====
// WiFi settings
const char* WIFI_SSID = "Museum-Room1";
const char* WIFI_PASSWORD = "88888888";

// MQTT settings
const char* MQTT_SERVER = "192.168.0.127";
const int MQTT_PORT = 1883;
const char* CLIENT_ID = "esp32_button_test";

// MQTT Topics
const char* BUTTON_TOPIC = "room1/scene";      // Topic to send button press
const char* STATUS_TOPIC = "devices/esp32_button_test/status";

// ===== GLOBAL VARIABLES =====
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
bool wifiConnected = false;
bool mqttConnected = false;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.println("=======================================");
  Serial.println("ESP32 Wireless Button Test v1.0");
  Serial.println("=======================================");
  Serial.println();
  
  // Initialize WiFi
  connectWiFi();
  
  // Initialize MQTT
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  
  Serial.println("Setup complete!");
  Serial.println();
  Serial.println("Commands:");
  Serial.println("  START - Send button press signal");
  Serial.println("  STATUS - Show connection status");
  Serial.println("  HELP - Show this help");
  Serial.println();
}

void loop() {
  // Maintain WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnected = false;
    connectWiFi();
  } else {
    wifiConnected = true;
  }
  
  // Maintain MQTT connection
  if (wifiConnected && !mqttClient.connected()) {
    mqttConnected = false;
    connectMQTT();
  } else if (mqttClient.connected()) {
    mqttConnected = true;
    mqttClient.loop();
  }
  
  // Process serial commands
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toUpperCase();
    
    processCommand(command);
  }
  
  delay(100);
}

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println();
    Serial.print("✅ WiFi connected! IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    wifiConnected = false;
    Serial.println();
    Serial.println("❌ WiFi connection failed!");
  }
  Serial.println();
}

void connectMQTT() {
  Serial.print("Connecting to MQTT broker: ");
  Serial.print(MQTT_SERVER);
  Serial.print(":");
  Serial.println(MQTT_PORT);
  
  // Connect with Last Will Testament
  if (mqttClient.connect(CLIENT_ID, NULL, NULL, STATUS_TOPIC, 0, true, "offline")) {
    mqttConnected = true;
    Serial.println("✅ MQTT connected!");
    
    // Publish online status
    mqttClient.publish(STATUS_TOPIC, "online", true);
    Serial.print("Published status: online to ");
    Serial.println(STATUS_TOPIC);
    
    Serial.println();
  } else {
    mqttConnected = false;
    Serial.print("❌ MQTT connection failed! Error code: ");
    Serial.println(mqttClient.state());
    Serial.println();
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("📨 Received message on ");
  Serial.print(topic);
  Serial.print(": ");
  Serial.println(message);
}

void processCommand(String command) {
  Serial.print("Command received: ");
  Serial.println(command);
  Serial.println();
  
  if (command == "START") {
    sendButtonPress();
  } 
  else if (command == "STATUS") {
    showStatus();
  }
  else if (command == "HELP") {
    showHelp();
  }
  else if (command == "RESTART") {
    Serial.println("🔄 Restarting ESP32...");
    delay(1000);
    ESP.restart();
  }
  else if (command == "RECONNECT") {
    Serial.println("🔄 Reconnecting to MQTT...");
    mqttClient.disconnect();
    delay(1000);
    connectMQTT();
  }
  else {
    Serial.println("❓ Unknown command. Type HELP for available commands.");
  }
  
  Serial.println();
}

void sendButtonPress() {
  Serial.println("🔘 Sending button press signal...");
  
  if (!wifiConnected) {
    Serial.println("❌ Cannot send - WiFi not connected!");
    return;
  }
  
  if (!mqttConnected) {
    Serial.println("❌ Cannot send - MQTT not connected!");
    return;
  }
  
  // Send button press signal
  bool success = mqttClient.publish(BUTTON_TOPIC, "START", false);
  
  if (success) {
    Serial.println("✅ Button press signal sent successfully!");
    Serial.print("   Topic: ");
    Serial.println(BUTTON_TOPIC);
    Serial.print("   Message: START");
    Serial.println();
    Serial.println("💡 Check your Raspberry Pi logs to see if scene started.");
  } else {
    Serial.println("❌ Failed to send button press signal!");
  }
}

void showStatus() {
  Serial.println("📊 Current Status:");
  Serial.println("==================");
  
  // WiFi Status
  Serial.print("WiFi: ");
  if (wifiConnected) {
    Serial.print("✅ Connected to ");
    Serial.println(WIFI_SSID);
    Serial.print("      IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("      Signal: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("❌ Disconnected");
  }
  
  // MQTT Status
  Serial.print("MQTT: ");
  if (mqttConnected) {
    Serial.print("✅ Connected to ");
    Serial.print(MQTT_SERVER);
    Serial.print(":");
    Serial.println(MQTT_PORT);
    Serial.print("      Client ID: ");
    Serial.println(CLIENT_ID);
  } else {
    Serial.println("❌ Disconnected");
    if (wifiConnected) {
      Serial.print("      Error code: ");
      Serial.println(mqttClient.state());
    }
  }
  
  // System Info
  Serial.print("Uptime: ");
  Serial.print(millis() / 1000);
  Serial.println(" seconds");
  
  Serial.print("Free heap: ");
  Serial.print(ESP.getFreeHeap());
  Serial.println(" bytes");
  
  Serial.println();
}

void showHelp() {
  Serial.println("📋 Available Commands:");
  Serial.println("======================");
  Serial.println("START     - Send wireless button press signal");
  Serial.println("STATUS    - Show connection and system status");
  Serial.println("RECONNECT - Reconnect to MQTT broker");
  Serial.println("RESTART   - Restart ESP32");
  Serial.println("HELP      - Show this help message");
  Serial.println();
  Serial.println("💡 Tips:");
  Serial.println("- Make sure your Raspberry Pi is running");
  Serial.println("- Check that MQTT broker is accessible");
  Serial.println("- Verify WiFi and MQTT settings in code");
  Serial.println();
}

// Utility function to get MQTT error description
String getMQTTErrorDescription(int error) {
  switch (error) {
    case -4: return "Connection timeout";
    case -3: return "Connection lost";
    case -2: return "Connect failed";
    case -1: return "Disconnected";
    case 0: return "Connected";
    case 1: return "Bad protocol version";
    case 2: return "Bad client ID";
    case 3: return "Unavailable";
    case 4: return "Bad credentials";
    case 5: return "Unauthorized";
    default: return "Unknown error";
  }
}