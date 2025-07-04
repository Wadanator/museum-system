#!/usr/bin/env python3
"""
This script creates the directory structure for the automated museum project
with MQTT control system.
"""

import os
import json
import configparser

def create_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    else:
        print(f"Directory already exists: {path}")

def create_file(path, content):
    """Create a file with the specified content."""
    with open(path, 'w', encoding='utf-8') as file:  # Specify UTF-8 encoding
        file.write(content)
    print(f"Created file: {path}")

def create_project_structure():
    """Create the complete project structure."""
    base_dir = "museum-system"
    
    # Create main directories
    directories = [
        f"{base_dir}",
        f"{base_dir}/docs",
        f"{base_dir}/broker",
        f"{base_dir}/raspberry_pi",
        f"{base_dir}/raspberry_pi/config",
        f"{base_dir}/raspberry_pi/scenes",
        f"{base_dir}/raspberry_pi/scenes/room1",
        f"{base_dir}/raspberry_pi/scenes/room2",
        f"{base_dir}/raspberry_pi/utils",
        f"{base_dir}/raspberry_pi/service",
        f"{base_dir}/esp32",
        f"{base_dir}/esp32/common",
        f"{base_dir}/esp32/devices",
        f"{base_dir}/esp32/devices/light_controller",
        f"{base_dir}/esp32/devices/audio_player",
        f"{base_dir}/esp32/devices/motor_controller",
        f"{base_dir}/esp32/examples",
        f"{base_dir}/tools",
        f"{base_dir}/tools/mqtt_test",
    ]
    
    for directory in directories:
        create_directory(directory)
    
    # Create README.md
    readme_content = """# Automated Museum with MQTT Control

This project implements an interactive museum where each room has its own guide system
based on timed scenes and automated hardware control using MQTT.

## Overview

- Each room has a button that triggers a specific scene when pressed
- Scenes are defined in JSON files stored on Raspberry Pi
- MQTT messaging is used for communication between devices
- ESP32 devices control various hardware components (lights, audio, motors)

## Directory Structure

- `docs/`: Project documentation
- `broker/`: MQTT broker configuration
- `raspberry_pi/`: Code for the Raspberry Pi scene controllers
- `esp32/`: Code for ESP32 devices
- `tools/`: Utility tools for testing and development
"""
    create_file(f"{base_dir}/README.md", readme_content)
    
    # Create .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Arduino
.pioenvs
.piolibdeps
.clang_complete
.gcc-flags.json

# Editors
.vscode/
.idea/
*.swp
*.swo

# OS specific
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
mosquitto.db
"""
    create_file(f"{base_dir}/.gitignore", gitignore_content)
    
    # Create mosquitto.conf
    mosquitto_conf = """# Basic configuration for Mosquitto MQTT Broker
listener 1883
allow_anonymous true
connection_messages true
log_type all
"""
    create_file(f"{base_dir}/broker/mosquitto.conf", mosquitto_conf)
    
    # Create start_broker.sh
    broker_script = """#!/bin/bash
# Script to start the MQTT broker
mosquitto -c mosquitto.conf
"""
    create_file(f"{base_dir}/broker/start_broker.sh", broker_script)
    os.chmod(f"{base_dir}/broker/start_broker.sh", 0o755)  # Make executable
    
    # Create config.ini
    config = configparser.ConfigParser()
    config['MQTT'] = {
        'BrokerIP': '192.168.0.127',
        'Port': '1883'
    }
    config['GPIO'] = {
        'ButtonPin': '17'
    }
    config['Room'] = {
        'ID': 'room1'
    }
    config['Scenes'] = {
        'Directory': 'scenes'
    }
    
    with open(f"{base_dir}/raspberry_pi/config/config.ini", 'w') as configfile:
        config.write(configfile)
    print(f"Created file: {base_dir}/raspberry_pi/config/config.ini")
    
    # Create sample scene JSON
    scene = [
        {
            "timestamp": 0,
            "topic": "room1/light",
            "message": "ON"
        },
        {
            "timestamp": 2.0,
            "topic": "room1/audio",
            "message": "PLAY_WELCOME"
        },
        {
            "timestamp": 5.0,
            "topic": "room1/light",
            "message": "BLINK"
        },
        {
            "timestamp": 10.0,
            "topic": "room1/audio",
            "message": "STOP"
        },
        {
            "timestamp": 12.0,
            "topic": "room1/light",
            "message": "OFF"
        }
    ]
    
    with open(f"{base_dir}/raspberry_pi/scenes/room1/intro.json", 'w') as f:
        json.dump(scene, f, indent=2)
    print(f"Created file: {base_dir}/raspberry_pi/scenes/room1/intro.json")
    
    # Create sample scene for room2
    scene2 = [
        {
            "timestamp": 0,
            "topic": "room2/light",
            "message": "ON"
        },
        {
            "timestamp": 3.0,
            "topic": "room2/motor",
            "message": "START"
        },
        {
            "timestamp": 8.0,
            "topic": "room2/motor",
            "message": "STOP"
        },
        {
            "timestamp": 10.0,
            "topic": "room2/light",
            "message": "OFF"
        }
    ]
    
    with open(f"{base_dir}/raspberry_pi/scenes/room2/intro.json", 'w') as f:
        json.dump(scene2, f, indent=2)
    print(f"Created file: {base_dir}/raspberry_pi/scenes/room2/intro.json")
    
    # Create MQTT test script
    mqtt_test = """#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time
