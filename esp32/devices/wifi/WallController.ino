#include <WiFi.h>
#include <PubSubClient.h>
#include <esp_task_wdt.h> // Added for Watchdog Timer

// Configuration Constants
// -----------------------------------------------------------------------------
const bool DEBUG = true;

// WiFi
const char* WIFI_SSID = "Majo-home";
const char* WIFI_PASSWORD = "Mmajcher7680home";

// MQTT
const char* MQTT_SERVER = "192.168.0.127";
const int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "esp32_wifi_controller";
const String STATUS_TOPIC = String("devices/") + CLIENT_ID + "/status";

// Hardware
const int MOTOR_PIN = 4;
const int LIGHT_PIN = 5;
const int STEAM_PIN = 14;

// Connection Management
const unsigned long WIFI_RETRY_INTERVAL = 5000;
const unsigned long MQTT_RETRY_INTERVAL = 5000;
const unsigned long MAX_RETRY_INTERVAL = 60000;
const unsigned long STATUS_PUBLISH_INTERVAL = 30000;
const unsigned long CONNECTION_CHECK_INTERVAL = 10000;
const int MAX_WIFI_ATTEMPTS = 5;
const int MAX_MQTT_ATTEMPTS = 5;
const int MQTT_KEEP_ALIVE = 15;

// Watchdog Timer Configuration
const uint32_t WDT_TIMEOUT = 30; // Watchdog timeout in seconds

// Global Objects and State
// -----------------------------------------------------------------------------
WiFiClient wifiClient;
PubSubClient client(wifiClient);
bool wifiConnected = false;
bool mqttConnected = false;
bool hardwareOff = false;
unsigned long lastWifiAttempt = 0;
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusPublish = 0;
unsigned long lastConnectionCheck = 0;

// Utility Functions
// -----------------------------------------------------------------------------
void debugPrint(const String& message) {
  if (DEBUG) {
    Serial.print("[DEBUG] ");
    Serial.print(millis());
    Serial.print("ms - ");
    Serial.println(message);
  }
}

// Hardware Control
// -----------------------------------------------------------------------------
void controlMotor(const char* command) {
  if (strcmp(command, "START") == 0) {
    digitalWrite(MOTOR_PIN, HIGH);
    debugPrint("Motor Started");
    hardwareOff = false;
  } else if (strcmp(command, "STOP") == 0) {
    digitalWrite(MOTOR_PIN, LOW);
    debugPrint("Motor Stopped");
  } else {
    debugPrint("Unknown motor command: " + String(command));
  }
}

void controlLight(const char* command) {
  if (strcmp(command, "ON") == 0) {
    digitalWrite(LIGHT_PIN, HIGH);
    debugPrint("Light ON");
    hardwareOff = false;
  } else if (strcmp(command, "OFF") == 0) {
    digitalWrite(LIGHT_PIN, LOW);
    debugPrint("Light OFF");
  } else {
    debugPrint("Unknown light command: " + String(command));
  }
}

void controlSteam(const char* command) {
  if (strcmp(command, "ON") == 0) {
    digitalWrite(STEAM_PIN, HIGH);
    debugPrint("Steam ON");
    hardwareOff = false;
  } else if (strcmp(command, "OFF") == 0) {
    digitalWrite(STEAM_PIN, LOW);
    debugPrint("Steam OFF");
  } else {
    debugPrint("Unknown steam command: " + String(command));
  }
}

void turnOffHardware() {
  digitalWrite(MOTOR_PIN, LOW);
  digitalWrite(LIGHT_PIN, LOW);
  digitalWrite(STEAM_PIN, LOW);
  debugPrint("All hardware turned OFF due to disconnection");
  hardwareOff = true;
}

// MQTT Callback
// -----------------------------------------------------------------------------
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

  if (topicStr.startsWith(basePrefix)) {
    String deviceType = topicStr.substring(basePrefix.length());

    if (deviceType == "motor") {
      controlMotor(message);
    } else if (deviceType == "light") {
      controlLight(message);
    } else if (deviceType == "steam") {
      controlSteam(message);
    } else {
      debugPrint("Unknown device in topic: " + deviceType);
    }
  } else {
    debugPrint("Unknown topic prefix");
  }
}

// WiFi Management
// -----------------------------------------------------------------------------
bool initializeWiFi() {
  debugPrint("Connecting to WiFi: " + String(WIFI_SSID));
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 20) {
    delay(500);
    timeout++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected - IP: ");
    Serial.println(WiFi.localIP());
    debugPrint("WiFi connected: " + WiFi.localIP().toString());
    wifiConnected = true;
    lastWifiAttempt = 0;
    return true;
  }

  wifiConnected = false;
  debugPrint("WiFi connection failed");
  return false;
}

