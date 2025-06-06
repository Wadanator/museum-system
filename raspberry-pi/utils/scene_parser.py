#!/usr/bin/env python3
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