import argparse

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    if args.subscribe:
        print(f"Subscribing to topic: {args.topic}")
        client.subscribe(args.topic)

def on_message(client, userdata, msg):
    print(f"Received message: {msg.topic} = {msg.payload.decode()}")

def on_publish(client, userdata, mid):
    print(f"Message {mid} published")

# Parse arguments
parser = argparse.ArgumentParser(description='MQTT Publisher/Subscriber for testing')
parser.add_argument('-b', '--broker', default='localhost', help='MQTT broker address')
parser.add_argument('-p', '--port', type=int, default=1883, help='MQTT broker port')
parser.add_argument('-t', '--topic', default='test/topic', help='MQTT topic')
parser.add_argument('-m', '--message', help='Message to publish')
parser.add_argument('-s', '--subscribe', action='store_true', help='Act as subscriber')

args = parser.parse_args()

# Setup client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish

# Connect
client.connect(args.broker, args.port, 60)

if args.subscribe:
    # Run as subscriber
    print(f"Running as subscriber to topic: {args.topic}")
    client.loop_forever()
else:
    # Run as publisher
    message = args.message if args.message else "Test message"
    print(f"Publishing to {args.topic}: {message}")
    client.publish(args.topic, message)
    time.sleep(1)  # Wait for message to be published
    client.disconnect()