void reconnectWiFi() {
  unsigned long currentTime = millis();
  static int wifiAttempts = 0;
  static unsigned long wifiRetryInterval = WIFI_RETRY_INTERVAL;

  if (WiFi.status() != WL_CONNECTED && (currentTime - lastWifiAttempt >= wifiRetryInterval)) {
    debugPrint("WiFi reconnect attempt " + String(wifiAttempts + 1) + "/" + String(MAX_WIFI_ATTEMPTS));
    lastWifiAttempt = currentTime;
    wifiAttempts++;

    WiFi.disconnect();
    delay(100);

    if (initializeWiFi()) {
      Serial.println("WiFi reconnected");
      debugPrint("WiFi reconnected successfully");
      wifiAttempts = 0;
      wifiRetryInterval = WIFI_RETRY_INTERVAL;
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

// MQTT Management
// -----------------------------------------------------------------------------
void connectToMqtt() {
  if (!wifiConnected || WiFi.status() != WL_CONNECTED) return;

  unsigned long currentTime = millis();
  static int mqttAttempts = 0;
  static unsigned long mqttRetryInterval = MQTT_RETRY_INTERVAL;

  if (!client.connected() && (currentTime - lastMqttAttempt >= mqttRetryInterval)) {
    debugPrint("MQTT connect attempt " + String(mqttAttempts + 1) + "/" + String(MAX_MQTT_ATTEMPTS));
    lastMqttAttempt = currentTime;
    mqttAttempts++;

    if (client.connect(CLIENT_ID, NULL, NULL, STATUS_TOPIC.c_str(), 0, true, "offline")) {
      Serial.println("MQTT connected");
      debugPrint("MQTT connected successfully");
      mqttConnected = true;
      mqttAttempts = 0;
      mqttRetryInterval = MQTT_RETRY_INTERVAL;

      String topicFilter = String(BASE_TOPIC_PREFIX) + "#";
      client.subscribe(topicFilter.c_str());
      debugPrint("Subscribed to: " + topicFilter);

      client.publish(STATUS_TOPIC.c_str(), "online", true);
      debugPrint("Published status: online to " + STATUS_TOPIC);
      lastStatusPublish = currentTime;
      hardwareOff = false; // Reset hardware state on successful connection
    } else {
      mqttRetryInterval = min(mqttRetryInterval * 2, MAX_RETRY_INTERVAL);
      mqttConnected = false;
      debugPrint("MQTT failed - error: " + String(client.state()));

      if (mqttAttempts >= MAX_MQTT_ATTEMPTS) {
        debugPrint("Max MQTT attempts - restarting");
        ESP.restart();
      }
    }
  }
}

void publishStatus() {
  unsigned long currentTime = millis();
  if (mqttConnected && client.connected() && (currentTime - lastStatusPublish >= STATUS_PUBLISH_INTERVAL)) {
    client.publish(STATUS_TOPIC.c_str(), "online", true);
    debugPrint("Published status: online to " + STATUS_TOPIC);
    lastStatusPublish = currentTime;
  }
}

// Connection Monitoring
// -----------------------------------------------------------------------------
void monitorConnections() {
  unsigned long currentTime = millis();

  if (currentTime - lastConnectionCheck >= CONNECTION_CHECK_INTERVAL) {
    lastConnectionCheck = currentTime;
    debugPrint("Status - WiFi: " + String(WiFi.status() == WL_CONNECTED ? "OK" : "FAIL") +
               ", MQTT: " + String(client.connected() ? "OK" : "FAIL"));

    if (WiFi.status() != WL_CONNECTED && wifiConnected) {
      wifiConnected = false;
      mqttConnected = false;
      debugPrint("WiFi connection lost");
    } else if (WiFi.status() == WL_CONNECTED && !wifiConnected) {
      wifiConnected = true;
      debugPrint("WiFi restored");
    }
  }
}

// Setup and Loop
// -----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 MQTT Controller Starting...");
  debugPrint("=== ESP32 MQTT Controller Starting ===");

  // Initialize Watchdog Timer
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000, // Convert seconds to milliseconds
    .idle_core_mask = 0,              // Watchdog monitors all cores
    .trigger_panic = true             // Trigger panic on timeout
  };
  esp_task_wdt_init(&wdt_config);     // Initialize Watchdog with config
  esp_task_wdt_add(NULL);             // Add current task to Watchdog
  debugPrint("Watchdog Timer initialized with " + String(WDT_TIMEOUT) + "s timeout");

  pinMode(MOTOR_PIN, OUTPUT);
  pinMode(LIGHT_PIN, OUTPUT);
  pinMode(STEAM_PIN, OUTPUT);
  turnOffHardware();
  debugPrint("Hardware initialized");

  if (!initializeWiFi()) {
    Serial.println("WiFi failed, will retry...");
    debugPrint("Initial WiFi failed");
  }

  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setKeepAlive(MQTT_KEEP_ALIVE);
  client.setCallback(mqttCallback);
  debugPrint("MQTT configured");

  Serial.println("Ready - Listening on: room1/#");
  debugPrint("=== Setup completed ===");
}

void loop() {
  esp_task_wdt_reset(); // Reset Watchdog Timer
  monitorConnections();

  if (WiFi.status() != WL_CONNECTED) {
    reconnectWiFi();
  }

  if (wifiConnected && !client.connected()) {
    connectToMqtt();
  }

  if (mqttConnected && client.connected()) {
    client.loop();
    publishStatus();
  } else if (!hardwareOff) { // Only turn off hardware if not already off
    turnOffHardware();
  }

  delay(50);
}