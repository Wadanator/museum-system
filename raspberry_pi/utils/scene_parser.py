#!/usr/bin/env python3
import json
import time
import os
import logging
import sys
from utils.logging_setup import get_logger

class SceneParser:
    def __init__(self, audio_handler=None, video_handler=None, logger=None):
        self.scene_data = None
        self.start_time = None
        self.audio_handler = audio_handler
        self.video_handler = video_handler
        self.executed_actions = set()
        self.logger = logger or get_logger("Scene_Parser")

    # Scene Management
    def load_scene(self, scene_file):
        try:
            with open(scene_file, 'r') as file:
                self.scene_data = json.load(file)
            
            self.executed_actions = set()
            
            if not isinstance(self.scene_data, list):
                self.logger.error("Scene data must be a list of actions")
                return False
            
            for i, action in enumerate(self.scene_data):
                if not all(key in action for key in ['timestamp', 'topic', 'message']):
                    self.logger.error(f"Action {i} missing required fields (timestamp, topic, message)")
                    return False
            
            self.logger.info(f"Scene loaded: {len(self.scene_data)} actions")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load scene: {e}")
            self.scene_data = None
            return False

    def start_scene(self):
        if not self.scene_data:
            self.logger.error("No scene is loaded")
            return False
        
        self.start_time = time.time()
        self.executed_actions = set()
        self.logger.info("Scene started")
        return True

    # Action Processing
    def get_current_actions(self, mqtt_client):
        if not self.scene_data or not self.start_time:
            return []
        
        current_time = time.time() - self.start_time
        actions = []
        
        for i, action in enumerate(self.scene_data):
            action_id = f"{i}_{action['timestamp']}"
            
            if action["timestamp"] <= current_time and action_id not in self.executed_actions:
                actions.append(action)
                self.executed_actions.add(action_id)
                
                if action["topic"].endswith("/audio"):
                    self._handle_audio_command(action["message"])
                elif action["topic"].endswith("/video"):
                    self._handle_video_command(action["message"])
                else:
                    if mqtt_client:
                        mqtt_client.publish(action["topic"], action["message"], retain=False)
        
        return actions

    def _handle_audio_command(self, message):
        if not self.audio_handler:
            self.logger.warning("No audio handler available")
            return False
    
        return self.audio_handler.handle_command(message)

    def _handle_video_command(self, message):
        if not self.video_handler:
            self.logger.warning("No video handler available")
            return False
        
        return self.video_handler.handle_command(message)

    # Scene Status
    def get_scene_duration(self):
        if not self.scene_data:
            return 0
        return max(action["timestamp"] for action in self.scene_data)

    def get_scene_progress(self):
        if not self.scene_data or not self.start_time:
            return 0.0
        
        current_time = time.time() - self.start_time
        total_duration = self.get_scene_duration()
        
        if total_duration <= 0:
            return 1.0
        
        return min(1.0, current_time / total_duration)

    def is_scene_complete(self):
        if not self.scene_data or not self.start_time:
            return False
        
        current_time = time.time() - self.start_time
        return current_time > self.get_scene_duration()

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scene_file = os.path.join(script_dir, "..", "scenes", "room1", "intro.json")
    
    print(f"Looking for scene file at: {scene_file}")
    
    utils_dir = os.path.dirname(__file__)
    if utils_dir not in sys.path:
        sys.path.insert(0, utils_dir)
    
    try:
        from mqtt_client import MQTTClient
        from audio_handler import AudioHandler
        from video_handler import VideoHandler
        
        audio_dir = os.path.join(script_dir, "..", "audio")
        video_dir = os.path.join(script_dir, "..", "videos")
        audio_handler = AudioHandler(audio_dir)
        video_handler = VideoHandler(video_dir)
        parser = SceneParser(audio_handler, video_handler)
        
        if parser.load_scene(scene_file):
            print("Scene loaded successfully")
            print(f"Scene duration: {parser.get_scene_duration()} seconds")
            
            mqtt_client = MQTTClient("localhost", use_logging=True)
            mqtt_connected = mqtt_client.connect()
            
            if mqtt_connected:
                print("Connected to MQTT broker")
            else:
                print("WARNING: No MQTT broker - running in simulation mode")
                mqtt_client = None
            
            parser.start_scene()
            
            while not parser.is_scene_complete():
                actions = parser.get_current_actions(mqtt_client)
                if actions:
                    progress = parser.get_scene_progress() * 100
                    print(f"[{progress:.1f}%] Executing {len(actions)} actions:")
                    for action in actions:
                        print(f"  MQTT: {action['topic']} = {action['message']}")
                
                time.sleep(0.1)
            
            print("Scene playback completed")
            
            if mqtt_connected:
                mqtt_client.disconnect()
            audio_handler.cleanup()
            video_handler.cleanup()
            
        else:
            print("ERROR: Failed to load scene file")
            print(f"Make sure the file exists at: {scene_file}")
            
    except ImportError as e:
        print(f"ERROR: Failed to import modules: {e}")
        print("Make sure mqtt_client.py, audio_handler.py, and video_handler.py are in the utils directory")