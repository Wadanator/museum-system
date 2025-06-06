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
    def __init__(self):
        self.scene_data = None
        self.start_time = None
    
    def load_scene(self, scene_file):
        try:
            with open(scene_file, 'r') as file:
                self.scene_data = json.load(file)
            return True
        except Exception as e:
            print(f"Error loading scene: {e}")
            self.scene_data = None
            return False
    
    def start_scene(self):
        if not self.scene_data:
            print("No scene is loaded")
            return False
        
        self.start_time = time.time()
        return True
    
    def get_current_actions(self, mqtt_client):
        if not self.scene_data or not self.start_time:
            return []
        
        current_time = time.time() - self.start_time
        actions = []
        
        for action in self.scene_data:
            if action["timestamp"] <= current_time < action["timestamp"] + 0.1:
                actions.append(action)
                # Publish to MQTT
                mqtt_client.publish(action["topic"], action["message"], retain=False)
        
        return actions

# Example usage
if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Build path to scene file
    scene_file = os.path.join(script_dir, "..", "scenes", "room1", "intro.json")
    
    print(f"Looking for scene file at: {scene_file}")
    
    # Add the utils directory to Python path for importing mqtt_client
    utils_dir = os.path.dirname(__file__)
    if utils_dir not in sys.path:
        sys.path.insert(0, utils_dir)
    
    try:
        from mqtt_client import MQTTClient
        
        parser = SceneParser()
        if parser.load_scene(scene_file):
            print("Scene loaded successfully!")
            mqtt_client = MQTTClient("localhost", use_logging=True)
            if mqtt_client.connect():
                print("Connected to MQTT broker")
                parser.start_scene()
                # Simulate scene playback
                for i in range(15):
                    actions = parser.get_current_actions(mqtt_client)
                    if actions:
                        print(f"[{i}s] Executing actions: {actions}")
                    time.sleep(1)
                mqtt_client.disconnect()
                print("Scene playback completed")
            else:
                print("Failed to connect to MQTT broker")
        else:
            print("Failed to load scene file")
            print(f"Make sure the file exists at: {scene_file}")
    except ImportError as e:
        print(f"Error importing mqtt_client: {e}")
        print("Make sure mqtt_client.py is in the same directory") 

"""
    create_file(f"{base_dir}/raspberry_pi/utils/scene_parser.py", scene_parser)
    
    # Create button handler Python module
    button_handler = """#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import atexit
import sys

class ButtonHandler:
    def __init__(self, pin, debounce_time=300):
        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        self._use_polling = False

        # Use GPIO.BCM mode
        try:
            GPIO.setmode(GPIO.BCM)
        except Exception as e:
            print(f"Error setting GPIO mode: {e}")
            sys.exit(1)

        # Attempt to clean up any existing GPIO configuration
        try:
            GPIO.cleanup(self.pin)  # Clean only the specific pin
        except Exception as e:
            print(f"Warning: Failed to clean up GPIO pin {self.pin}: {e}")

        # Setup GPIO pin with pull-up resistor
        try:
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except Exception as e:
            print(f"Error setting up GPIO pin {self.pin}: {e}")
            sys.exit(1)

        # Setup edge detection
        try:
            GPIO.add_event_detect(self.pin, GPIO.FALLING, 
                                 callback=self._button_callback, 
                                 bouncetime=debounce_time)
        except RuntimeError as e:
            print(f"Error setting up edge detection on pin {self.pin}: {e}")
            print("Falling back to polling mode.")
            self._use_polling = True

        # Register cleanup function
        atexit.register(self.cleanup)

    def _button_callback(self, channel):
        current_time = time.time() * 1000  # Convert to milliseconds
        if (current_time - self.last_press_time) > self.debounce_time:
            self.last_press_time = current_time
            if self.callback:
                try:
                    self.callback()
                except Exception as e:
                    print(f"Error in callback: {e}")

    def _check_button_polling(self):
        if not hasattr(self, '_last_state'):
            self._last_state = GPIO.input(self.pin)

        current_state = GPIO.input(self.pin)
        if self._last_state == GPIO.HIGH and current_state == GPIO.LOW:
            current_time = time.time() * 1000
            if (current_time - self.last_press_time) > self.debounce_time:
                self.last_press_time = current_time
                if self.callback:
                    try:
                        self.callback()
                    except Exception as e:
                        print(f"Error in polling callback: {e}")
        self._last_state = current_state

    def set_callback(self, callback_function):
        self.callback = callback_function

    def cleanup(self):
        try:
            if not self._use_polling:
                GPIO.remove_event_detect(self.pin)
            GPIO.cleanup(self.pin)  # Clean only the specific pin
            print(f"Cleaned up GPIO pin {self.pin}")
        except Exception as e:
            print(f"Error during cleanup of pin {self.pin}: {e}")

