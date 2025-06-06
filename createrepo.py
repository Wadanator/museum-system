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
        f"{base_dir}/raspberry-pi",
        f"{base_dir}/raspberry-pi/config",
        f"{base_dir}/raspberry-pi/scenes",
        f"{base_dir}/raspberry-pi/scenes/room1",
        f"{base_dir}/raspberry-pi/scenes/room2",
        f"{base_dir}/raspberry-pi/utils",
        f"{base_dir}/raspberry-pi/service",
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
- `raspberry-pi/`: Code for the Raspberry Pi scene controllers
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
        'BrokerIP': '192.168.1.100',
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
    
    with open(f"{base_dir}/raspberry-pi/config/config.ini", 'w') as configfile:
        config.write(configfile)
    print(f"Created file: {base_dir}/raspberry-pi/config/config.ini")
    
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
    
    with open(f"{base_dir}/raspberry-pi/scenes/room1/intro.json", 'w') as f:
        json.dump(scene, f, indent=2)
    print(f"Created file: {base_dir}/raspberry-pi/scenes/room1/intro.json")
    
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
    
    with open(f"{base_dir}/raspberry-pi/scenes/room2/intro.json", 'w') as f:
        json.dump(scene2, f, indent=2)
    print(f"Created file: {base_dir}/raspberry-pi/scenes/room2/intro.json")
    
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
const char* mqtt_server = "192.168.1.100";
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
ExecStart=/usr/bin/python3 /home/pi/museum-system/raspberry-pi/main.py
WorkingDirectory=/home/pi/museum-system/raspberry-pi
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
    create_file(f"{base_dir}/raspberry-pi/service/museum_service.service", systemd_service)
    
    # Create MQTT client Python module
    mqtt_client = """#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time
import threading
import logging

# Nastavenie loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/museum-mqtt.log')
        #sudo touch /var/log/museum-mqtt.log
        #sudo chown pi:pi /var/log/museum-mqtt.log
        #sudo chmod 664 /var/log/museum-mqtt.log
    ]
)
logger = logging.getLogger('mqtt_client')

class MQTTClient:
    def __init__(self, broker_ip, client_id="rpi_controller", port=1883, use_logging=True):
        self.client = mqtt.Client(client_id)
        self.broker_ip = broker_ip
        self.port = port
        self.connected = False
        self.stopping = False
        self.reconnect_thread = None
        self.reconnect_delay = 5  # sekundy
        self.max_reconnect_delay = 300  # max 5 minút
        self.use_logging = use_logging
        
        # Setup callback functions
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
    def log_info(self, message):
        if self.use_logging:
            logger.info(message)
        else:
            print(message)
            
    def log_warning(self, message):
        if self.use_logging:
            logger.warning(message)
        else:
            print(f"WARNING: {message}")
            
    def log_error(self, message):
        if self.use_logging:
            logger.error(message)
        else:
            print(f"ERROR: {message}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log_info(f"Pripojené k MQTT brokeru na {self.broker_ip}")
            self.connected = True
            self.reconnect_delay = 5  # reset delay po úspešnom pripojení
        else:
            self.log_error(f"Nepodarilo sa pripojiť k MQTT brokeru, návratový kód: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        self.log_warning("Odpojené od MQTT brokera")
        self.connected = False
        
        # Automatické opätovné pripojenie, ak nejde o úmyselné zastavenie
        if not self.stopping and self.reconnect_thread is None:
            self.reconnect_thread = threading.Thread(target=self.reconnect_loop)
            self.reconnect_thread.daemon = True
            self.reconnect_thread.start()
    
    def reconnect_loop(self):

        while not self.connected and not self.stopping:
            self.log_info(f"Pokus o opätovné pripojenie k MQTT za {self.reconnect_delay} sekúnd...")
            time.sleep(self.reconnect_delay)
            
            try:
                self.client.reconnect()
                # Ak sa dostaneme sem bez výnimky, on_connect sa spustí samostatne
            except Exception as e:
                self.log_error(f"Chyba pri pokuse o opätovné pripojenie: {e}")
                # Zvýš interval pre ďalší pokus (exponenciálny backoff)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        
        self.reconnect_thread = None
        
    def connect(self):
        try:
            self.client.connect(self.broker_ip, self.port, 60)
            self.client.loop_start()
            # Počkaj na pripojenie
            for _ in range(5):
                if self.connected:
                    return True
                time.sleep(1)
            
            # Ak sme sa nedostali sem, začni automatické opätovné pripojenie
            if not self.connected and self.reconnect_thread is None:
                self.reconnect_thread = threading.Thread(target=self.reconnect_loop)
                self.reconnect_thread.daemon = True
                self.reconnect_thread.start()
            
            return self.connected
        except Exception as e:
            self.log_error(f"Chyba pri pripájaní k MQTT brokeru: {e}")
            
            # Začni automatické opätovné pripojenie
            if self.reconnect_thread is None:
                self.reconnect_thread = threading.Thread(target=self.reconnect_loop)
                self.reconnect_thread.daemon = True
                self.reconnect_thread.start()
            
            return False
    
    def publish(self, topic, message, retain=False):

        if not self.connected:
            self.log_warning(f"Nie je pripojené k MQTT brokeru, správa do {topic} nebola odoslaná")
            return False
        
        result = self.client.publish(topic, message, retain=retain)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.log_info(f"Správa publikovaná do {topic}: {message}")
            return True
        else:
            self.log_error(f"Chyba pri publikovaní správy: {result.rc}")
            return False
    
    def subscribe(self, topic, callback=None):

        if callback:
            # Nastav lokálny callback pre túto tému
            self.client.message_callback_add(topic, callback)
        
        self.client.subscribe(topic)
        self.log_info(f"Prihlásené na odber témy: {topic}")
    
    def disconnect(self):
        self.stopping = True
        self.client.loop_stop()
        self.client.disconnect()
        self.log_info("MQTT klient odpojený")

# Example usage
if __name__ == "__main__":
    client = MQTTClient("localhost", use_logging=False)  # MQTT broker address
    if client.connect():
        client.publish("test/topic", "Test message")
        time.sleep(2)
        client.disconnect()
"""
    create_file(f"{base_dir}/raspberry-pi/utils/mqtt_client.py", mqtt_client)
    
    # Create scene parser Python module
    scene_parser = """#!/usr/bin/env python3
import json
import time

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
    import sys
    sys.path.append('..')  # For importing mqtt_client
    from mqtt_client import MQTTClient
    
    parser = SceneParser()
    if parser.load_scene("../scenes/room1/intro.json"):
        mqtt_client = MQTTClient("localhost")
        if mqtt_client.connect():
            parser.start_scene()
            # Simulate scene playback
            for _ in range(15):
                actions = parser.get_current_actions(mqtt_client)
                if actions:
                    print(f"Executing actions: {actions}")
                time.sleep(1)
            mqtt_client.disconnect()
"""
    create_file(f"{base_dir}/raspberry-pi/utils/scene_parser.py", scene_parser)
    
    # Create button handler Python module
    button_handler = """#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

class ButtonHandler:
    def __init__(self, pin, debounce_time=300):

        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Setup edge detection
        GPIO.add_event_detect(pin, GPIO.FALLING, 
                             callback=self._button_callback, 
                             bouncetime=debounce_time)
    
    def _button_callback(self, channel):
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check time difference for debouncing
        if (current_time - self.last_press_time) > self.debounce_time:
            self.last_press_time = current_time
            if self.callback:
                self.callback()
    
    def set_callback(self, callback_function):
        self.callback = callback_function
    
    def cleanup(self):
        GPIO.remove_event_detect(self.pin)

# Example usage
if __name__ == "__main__":
    def on_button_press():
        print("Button pressed!")
    
    button = ButtonHandler(17)  # GPIO17
    button.set_callback(on_button_press)
    
    try:
        print("Press the button (Ctrl+C to exit)...")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Program terminated")
    finally:
        button.cleanup()
        GPIO.cleanup()
"""
    create_file(f"{base_dir}/raspberry-pi/utils/button_handler.py", button_handler)
    
    # Create main Python script for Raspberry Pi
    main_script = """#!/usr/bin/env python3
import os
import time
import configparser
from utils.mqtt_client import MQTTClient
from utils.scene_parser import SceneParser
from utils.button_handler import ButtonHandler
import RPi.GPIO as GPIO

class MuseumController:
    def __init__(self, config_file="config/config.ini"):
        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Get settings
        broker_ip = self.config['MQTT']['BrokerIP']
        button_pin = int(self.config['GPIO']['ButtonPin'])
        self.room_id = self.config['Room']['ID']
        self.scenes_dir = self.config['Scenes']['Directory']
        
        # Initialize components
        self.mqtt_client = MQTTClient(broker_ip, f"rpi_room_{self.room_id}", use_logging=False)
        self.scene_parser = SceneParser()
        self.button_handler = ButtonHandler(button_pin)
        
        # Set button callback function
        self.button_handler.set_callback(self.start_default_scene)
        
        # State
        self.scene_running = False
    
    def start_default_scene(self):
        if self.scene_running:
            print("Scene already running, ignoring button press")
            return
        
        default_scene = os.path.join(self.scenes_dir, self.room_id, "intro.json")
        if not os.path.exists(default_scene):
            print(f"Error: Scene file {default_scene} does not exist")
            return
        
        print(f"Starting scene: {default_scene}")
        if self.scene_parser.load_scene(default_scene):
            self.scene_running = True
            self.scene_parser.start_scene()
            self.run_scene()
    
    def run_scene(self):
        start_time = time.time()
        # Get maximum scene time
        max_time = 0
        for action in self.scene_parser.scene_data:
            if action["timestamp"] > max_time:
                max_time = action["timestamp"]
        
        print(f"Playing scene, duration: {max_time} seconds")
        
        # Main scene playback loop
        while time.time() - start_time <= max_time + 1:
            actions = self.scene_parser.get_current_actions(self.mqtt_client)
            if actions:
                current_time = time.time() - start_time
                for action in actions:
                    print(f"[{current_time:.2f}s] Executing: {action['topic']} = {action['message']}")
            time.sleep(0.1)
        
        print("Scene completed")
        self.scene_running = False
    
    def run(self):
        if not self.mqtt_client.connect():
            print("Cannot connect to MQTT broker, exiting")
            return
        
        print(f"Museum controller for room {self.room_id} is ready")
        print("Press the button to start a scene...")
        
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Program terminated by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        if hasattr(self, 'button_handler'):
            self.button_handler.cleanup()
        if hasattr(self, 'mqtt_client'):
            self.mqtt_client.disconnect()
        GPIO.cleanup()

if __name__ == "__main__":
    controller = MuseumController()
    controller.run()
"""
    create_file(f"{base_dir}/raspberry-pi/main.py", main_script)
    os.chmod(f"{base_dir}/raspberry-pi/main.py", 0o755)  # Make executable
    
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