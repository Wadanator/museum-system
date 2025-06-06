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