"""
    create_file(f"{base_dir}/tools/mqtt_test/mqtt_publisher.py", mqtt_test)
    os.chmod(f"{base_dir}/tools/mqtt_test/mqtt_publisher.py", 0o755)  # Make executable
    
    # Create a sample ESP32 sketch
    esp32_sketch = """/*
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
"""
    create_file(f"{base_dir}/esp32/devices/light_controller/light_controller.ino", esp32_sketch)
    
    # Create systemd service file
    systemd_service = """[Unit]
Description=Museum Automation Service
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/museum-system/raspberry_pi/main.py
WorkingDirectory=/home/pi/museum-system/raspberry_pi
StandardOutput=append:/var/log/museum-system.log
StandardError=append:/var/log/museum-system-error.log
Restart=always
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5
User=pi

[Install]
WantedBy=multi-user.target
"""
    create_file(f"{base_dir}/raspberry_pi/service/museum_service.service", systemd_service)
    
    # Create MQTT client Python module
    mqtt_client = """#!/usr/bin/env python3
#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time

class MQTTClient:
    def __init__(self, broker_host, broker_port=1883, client_id=None, use_logging=True):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.use_logging = use_logging
        self.connected = False
        
        # Fix for paho-mqtt 2.0+ compatibility
        try:
            # Try the new API first (paho-mqtt 2.0+)
            self.client = mqtt.Client(
                client_id=client_id,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1
            )
        except TypeError:
            # Fallback to old API (paho-mqtt 1.x)
            self.client = mqtt.Client(client_id=client_id)
        
        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            if self.use_logging:
                print(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
        else:
            self.connected = False
            if self.use_logging:
                print(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if self.use_logging:
            print(f"Disconnected from MQTT broker. Return code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        if self.use_logging:
            print(f"Received message: {msg.topic} - {msg.payload.decode()}")
    
    def _on_publish(self, client, userdata, mid):
        if self.use_logging:
            print(f"Message published with ID: {mid}")
    
    def connect(self, timeout=10):
        try:
            self.client.connect(self.broker_host, self.broker_port, timeout)
            self.client.loop_start()
            
            # Wait for connection to be established
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            return self.connected
        except Exception as e:
            if self.use_logging:
                print(f"Error connecting to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
    
    def publish(self, topic, message, qos=0, retain=False):
        if not self.connected:
            if self.use_logging:
                print("Not connected to MQTT broker")
            return False
        
        try:
            # Convert message to JSON string if it's a dict
            if isinstance(message, dict):
                message = json.dumps(message)
            
            result = self.client.publish(topic, message, qos, retain)
            
            if self.use_logging:
                print(f"Publishing to {topic}: {message}")
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            if self.use_logging:
                print(f"Error publishing message: {e}")
            return False
    
    def subscribe(self, topic, qos=0):
        if not self.connected:
            if self.use_logging:
                print("Not connected to MQTT broker")
            return False
        
        try:
            result = self.client.subscribe(topic, qos)
            if self.use_logging:
                print(f"Subscribed to topic: {topic}")
            return result[0] == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            if self.use_logging:
                print(f"Error subscribing to topic: {e}")
            return False
    
    def is_connected(self):
        return self.connected

# Example usage and testing
if __name__ == "__main__":
    # Test the MQTT client
    client = MQTTClient("localhost", use_logging=True)
    
    if client.connect():
        print("Connection successful!")
        
        # Test publishing
        test_message = {"device": "test", "value": 42, "timestamp": time.time()}
        client.publish("test/topic", test_message)
        
        # Test subscribing
        client.subscribe("test/topic")
        
        # Keep alive for a bit
        time.sleep(2)
        
        client.disconnect()
        print("Test completed")
    else:
        print("Failed to connect to MQTT broker")
        print("Make sure your MQTT broker is running on localhost:1883") 
"""
    create_file(f"{base_dir}/raspberry_pi/utils/mqtt_client.py", mqtt_client)
    
    # Create scene parser Python module
    scene_parser = """
#!/usr/bin/env python3
import json
import time
import os
import sys

class SceneParser:
    def __init__(self, audio_handler=None):
        self.scene_data = None
        self.start_time = None
        self.audio_handler = audio_handler
        self.executed_actions = set()  # Track executed actions to avoid duplicates
    
    def load_scene(self, scene_file):
        ###Load scene from JSON file.###
        try:
            with open(scene_file, 'r') as file:
                self.scene_data = json.load(file)
            
            # Reset executed actions when loading new scene
            self.executed_actions = set()
            
            # Validate scene data
            if not isinstance(self.scene_data, list):
                print("❌ Scene data must be a list of actions")
                return False
            
            # Validate each action
            for i, action in enumerate(self.scene_data):
                if not all(key in action for key in ['timestamp', 'topic', 'message']):
                    print(f"❌ Action {i} missing required fields (timestamp, topic, message)")
                    return False
            
            print(f"✅ Scene loaded: {len(self.scene_data)} actions")
            return True
            
        except Exception as e:
            print(f"❌ Error loading scene: {e}")
            self.scene_data = None
            return False
    
    def start_scene(self):
        ###Start scene playback.###
        if not self.scene_data:
            print("❌ No scene is loaded")
            return False
        
        self.start_time = time.time()
        self.executed_actions = set()
        print("🎬 Scene started")
        return True
    
    def get_current_actions(self, mqtt_client):
        ###Get actions that should execute at current time.###
        if not self.scene_data or not self.start_time:
            return []
        
        current_time = time.time() - self.start_time
        actions = []
        
        for i, action in enumerate(self.scene_data):
            action_id = f"{i}_{action['timestamp']}"
            
            # Check if action should execute now and hasn't been executed yet
            if (action["timestamp"] <= current_time and 
                action_id not in self.executed_actions):
                
                actions.append(action)
                self.executed_actions.add(action_id)
                
                # Handle audio commands locally
                if action["topic"].endswith("/audio"):
                    self._handle_audio_command(action["message"])
                else:
                    # Publish other commands to MQTT
                    if mqtt_client:
                        mqtt_client.publish(action["topic"], action["message"], retain=False)
        
        return actions
    
    def _handle_audio_command(self, message):
        ###Handle audio-specific commands.###
        if not self.audio_handler:
            print("⚠️  No audio handler available")
            return
        
        try:
            # Parse different audio command formats
            if message.startswith("PLAY:"):
                # Format: PLAY:filename.mp3 or PLAY:filename.mp3:volume
                parts = message.split(":")
                filename = parts[1]
                volume = float(parts[2]) if len(parts) > 2 else 0.7
                self.audio_handler.play_audio_with_volume(filename, volume)
                
            elif message.startswith("PLAY_"):
                # Legacy format: PLAY_WELCOME -> welcome.mp3/mp3/ogg
                self.audio_handler.play_audio(message)
                
            elif message == "STOP":
                self.audio_handler.stop_audio()
                
            elif message == "PAUSE":
                self.audio_handler.pause_audio()
                
            elif message == "RESUME":
                self.audio_handler.resume_audio()
                
            elif message.startswith("VOLUME:"):
                # Format: VOLUME:0.5
                volume = float(message.split(":")[1])
                self.audio_handler.set_volume(volume)
                
            else:
                # Direct filename
                self.audio_handler.play_audio(message)
                
        except Exception as e:
            print(f"❌ Error handling audio command '{message}': {e}")
    
    def get_scene_duration(self):
        ###Get total duration of the scene.###
        if not self.scene_data:
            return 0
        return max(action["timestamp"] for action in self.scene_data)
    
    def get_scene_progress(self):
        ###Get current scene progress (0.0 to 1.0).###
        if not self.scene_data or not self.start_time:
            return 0.0
        
        current_time = time.time() - self.start_time
        total_duration = self.get_scene_duration()
        
        if total_duration <= 0:
            return 1.0
        
        return min(1.0, current_time / total_duration)
    
    def is_scene_complete(self):
        ###Check if scene has completed.###
        if not self.scene_data or not self.start_time:
            return False
        
        current_time = time.time() - self.start_time
        return current_time > self.get_scene_duration()

# Example usage and testing
if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Build path to scene file
    scene_file = os.path.join(script_dir, "..", "scenes", "room1", "intro.json")
    
    print(f"Looking for scene file at: {scene_file}")
    
    # Add the utils directory to Python path for importing other modules
    utils_dir = os.path.dirname(__file__)
    if utils_dir not in sys.path:
        sys.path.insert(0, utils_dir)
    
    try:
        from mqtt_client import MQTTClient
        from audio_handler import AudioHandler
        
        audio_dir = os.path.join(script_dir, "..", "audio")
        audio_handler = AudioHandler(audio_dir)
        parser = SceneParser(audio_handler)
        
        if parser.load_scene(scene_file):
            print("✅ Scene loaded successfully!")
            print(f"Scene duration: {parser.get_scene_duration()} seconds")
            
            # Try to connect to MQTT
            mqtt_client = MQTTClient("localhost", use_logging=True)
            mqtt_connected = mqtt_client.connect()
            
            if mqtt_connected:
                print("✅ Connected to MQTT broker")
            else:
                print("⚠️  No MQTT broker - running in simulation mode")
                mqtt_client = None
            
            parser.start_scene()
            
            # Simulate scene playback
            while not parser.is_scene_complete():
                actions = parser.get_current_actions(mqtt_client)
                if actions:
                    progress = parser.get_scene_progress() * 100
                    print(f"[{progress:.1f}%] Executing {len(actions)} actions:")
                    for action in actions:
                        print(f"  📡 {action['topic']} = {action['message']}")
                
                time.sleep(0.1)
            
            print("✅ Scene playback completed")
            
            if mqtt_connected:
                mqtt_client.disconnect()
            audio_handler.cleanup()
            
        else:
            print("❌ Failed to load scene file")
            print(f"Make sure the file exists at: {scene_file}")
            
    except ImportError as e:
        print(f"❌ Error importing modules: {e}")
        print("Make sure mqtt_client.py and audio_handler.py are in the utils directory")
"""
    create_file(f"{base_dir}/raspberry_pi/utils/scene_parser.py", scene_parser)

button_handler_improved = """
#!/usr/bin/env python3
import time
import atexit

# Try to import RPi.GPIO, fall back to mock if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("Warning: RPi.GPIO not available, using mock GPIO")
    GPIO_AVAILABLE = False
    
    # Mock GPIO for testing
    class MockGPIO:
        BCM = "BCM"
        IN = "IN"
        HIGH = 1
        LOW = 0
        PUD_UP = "PUD_UP"
        FALLING = "FALLING"
        
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode, pull_up_down=None): pass
        @staticmethod
        def input(pin): return MockGPIO.HIGH
        @staticmethod
        def add_event_detect(pin, edge, callback=None, bouncetime=None): pass
        @staticmethod
        def remove_event_detect(pin): pass
        @staticmethod
        def cleanup(): pass
    
    GPIO = MockGPIO()

class ImprovedButtonHandler:
    def __init__(self, pin, debounce_time=300):
        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        self.use_polling = False
        self.running = True
        
        if not GPIO_AVAILABLE:
            print(f"Warning: GPIO not available, button on pin {pin} will be simulated")
            self.use_polling = True
            return
        
        try:
            # Clean setup
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Try edge detection first
            try:
                GPIO.remove_event_detect(pin)  # Remove any existing detection
            except:
                pass
            
            time.sleep(0.1)  # Small delay
            
            GPIO.add_event_detect(pin, GPIO.FALLING, 
                                 callback=self._button_callback, 
                                 bouncetime=debounce_time)
            print(f"✅ Button handler setup with edge detection on GPIO {pin}")
            
        except Exception as e:
            print(f"⚠️  Edge detection failed ({e}), using polling method")
            self.use_polling = True
            self._last_state = GPIO.HIGH
        
        atexit.register(self.cleanup)
    
    def _button_callback(self, channel):
        current_time = time.time() * 1000
        if (current_time - self.last_press_time) > self.debounce_time:
            self.last_press_time = current_time
            if self.callback:
                print(f"🔘 Button pressed on GPIO {self.pin}")
                self.callback()
    
    def check_button_polling(self):
        if not self.use_polling or not GPIO_AVAILABLE:
            return
            
        try:
            current_state = GPIO.input(self.pin)
            
            # Button pressed (transition from HIGH to LOW)
            if hasattr(self, '_last_state') and self._last_state == GPIO.HIGH and current_state == GPIO.LOW:
                current_time = time.time() * 1000
                if (current_time - self.last_press_time) > self.debounce_time:
                    self.last_press_time = current_time
                    if self.callback:
                        print(f"🔘 Button pressed on GPIO {self.pin} (polling)")
                        self.callback()
            
            self._last_state = current_state
        except Exception as e:
            print(f"Error in button polling: {e}")
    
    def set_callback(self, callback_function):
        self.callback = callback_function
    
    def cleanup(self):
        self.running = False
        if GPIO_AVAILABLE:
            try:
                GPIO.remove_event_detect(self.pin)
                GPIO.cleanup()
            except:
                pass

# Test function
if __name__ == "__main__":
    def on_button_press():
        print("🎉 Button press detected!")
    
    button = ImprovedButtonHandler(17)
    button.set_callback(on_button_press)
    
    print("Testing button handler...")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            if button.use_polling:
                button.check_button_polling()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nTest completed")
    finally:
        button.cleanup()

    """
    create_file(f"{base_dir}/raspberry_pi/utils/button_handler_improved.py", button_handler_improved)

    audio_handler = """
#!/usr/bin/env python3
import pygame
import os
import sys

class AudioHandler:
    def __init__(self, audio_dir):
        self.audio_dir = audio_dir
        self.currently_playing = None
        
        # Initialize pygame mixer with better settings for various formats
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            print("✅ Audio handler initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing pygame mixer: {e}")
            sys.exit(1)
    
    def play_audio(self, audio_file):
        try:
            # Check if it's a direct filename or a command
            if audio_file.startswith("PLAY_"):
                # Legacy support - extract filename from command
                filename = audio_file.replace("PLAY_", "").lower()
                # Try different extensions
                for ext in ['.wav', '.mp3', '.ogg']:
                    test_file = filename + ext
                    full_path = os.path.join(self.audio_dir, test_file)
                    if os.path.exists(full_path):
                        audio_file = test_file
                        break
                else:
                    print(f"❌ Audio file not found for command: {audio_file}")
                    return False
            
            full_path = os.path.join(self.audio_dir, audio_file)
            
            if not os.path.exists(full_path):
                print(f"❌ Audio file not found: {full_path}")
                return False
            
            # Check file extension
            _, ext = os.path.splitext(audio_file.lower())
            if ext not in ['.wav', '.mp3', '.ogg']:
                print(f"⚠️  Unsupported audio format: {ext}")
                print("Supported formats: .wav, .mp3, .ogg")
                return False
            
            # Stop any currently playing audio
            if self.currently_playing:
                pygame.mixer.music.stop()
            
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.play()
            self.currently_playing = audio_file
            print(f"🎵 Playing audio: {audio_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error playing audio {audio_file}: {e}")
            return False
    
    def play_audio_with_volume(self, audio_file, volume=0.7):
        ###Play audio file with specified volume (0.0 to 1.0).###
        if self.play_audio(audio_file):
            pygame.mixer.music.set_volume(volume)
            print(f"🔊 Volume set to {volume}")
            return True
        return False
    
    def is_playing(self):
        ###Check if audio is currently playing.###
        return pygame.mixer.music.get_busy()
    
    def pause_audio(self):
        ###Pause currently playing audio.###
        try:
            if self.currently_playing and self.is_playing():
                pygame.mixer.music.pause()
                print(f"⏸️  Paused audio: {self.currently_playing}")
                return True
        except Exception as e:
            print(f"❌ Error pausing audio: {e}")
        return False
    
    def resume_audio(self):
        ###Resume paused audio.###
        try:
            pygame.mixer.music.unpause()
            print(f"▶️  Resumed audio: {self.currently_playing}")
            return True
        except Exception as e:
            print(f"❌ Error resuming audio: {e}")
            return False
    
    def stop_audio(self):
        ###Stop currently playing audio.###
        try:
            if self.currently_playing:
                pygame.mixer.music.stop()
                print(f"⏹️  Stopped audio: {self.currently_playing}")
                self.currently_playing = None
            return True
        except Exception as e:
            print(f"❌ Error stopping audio: {e}")
            return False
    
    def set_volume(self, volume):
        ###Set volume for currently playing audio (0.0 to 1.0).###
        try:
            volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
            pygame.mixer.music.set_volume(volume)
            print(f"🔊 Volume set to {volume}")
            return True
        except Exception as e:
            print(f"❌ Error setting volume: {e}")
            return False
    
    def list_audio_files(self):
        ###List all supported audio files in the audio directory.###
        try:
            if not os.path.exists(self.audio_dir):
                print(f"❌ Audio directory not found: {self.audio_dir}")
                return []
            
            supported_extensions = ['.wav', '.mp3', '.ogg']
            audio_files = []
            
            for file in os.listdir(self.audio_dir):
                _, ext = os.path.splitext(file.lower())
                if ext in supported_extensions:
                    audio_files.append(file)
            
            return sorted(audio_files)
        except Exception as e:
            print(f"❌ Error listing audio files: {e}")
            return []
    
    def cleanup(self):
        ###Clean up audio resources.###
        try:
            self.stop_audio()
            pygame.mixer.quit()
            print("🧹 Audio handler cleaned up")
        except Exception as e:
            print(f"❌ Error during audio cleanup: {e}")

# Example usage and testing
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(script_dir, "..", "audio")
    
    print(f"Audio directory: {audio_dir}")
    
    audio_handler = AudioHandler(audio_dir)
    
    # List available audio files
    print("📁 Available audio files:")
    files = audio_handler.list_audio_files()
    if files:
        for i, file in enumerate(files, 1):
            print(f"  {i}. {file}")
    else:
        print("  No audio files found")
    
    # Test audio playback if files exist
    if files:
        print(f"\n🎵 Testing playback of first file: {files[0]}")
        audio_handler.play_audio_with_volume(files[0], 0.5)
        
        import time
        print("Playing for 5 seconds...")
        time.sleep(5)
        
        audio_handler.stop_audio()
    
    audio_handler.cleanup()
    """
    create_file(f"{base_dir}/raspberry_pi/utils/button_handler_improved.py", audio_handler)
    # Create main Python script for Raspberry Pi
    main_script = """
#!/usr/bin/env python3

import os, time, configparser, sys, logging, signal, threading
from datetime import datetime

# Add current directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Clean logging setup
def setup_logging():
    class CleanFormatter(logging.Formatter):
        def format(self, record):
            timestamp = datetime.now().strftime('%H:%M:%S')
            level = record.levelname.ljust(7)
            return f"[{timestamp}] {level} {record.getMessage()}"
    
    logger = logging.getLogger('museum')
    logger.setLevel(logging.DEBUG)
    
    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CleanFormatter())
    logger.addHandler(console_handler)
    
    # Log files
    log_dir = os.path.expanduser("~/Documents/GitHub/museum-system/logs")
    os.makedirs(log_dir, exist_ok=True)
    
    for level, filename in [(logging.INFO, 'museum-info.log'), 
                           (logging.WARNING, 'museum-warnings.log'), 
                           (logging.ERROR, 'museum-errors.log')]:
        handler = logging.FileHandler(f"{log_dir}/{filename}")
        handler.setLevel(level)
        handler.setFormatter(CleanFormatter())
        logger.addHandler(handler)
    
    return logger

log = setup_logging()

# Import components
try:
    from utils.systemd_watchdog import SystemdWatchdog
    from utils.mqtt_client import MQTTClient
    from utils.scene_parser import SceneParser
    from utils.audio_handler import AudioHandler
    log.info("Core modules loaded")
except ImportError as e:
    log.error(f"Import failed: {e}")
    sys.exit(1)

# Button handler with fallback
try:
    from utils.button_handler_improved import ImprovedButtonHandler as ButtonHandler
    log.info("Button handler loaded")
except ImportError:
    log.warning("Using mock button")
    class MockButtonHandler:
        def __init__(self, pin):
            self.pin = pin
            self.callback = None
        def set_callback(self, callback): self.callback = callback
        def simulate_press(self): 
            if self.callback: self.callback()
        def cleanup(self): pass
    ButtonHandler = MockButtonHandler

class MuseumController:
    def __init__(self, config_file=None):
        # Config loading
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), "config", "config.ini")
        
        if not os.path.exists(config_file):
            log.error(f"Config missing: {config_file}")
            self.create_default_config(config_file)
        
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Config values
        broker_ip = self.config['MQTT']['BrokerIP']
        button_pin = int(self.config['GPIO']['ButtonPin'])
        self.room_id = self.config['Room']['ID']
        self.json_file_name = self.config['Json']['json_file_name']
        self.scenes_dir = "/home/admin/Documents/GitHub/museum-system/raspberry_pi/scenes"
        self.audio_dir = os.path.join(os.path.dirname(__file__), "audio")
        
        log.info(f"Room: {self.room_id}, MQTT: {broker_ip}, GPIO: {button_pin}")
        os.makedirs(self.scenes_dir, exist_ok=True)
        
        # Components init
        self.watchdog = SystemdWatchdog(logger=log)
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Init with error handling
        self.mqtt_client = self._safe_init(lambda: MQTTClient(broker_ip, client_id=f"rpi_room_{self.room_id}", use_logging=True), "MQTT")
        self.audio_handler = self._safe_init(lambda: AudioHandler(self.audio_dir), "Audio")
        self.scene_parser = self._safe_init(lambda: SceneParser(self.audio_handler), "Scene parser")
        self.button_handler = self._safe_init(lambda: ButtonHandler(button_pin), "Button")
        
        if self.button_handler:
            self.button_handler.set_callback(self.on_button_press)
        
        # State
        self.scene_running = False
        self.connected_to_broker = False
        self.last_heartbeat = time.time()
        self.health_check_interval = int(self.config['System'].get('health_check_interval', '30'))
    
    def _safe_init(self, init_func, name):
        try:
            return init_func()
        except Exception as e:
            log.error(f"{name} init failed: {e}")
            return None
    
    def _signal_handler(self, signum, frame):
        log.info(f"Signal {signum} received, shutting down...")
        self.shutdown_requested = True
    
    def create_default_config(self, config_file):
        config = configparser.ConfigParser()
        config['MQTT'] = {'BrokerIP': 'localhost', 'Port': '1883'}
        config['GPIO'] = {'ButtonPin': '17'}
        config['Room'] = {'ID': 'room1'}
        config['Scenes'] = {'Directory': '/home/admin/Documents/GitHub/museum-system/raspberry_pi/scenes'}
        config['Audio'] = {'Directory': 'audio'}
        
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as f:
            config.write(f)
        log.info(f"Default config created: {config_file}")
    
    def test_mqtt_connection(self):
        if not self.mqtt_client:
            log.error("MQTT client missing")
            return False
        
        broker_ip = self.config['MQTT']['BrokerIP']
        
        # Try main broker
        for attempt in range(1, 11):
            if self.shutdown_requested: return False
            log.info(f"MQTT attempt {attempt}/10 to {broker_ip}")
            
            try:
                if self.mqtt_client.connect(timeout=10):
                    self.connected_to_broker = True
                    log.info(f"MQTT connected on attempt {attempt}")
                    return True
            except Exception as e:
                log.warning(f"Attempt {attempt} failed: {e}")
            
            if attempt < 10:
                for _ in range(5):
                    if self.shutdown_requested: return False
                    time.sleep(1)
        
        # Try localhost fallback
        if broker_ip != 'localhost' and not self.shutdown_requested:
            log.info("Trying localhost fallback")
            self.mqtt_client.broker_host = 'localhost'
            
            for attempt in range(1, 11):
                if self.shutdown_requested: return False
                try:
                    if self.mqtt_client.connect(timeout=10):
                        self.connected_to_broker = True
                        log.info(f"Localhost connected on attempt {attempt}")
                        return True
                except Exception as e:
                    log.warning(f"Localhost attempt {attempt} failed: {e}")
                
                if attempt < 10:
                    for _ in range(5):
                        if self.shutdown_requested: return False
                        time.sleep(1)
        
        log.error("MQTT completely unavailable")
        return False
    
    def send_ready_notification(self):
        try:
            os.system('systemd-notify READY=1')
            log.info("Systemd READY sent")
        except Exception as e:
            log.warning(f"Systemd notify failed: {e}")
    
    def perform_health_check(self):
        try:
            self.last_heartbeat = time.time()
            issues = []
            
            if not self.connected_to_broker: issues.append("MQTT down")
            if not self.mqtt_client: issues.append("MQTT missing")
            
            # Watchdog check
            ws = self.watchdog.get_status()
            if ws['enabled']:
                if ws['status'] == 'stalled':
                    issues.append(f"WD stalled: {ws['message']}")
                elif ws['status'] == 'degraded':
                    issues.append(f"WD degraded: {ws['message']}")
            
            # Memory check
            try:
                import psutil
                if psutil.virtual_memory().percent > 90:
                    issues.append(f"High mem")
            except ImportError:
                pass
            
            if issues:
                log.warning(f"Health: {len(issues)} issues: {', '.join(issues)}")
                return False
            else:
                if not hasattr(self, '_hc_count'): self._hc_count = 0
                self._hc_count += 1
                if self._hc_count % 10 == 0:
                    if ws['enabled']:
                        log.info(f"Health #{self._hc_count}: OK (WD: {ws['heartbeat_count']} beats)")
                    else:
                        log.info(f"Health #{self._hc_count}: OK")
                return True
                
        except Exception as e:
            log.error(f"Health check failed: {e}")
            return False
    
    def on_button_press(self):
        if self.scene_running:
            log.warning("Scene running, ignoring button")
            return
        log.info("Button pressed, starting scene")
        self.start_default_scene()
    
    def start_default_scene(self):
        scene_path = os.path.join(self.scenes_dir, self.room_id, self.json_file_name)
        
        if not os.path.exists(scene_path):
            log.warning(f"Scene missing: {scene_path}")
            self.create_default_scene(scene_path)
        
        if not self.scene_parser:
            log.error("Scene parser unavailable")
            return
        
        log.info(f"Loading: {scene_path}")
        if self.scene_parser.load_scene(scene_path):
            self.scene_running = True
            self.scene_parser.start_scene()
            self.run_scene()
        else:
            log.error("Scene load failed")
    
    def create_default_scene(self, scene_path):
        import json
        
        default_scene = [
            {"timestamp": 0, "topic": f"{self.room_id}/light", "message": "ON"},
            {"timestamp": 2.0, "topic": f"{self.room_id}/audio", "message": "PLAY_WELCOME"},
            {"timestamp": 5.0, "topic": f"{self.room_id}/light", "message": "BLINK"},
            {"timestamp": 8.0, "topic": f"{self.room_id}/audio", "message": "STOP"},
            {"timestamp": 10.0, "topic": f"{self.room_id}/light", "message": "OFF"}
        ]
        
        os.makedirs(os.path.dirname(scene_path), exist_ok=True)
        with open(scene_path, 'w') as f:
            json.dump(default_scene, f, indent=2)
        log.info(f"Default scene created: {scene_path}")
    
    def run_scene(self):
        if not self.scene_parser.scene_data:
            log.error("No scene data")
            return
        
        start_time = time.time()
        max_time = max(action["timestamp"] for action in self.scene_parser.scene_data)
        log.info(f"Scene duration: {max_time}s")
        
        while time.time() - start_time <= max_time + 1 and not self.shutdown_requested:
            actions = self.scene_parser.get_current_actions(self.mqtt_client if self.connected_to_broker else None)
            
            if actions:
                current_time = time.time() - start_time
                for action in actions:
                    status = "" if self.connected_to_broker else " (sim)"
                    log.info(f"[{current_time:.1f}s] {action['topic']} = {action['message']}{status}")
            
            time.sleep(0.1)
        
        log.info("Scene completed")
        self.scene_running = False
    
    def run_interactive_mode(self):
        log.info("Interactive mode: 'b'=button, 's'=scene, 'status', 'watchdog', 'q'=quit")
        
        while not self.shutdown_requested:
            try:
                cmd = input("\n> ").strip().lower()
                
                if cmd in ['q', 'quit', 'exit']: break
                elif cmd in ['b', 'button']: self.on_button_press()
                elif cmd in ['s', 'scene']: self.start_default_scene()
                elif cmd == 'status':
                    ws = self.watchdog.get_status()
                    log.info(f"MQTT: {self.connected_to_broker}, Scene: {self.scene_running}, Room: {self.room_id}")
                    log.info(f"Watchdog: {'enabled' if ws['enabled'] else 'disabled'}")
                elif cmd == 'watchdog':
                    ws = self.watchdog.get_status()
                    if ws['enabled']:
                        log.info(f"WD: {ws['status']}, Beats: {ws['heartbeat_count']}, Uptime: {ws['uptime_seconds']/60:.1f}m")
                elif cmd == 'health':
                    healthy = self.perform_health_check()
                    log.info(f"Health: {'OK' if healthy else 'ISSUES'}")
                elif cmd == 'help':
                    log.info("Commands: button/b, scene/s, status, watchdog, health, quit/q")
                else:
                    log.warning("Unknown cmd. Type 'help'")
                    
            except (KeyboardInterrupt, EOFError): break
    
    def run(self):
        log.info("Starting Enhanced Museum Controller")
        
        self.watchdog.start()
        
        if not self.test_mqtt_connection():
            if self.shutdown_requested: return
            log.error("CRITICAL: No MQTT connection")
            sys.exit(1)
        
        self.send_ready_notification()
        log.info(f"System ready - {self.room_id} operational")
        
        last_health = time.time()
        last_mqtt = time.time()
        
        # Check for polling mode
        use_polling = hasattr(self.button_handler, 'use_polling') and self.button_handler.use_polling
        
        try:
            while not self.shutdown_requested:
                current_time = time.time()
                
                # Health checks
                if current_time - last_health > self.health_check_interval:
                    self.perform_health_check()
                    last_health = current_time
                
                # MQTT checks
                if current_time - last_mqtt > 15:
                    self.check_mqtt_status()
                    last_mqtt = current_time
                
                # Button polling if needed
                if use_polling and self.button_handler:
                    self.button_handler.check_button_polling()
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            if not self.shutdown_requested:
                log.info("Interactive mode")
                self.run_interactive_mode()
        
        self.cleanup()
    
    def cleanup(self):
        log.info("Cleanup started")
        self.watchdog.stop()
        
        for component, name in [(self.button_handler, "Button"), 
                               (self.audio_handler, "Audio")]:
            if component:
                try:
                    component.cleanup()
                    log.info(f"{name} cleaned")
                except Exception as e:
                    log.error(f"{name} cleanup error: {e}")
        
        if self.mqtt_client and self.connected_to_broker:
            try:
                self.mqtt_client.disconnect()
                log.info("MQTT disconnected")
            except Exception as e:
                log.error(f"MQTT disconnect error: {e}")
        
        log.info("Controller stopped cleanly")
    
    def check_mqtt_status(self):
        if not self.mqtt_client: return
        
        was_connected = self.connected_to_broker
        
        try:
            currently_connected = self.mqtt_client.is_connected()
            if hasattr(self.mqtt_client.client, 'is_connected'):
                currently_connected = currently_connected and self.mqtt_client.client.is_connected()
        except Exception as e:
            log.error(f"MQTT status check error: {e}")
            currently_connected = False
        
        self.connected_to_broker = currently_connected
        
        # Log only changes
        if was_connected and not currently_connected:
            log.warning("MQTT lost")
        elif not was_connected and currently_connected:
            log.info("MQTT restored")
        
        # Reconnect if needed
        if not currently_connected and not self.shutdown_requested:
            if self.mqtt_client.connect(timeout=5):
                log.info("MQTT reconnected")
                self.connected_to_broker = True

def main():
    log.info("Enhanced Museum System Starting")
    log.info("="*40)
    
    controller = None
    try:
        controller = MuseumController()
        controller.run()
    except Exception as e:
        log.error(f"Critical error: {e}")
        if controller: controller.cleanup()
        sys.exit(1)
    finally:
        if controller: controller.cleanup()

if __name__ == "__main__":
    main()
"""

    create_file(f"{base_dir}/raspberry_pi/main.py", main_script)
    os.chmod(f"{base_dir}/raspberry_pi/main.py", 0o755)  # Make executable
    print("\nProject structure created successfully!")
    print(f"Project created at: {os.path.abspath(base_dir)}")
    print("\nNext steps:")
    print("1. Install dependencies: pip install paho-mqtt RPi.GPIO")
    print("2. Set up MQTT broker")
    print("3. Configure Raspberry Pi and ESP32 devices")
    print("4. Test the system components")

if __name__ == "__main__":
    create_project_structure()