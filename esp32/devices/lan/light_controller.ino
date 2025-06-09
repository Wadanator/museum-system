/*
/*
 * ESP32 W5500 Ethernet Shield MQTT Client for Museum Automation
 * 
 * This sketch connects an ESP32 with W5500 Ethernet shield to an MQTT broker
 * and subscribes to specific topics to control connected hardware.
 * 
 * Hardware connections:
 * W5500 Shield -> ESP32
 * MOSI -> GPIO 23
 * MISO -> GPIO 19
 * SCK  -> GPIO 18
 * CS   -> GPIO 5
 * RST  -> GPIO 4 (optional)
 */

#include <SPI.h>
#include <Ethernet.h>
#include <PubSubClient.h>

// W5500 Ethernet Shield Settings
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED}; // MAC adresa
IPAddress ip(192, 168, 1, 177);      // Statická IP adresa (voliteľné)
IPAddress gateway(192, 168, 1, 1);   // Gateway
IPAddress subnet(255, 255, 255, 0);  // Subnet mask

// W5500 SPI pin definitions
#define W5500_CS   5   // Chip Select pin
#define W5500_RST  4   // Reset pin (voliteľný)

// MQTT Settings
const char* mqtt_server = "192.168.0.127";
const int mqtt_port = 1883;
const char* mqtt_topic = "room1/light";
const char* client_id = "esp32_w5500_light_controller";

// Hardware pins
const int RELAY_PIN = 2;  // GPIO pin connected to relay (zmenené z 5 lebo CS používa 5)

// Global objects
EthernetClient ethClient;
PubSubClient client(ethClient);

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
  message[length] = '';
  
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

// Inicializácia W5500 Ethernet
bool initializeEthernet() {
  Serial.println("Initializing W5500 Ethernet...");
  
  // Reset W5500 chip (ak je RST pin pripojený)
  if (W5500_RST >= 0) {
    pinMode(W5500_RST, OUTPUT);
    digitalWrite(W5500_RST, LOW);
    delay(100);
    digitalWrite(W5500_RST, HIGH);
    delay(100);
  }
  
  // Nastavenie CS pinu
  Ethernet.init(W5500_CS);
  
  // Pokus o pripojenie s DHCP
  Serial.println("Attempting DHCP connection...");
  if (Ethernet.begin(mac) == 0) {
    Serial.println("DHCP failed, using static IP");
    // Ak DHCP zlyhá, použije statickú IP
    Ethernet.begin(mac, ip, gateway, subnet);
  }
  
  // Malé zdržanie pre stabilizáciu
  delay(2000);
  
  // Kontrola pripojenia
  if (Ethernet.hardwareStatus() == EthernetNoHardware) {
    Serial.println("Ethernet shield was not found.");
    return false;
  }
  
  if (Ethernet.linkStatus() == LinkOFF) {
    Serial.println("Ethernet cable is not connected.");
    return false;
  }
  
  // Zobrazenie network informácií
  Serial.print("IP address: ");
  Serial.println(Ethernet.localIP());
  Serial.print("Gateway: ");
  Serial.println(Ethernet.gatewayIP());
  Serial.print("Subnet: ");
  Serial.println(Ethernet.subnetMask());
  Serial.print("DNS: ");
  Serial.println(Ethernet.dnsServerIP());
  
  eth_connected = true;
  return true;
}

unsigned long lastConnectionAttempt = 0;
unsigned long connectionRetryInterval = 5000;  // Začína na 5 sekundách
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

// Kontrola Ethernet pripojenia
void checkEthernetConnection() {
  static unsigned long lastCheck = 0;
  unsigned long currentTime = millis();
  
  // Kontroluj každých 10 sekúnd
  if (currentTime - lastCheck > 10000) {
    lastCheck = currentTime;
    
    if (Ethernet.linkStatus() == LinkOFF) {
      Serial.println("Ethernet cable disconnected");
      eth_connected = false;
      mqtt_connected = false;
    } else if (!eth_connected && Ethernet.linkStatus() == LinkON) {
      Serial.println("Ethernet cable reconnected");
      eth_connected = true;
      // Pokus o obnovenie MQTT pripojenia
      connectToMqtt();
    }
  }
}

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  while (!Serial) delay(10);
  
  Serial.println("W5500 Light Controller starting...");
  
  // Set up GPIO pins
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);  // Start with light off
  
  // Initialize SPI
  SPI.begin();
  
  // Initialize W5500 Ethernet
  if (!initializeEthernet()) {
    Serial.println("Ethernet initialization failed!");
    // Môžete sa rozhodnúť reštartovať alebo pokračovať bez siete
    while(1) {
      delay(1000);
      Serial.println("Retrying Ethernet initialization...");
      if (initializeEthernet()) {
        break;
      }
    }
  }
  
  // Initialize MQTT client
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  Serial.println("Setup complete");
}

void loop() {
  // Kontrola Ethernet pripojenia
  checkEthernetConnection();
  
  // Maintain MQTT connection
  if (eth_connected && !client.connected()) {
    connectToMqtt();
  }
  
  // Process MQTT messages
  if (mqtt_connected) {
    client.loop();
  }
  
  // Maintain Ethernet connection
  Ethernet.maintain();
  
  delay(10);  // Small delay to prevent CPU hogging
}
