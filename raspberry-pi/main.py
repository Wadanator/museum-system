#!/usr/bin/env python3
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
