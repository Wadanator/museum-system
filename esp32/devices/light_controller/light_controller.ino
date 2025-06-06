/*
 * Basic ESP32 Ethernet MQTT Client for Museum Automation
 * 
 * This sketch connects an ESP32 with Ethernet shield to an MQTT broker
 * and subscribes to specific topics to control connected hardware.
 */

#include <ETH.h>
#include <PubSubClient.h>

// Ethernet settings
#define ETH_PHY_ADDR      1
#define ETH_PHY_POWER     -1
#define ETH_PHY_MDC       23
#define ETH_PHY_MDIO      18
#define ETH_PHY_TYPE      ETH_PHY_LAN8720
#define ETH_CLK_MODE      ETH_CLOCK_GPIO17_OUT

// MQTT Settings
const char* mqtt_server = "192.168.1.100";
const int mqtt_port = 1883;
const char* mqtt_topic = "room1/light";
const char* client_id = "esp32_light_controller";

// Hardware pins
const int RELAY_PIN = 5;  // GPIO pin connected to relay

// Global objects
WiFiClient espClient;
PubSubClient client(espClient);

// Connection status
bool eth_connected = false;
bool mqtt_connected = false;

// Callback for MQTT messages
void callback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  char message[length + 1];
  for (int i = 0; i < length; i++) {
    message[i] = (char)payload[i];
  }
  message[length] = '\0';
  
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);
  
  // Handle different commands
  if (strcmp(message, "ON") == 0) {
    digitalWrite(RELAY_PIN, HIGH);
    Serial.println("Turning light ON");
  } 
  else if (strcmp(message, "OFF") == 0) {
    digitalWrite(RELAY_PIN, LOW);
    Serial.println("Turning light OFF");
  }
  else if (strcmp(message, "BLINK") == 0) {
    blinkLight();
  }
}

void blinkLight() {
  for (int i = 0; i < 5; i++) {
    digitalWrite(RELAY_PIN, HIGH);
    delay(200);
    digitalWrite(RELAY_PIN, LOW);
    delay(200);
  }
  digitalWrite(RELAY_PIN, HIGH);  // Leave ON after blinking
}

// Ethernet event handler
void WiFiEvent(WiFiEvent_t event) {
  switch (event) {
    case ARDUINO_EVENT_ETH_START:
      Serial.println("ETH Started");
      ETH.setHostname(client_id);
      break;
    case ARDUINO_EVENT_ETH_CONNECTED:
      Serial.println("ETH Connected");
      break;
    case ARDUINO_EVENT_ETH_GOT_IP:
      Serial.print("ETH MAC: ");
      Serial.print(ETH.macAddress());
      Serial.print(", IPv4: ");
      Serial.print(ETH.localIP());
      if (ETH.fullDuplex()) {
        Serial.print(", FULL_DUPLEX");
      }
      Serial.print(", ");
      Serial.print(ETH.linkSpeed());
      Serial.println("Mbps");
      eth_connected = true;
      connectToMqtt();
      break;
    case ARDUINO_EVENT_ETH_DISCONNECTED:
      Serial.println("ETH Disconnected");
      eth_connected = false;
      mqtt_connected = false;
      break;
    case ARDUINO_EVENT_ETH_STOP:
      Serial.println("ETH Stopped");
      eth_connected = false;
      mqtt_connected = false;
      break;
    default:
      break;
  }
}

unsigned long lastConnectionAttempt = 0;
unsigned long connectionRetryInterval = 5000;  // Zacína na 5 sekundách
const unsigned long MAX_RETRY_INTERVAL = 60000;  // Maximum 1 minúta
int connectionAttempts = 0;
const int MAX_CONNECTION_ATTEMPTS = 10;  // Po 10 pokusoch reštartovať

void connectToMqtt() {
  if (!eth_connected) return;
  
  unsigned long currentTime = millis();
  
  if (!client.connected() && 
      (currentTime - lastConnectionAttempt > connectionRetryInterval)) {
    
    lastConnectionAttempt = currentTime;
    connectionAttempts++;
    
    Serial.print("MQTT connection attempt #");
    Serial.print(connectionAttempts);
    Serial.print(" connecting to broker...");
    
    if (client.connect(client_id)) {
      Serial.println("connected");
      mqtt_connected = true;
      connectionAttempts = 0;
      connectionRetryInterval = 5000;  // Reset interval
      
      // Subscribe to topic
      client.subscribe(mqtt_topic);
      Serial.print("Subscribed to topic: ");
      Serial.println(mqtt_topic);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      
      // Exponenciálny backoff
      connectionRetryInterval = min(connectionRetryInterval * 2, MAX_RETRY_INTERVAL);
      Serial.print(" trying again in ");
      Serial.print(connectionRetryInterval / 1000);
      Serial.println(" seconds");
      
      mqtt_connected = false;
      
      // Po X pokusoch reštartovať zariadenie
      if (connectionAttempts >= MAX_CONNECTION_ATTEMPTS) {
        Serial.println("Max connection attempts reached, restarting device");
        ESP.restart();  // Reštartovanie ESP32
      }
    }
  }
}

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  while (!Serial) delay(10);
  
  Serial.println("Light Controller starting...");
  
  // Set up GPIO pins
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);  // Start with light off
  
  // Initialize Ethernet
  WiFi.onEvent(WiFiEvent);
  ETH.begin(ETH_PHY_ADDR, ETH_PHY_POWER, ETH_PHY_MDC, ETH_PHY_MDIO, ETH_PHY_TYPE, ETH_CLK_MODE);
  
  // Initialize MQTT client
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  Serial.println("Setup complete");
}

void loop() {
  // Maintain MQTT connection
  if (eth_connected && !client.connected()) {
    connectToMqtt();
  }
  
  // Process MQTT messages
  if (mqtt_connected) {
    client.loop();
  }
  
  // Add any other periodic tasks here
  
  delay(10);  // Small delay to prevent CPU hogging
}
