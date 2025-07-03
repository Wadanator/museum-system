#!/usr/bin/env python3
import json
import time
import os
import sys
import logging

class SceneParser:
    def __init__(self, audio_handler=None, video_handler=None, logger=None):
        self.scene_data = None
        self.start_time = None
        self.audio_handler = audio_handler
        self.video_handler = video_handler
        self.executed_actions = set()  # Track executed actions to avoid duplicates
        self.logger = logger or logging.getLogger(__name__)
    
    def load_scene(self, scene_file):
        """Load scene from JSON file."""
        try:
            with open(scene_file, 'r') as file:
                self.scene_data = json.load(file)
            
            # Reset executed actions when loading new scene
            self.executed_actions = set()
            
            # Validate scene data
            if not isinstance(self.scene_data, list):
                self.logger.error("Scene data must be a list of actions")
                return False
            
            # Validate each action
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
        """Start scene playback."""
        if not self.scene_data:
            self.logger.error("No scene is loaded")
            return False
        
        self.start_time = time.time()
        self.executed_actions = set()
        self.logger.info("Scene started")
        return True
    
    def get_current_actions(self, mqtt_client):
        """Get actions that should execute at current time."""
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
                # Handle video commands locally
                elif action["topic"].endswith("/video"):
                    self._handle_video_command(action["message"])
                else:
                    # Publish other commands to MQTT
                    if mqtt_client:
                        mqtt_client.publish(action["topic"], action["message"], retain=False)
        
        return actions
    
    def _handle_audio_command(self, message):
        """Handle audio-specific commands."""
        if not self.audio_handler:
            self.logger.warning("No audio handler available")
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
                # Legacy format: PLAY_WELCOME -> welcome.wav/mp3/ogg
                self.audio_handler.play_audio(message.replace("PLAY_", ""))
                
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
            self.logger.error(f"Failed to handle audio command '{message}': {e}")
    
    def _handle_video_command(self, message):
        """Handle video-specific commands."""
        if not self.video_handler:
            self.logger.warning("No video handler available")
            return
        
        try:
            if message.startswith("PLAY_VIDEO:"):
                # Format: PLAY_VIDEO:filename.mp4
                filename = message.split(":")[1]
                self.video_handler.play_video(filename)
                
            elif message == "STOP_VIDEO":
                self.video_handler.stop_video()
                
            elif message == "PAUSE":
                self.video_handler.pause_video()
                
            elif message == "RESUME":
                self.video_handler.resume_video()
                
            elif message.startswith("SEEK:"):
                # Format: SEEK:seconds
                seconds = float(message.split(":")[1])
                self.video_handler.seek_video(seconds)
                
            else:
                # Direct filename
                self.video_handler.play_video(message)
                
        except Exception as e:
            self.logger.error(f"Failed to handle video command '{message}': {e}")
    
    def get_scene_duration(self):
        """Get total duration of the scene."""
        if not self.scene_data:
            return 0
        return max(action["timestamp"] for action in self.scene_data)
    
    def get_scene_progress(self):
        """Get current scene progress (0.0 to 1.0)."""
        if not self.scene_data or not self.start_time:
            return 0.0
        
        current_time = time.time() - self.start_time
        total_duration = self.get_scene_duration()
        
        if total_duration <= 0:
            return 1.0
        
        return min(1.0, current_time / total_duration)
    
    def is_scene_complete(self):
        """Check if scene has completed."""
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
        from video_handler import VideoHandler
        
        audio_dir = os.path.join(script_dir, "..", "audio")
        video_dir = os.path.join(script_dir, "..", "videos")
        audio_handler = AudioHandler(audio_dir)
        video_handler = VideoHandler(video_dir)
        parser = SceneParser(audio_handler, video_handler)
        
        if parser.load_scene(scene_file):
            print("Scene loaded successfully")
            print(f"Scene duration: {parser.get_scene_duration()} seconds")
            
            # Try to connect to MQTT
            mqtt_client = MQTTClient("localhost", use_logging=True)
            mqtt_connected = mqtt_client.connect()
            
            if mqtt_connected:
                print("Connected to MQTT broker")
            else:
                print("WARNING: No MQTT broker - running in simulation mode")
                mqtt_client = None
            
            parser.start_scene()
            
            # Simulate scene playback
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