# Example usage
if __name__ == "__main__":
    def on_button_press():
        print("Button pressed!")

    # Initialize button handler on GPIO17
    try:
        button = ButtonHandler(27)
        button.set_callback(on_button_press)
    except Exception as e:
        print(f"Failed to initialize button handler: {e}")
        sys.exit(1)

    print("Press the button (Ctrl+C to exit)...")
    try:
        while True:
            if button._use_polling:
                button._check_button_polling()
            time.sleep(0.1)  # Reduce CPU usage in polling mode
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        button.cleanup()
"""
    create_file(f"{base_dir}/raspberry_pi/utils/button_handler.py", button_handler)
    

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
        print("Test completed")
    finally:
        button.cleanup()

    """
    create_file(f"{base_dir}/raspberry_pi/utils/button_handler_improved.py", button_handler_improved)

    # Create main Python script for Raspberry Pi
    main_script = """
#!/usr/bin/env python3

import os
import time
import configparser
import sys

# Add the current directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from utils.mqtt_client import MQTTClient
    from utils.scene_parser import SceneParser
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the raspberry_pi directory")
    sys.exit(1)

# Import improved button handler or fall back to simulation
try:
        from utils.button_handler_improved import ImprovedButtonHandler as ButtonHandler
        print("✅ Using improved button handler")
except ImportError:
    print("⚠️  Button handler not available, using simulation")
    
    class MockButtonHandler:
        def __init__(self, pin):
            self.pin = pin
            self.callback = None
            print(f"Mock button handler created for GPIO {pin}")
        
        def set_callback(self, callback):
            self.callback = callback
        
        def simulate_press(self):
            if self.callback:
                print("🔘 Simulated button press")
                self.callback()
        
        def cleanup(self):
            pass
    
    ButtonHandler = MockButtonHandler

class FixedMuseumController:
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), "config", "config.ini")
        
        if not os.path.exists(config_file):
            print(f"❌ Config file not found: {config_file}")
            print("Creating default config...")
            self.create_default_config(config_file)
        
        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Get configuration values
        broker_ip = self.config['MQTT']['BrokerIP']
        button_pin = int(self.config['GPIO']['ButtonPin'])
        self.room_id = self.config['Room']['ID']
        self.scenes_dir = self.config['Scenes']['Directory']
        
        print(f"🏛️  Museum Controller for Room: {self.room_id}")
        print(f"📡 MQTT Broker: {broker_ip}")
        print(f"🔘 Button Pin: GPIO {button_pin}")
        
        # Initialize components with error handling
        try:
            self.mqtt_client = MQTTClient(broker_ip, client_id=f"rpi_room_{self.room_id}", use_logging=True)
        except Exception as e:
            print(f"❌ MQTT client initialization failed: {e}")
            self.mqtt_client = None
        
        try:
            self.scene_parser = SceneParser()
        except Exception as e:
            print(f"❌ Scene parser initialization failed: {e}")
            self.scene_parser = None
        
        try:
            self.button_handler = ButtonHandler(button_pin)
            self.button_handler.set_callback(self.on_button_press)
        except Exception as e:
            print(f"❌ Button handler initialization failed: {e}")
            self.button_handler = None
        
        # State
        self.scene_running = False
        self.connected_to_broker = False
    
    def create_default_config(self, config_file):
        config = configparser.ConfigParser()
        config['MQTT'] = {
            'BrokerIP': 'localhost',
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
        
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, 'w') as f:
            config.write(f)
        
        print(f"✅ Created default config: {config_file}")
    
    def test_mqtt_connection(self):
        if not self.mqtt_client:
            return False
        
        # Try current broker
        if self.mqtt_client.connect(timeout=3):
            self.connected_to_broker = True
            print("✅ Connected to MQTT broker")
            return True
        
        print("❌ Failed to connect to configured broker")
        
        # Try localhost as fallback
        if self.config['MQTT']['BrokerIP'] != 'localhost':
            print("🔄 Trying localhost as fallback...")
            self.mqtt_client.broker_host = 'localhost'
            if self.mqtt_client.connect(timeout=3):
                self.connected_to_broker = True
                print("✅ Connected to localhost broker")
                return True
        
        print("❌ No MQTT broker accessible")
        return False
    
    def on_button_press(self):
        if self.scene_running:
            print("⚠️  Scene already running, ignoring button press")
            return
        
        print("🔘 Button pressed! Starting default scene...")
        self.start_default_scene()
    
    def start_default_scene(self):
        scene_path = os.path.join(self.scenes_dir, self.room_id, "intro.json")
        
        if not os.path.exists(scene_path):
            print(f"❌ Scene file not found: {scene_path}")
            self.create_default_scene(scene_path)
        
        if not self.scene_parser:
            print("❌ Scene parser not available")
            return
        
        print(f"🎬 Loading scene: {scene_path}")
        if self.scene_parser.load_scene(scene_path):
            self.scene_running = True
            self.scene_parser.start_scene()
            self.run_scene()
        else:
            print("❌ Failed to load scene")
    
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
        
        print(f"✅ Created default scene: {scene_path}")
    
    def run_scene(self):
        if not self.scene_parser.scene_data:
            print("❌ No scene data to run")
            return
        
        start_time = time.time()
        max_time = max(action["timestamp"] for action in self.scene_parser.scene_data)
        
        print(f"🎬 Playing scene, duration: {max_time} seconds")
        
        while time.time() - start_time <= max_time + 1:
            actions = self.scene_parser.get_current_actions(self.mqtt_client if self.connected_to_broker else None)
            
            if actions:
                current_time = time.time() - start_time
                for action in actions:
                    print(f"[{current_time:.1f}s] 🎭 {action['topic']} = {action['message']}")
                    
                    # If MQTT is not connected, just simulate the action
                    if not self.connected_to_broker:
                        print(f"    (Simulated - no MQTT connection)")
            
            time.sleep(0.1)
        
        print("✅ Scene completed")
        self.scene_running = False
    
    def run_interactive_mode(self):
        print("\n🎮 Interactive Mode")
        print("Commands:")
        print("  'b' or 'button' - Simulate button press")
        print("  's' or 'scene' - Start default scene")
        print("  'q' or 'quit' - Exit")
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                
                if cmd in ['q', 'quit', 'exit']:
                    break
                elif cmd in ['b', 'button']:
                    self.on_button_press()
                elif cmd in ['s', 'scene']:
                    self.start_default_scene()
                elif cmd == 'status':
                    print(f"MQTT Connected: {self.connected_to_broker}")
                    print(f"Scene Running: {self.scene_running}")
                    print(f"Room ID: {self.room_id}")
                elif cmd == 'help':
                    print("Available commands: button, scene, status, quit")
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
    
    def run(self):
        print("🚀 Starting Museum Controller...")
        
        # Test MQTT connection
        mqtt_ok = self.test_mqtt_connection()
        
        if mqtt_ok:
            print("✅ System ready with MQTT")
        else:
            print("⚠️  System ready without MQTT (simulation mode)")
        
        print(f"🏛️  Museum controller for {self.room_id} is running")
        
        # Check if we have a working button handler
        if hasattr(self.button_handler, 'use_polling') and self.button_handler.use_polling:
            print("🔘 Using button polling mode")
            print("💡 Press Ctrl+C to enter interactive mode")
            
            try:
                while True:
                    if self.button_handler:
                        self.button_handler.check_button_polling()
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n🎮 Switching to interactive mode...")
                self.run_interactive_mode()
        else:
            print("🔘 Using button interrupt mode")
            print("💡 Press the button or Ctrl+C for interactive mode")
            
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n🎮 Switching to interactive mode...")
                self.run_interactive_mode()
        
        # Cleanup
        if self.button_handler:
            self.button_handler.cleanup()
        if self.mqtt_client and self.connected_to_broker:
            self.mqtt_client.disconnect()
        
        print("👋 Museum controller stopped")

def main():
    print("🏛️  Fixed Museum Automation System")
    print("=" * 40)
    
    try:
        controller = FixedMuseumController()
        controller.run()
    except Exception as e:
        print(f"❌ Critical error: {e}")
        print("💡 Try running the diagnostic script first")

if __name__ == "__main__":
    main()
"""

    create_file(f"{base_dir}/raspberry_pi/main.py", main_script)
    os.chmod(f"{base_dir}/raspberry_pi/main.py", 0o755)  # Make executable
    
    # Create architecture documentation
    arch_doc = """# Museum Automation System Architecture

## System Overview

The automated museum system uses a distributed architecture with MQTT communication:

- **MQTT Broker**: Central communication hub
- **Raspberry Pi Controllers**: One per room, manages scene playback
- **ESP32 Devices**: Control hardware (lights, audio, motors)

## Communication Flow

1. User presses button in a room
2. Raspberry Pi loads the corresponding scene from JSON file
3. Raspberry Pi publishes MQTT messages according to scene timestamps
4. ESP32 devices receive messages and control physical hardware

## MQTT Topics Structure

Topics follow a hierarchical structure: `room_id/device_type`

Examples:
- `room1/light`
- `room1/audio`
- `room2/motor`

## Hardware Components

### Raspberry Pi
- Controls the scene playback
- Connects to network via Ethernet
- Communicates with button input
- Manages JSON scene files

### ESP32 Devices
- Connect to network via Ethernet (using ESP32-Ethernet-Kit)
- Subscribe to MQTT topics
- Control physical hardware components
"""
    create_file(f"{base_dir}/docs/architecture.md", arch_doc)
    
    # Create MQTT topics documentation
    topics_doc = """# MQTT Topics Structure

## Topic Convention

All topics follow the pattern: `room_id/device_type`

## Standard Topics

### Light Control
- Topic: `roomX/light`
- Messages:
  - `ON`: Turn on all lights
  - `OFF`: Turn off all lights
  - `BLINK`: Blink lights sequence

### Audio Control
- Topic: `roomX/audio`
- Messages:
  - `PLAY_WELCOME`: Play welcome audio file
  - `PLAY_INFO`: Play information audio file
  - `STOP`: Stop audio playback

### Motor Control
- Topic: `roomX/motor`
- Messages:
  - `START`: Start motor movement
  - `STOP`: Stop motor movement
  - `SPEED:X`: Set motor speed (where X is a value)

## Room-Specific Examples

### Room 1
- `room1/light`
- `room1/audio`

### Room 2
- `room2/light`
- `room2/motor`

## Adding New Topics

When adding new functionality:
1. Follow the naming convention
2. Document the topic and messages
3. Ensure all devices are configured for the new topics
"""
    create_file(f"{base_dir}/docs/mqtt_topics.md", topics_doc)
    
    print("\nProject structure created successfully!")
    print(f"Project created at: {os.path.abspath(base_dir)}")
    print("\nNext steps:")
    print("1. Install dependencies: pip install paho-mqtt RPi.GPIO")
    print("2. Set up MQTT broker")
    print("3. Configure Raspberry Pi and ESP32 devices")
    print("4. Test the system components")

if __name__ == "__main__":
    create_project_structure()