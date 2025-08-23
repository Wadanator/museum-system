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

    # Action Processing with MQTT Feedback Integration
    def get_current_actions(self, mqtt_client):
        if not self.scene_data or not self.start_time:
            return []
        
        current_time = time.time() - self.start_time
        actions = []
        
        # NEW: Enable MQTT feedback tracking when scene starts
        if mqtt_client and hasattr(mqtt_client, 'feedback_tracker'):
            if mqtt_client.feedback_tracker and not mqtt_client.feedback_tracker.feedback_enabled:
                mqtt_client.feedback_tracker.enable_feedback_tracking()
        
        for i, action in enumerate(self.scene_data):
            action_id = f"{i}_{action['timestamp']}"
            
            if action["timestamp"] <= current_time and action_id not in self.executed_actions:
                actions.append(action)
                self.executed_actions.add(action_id)
                
                # Handle local audio/video (no MQTT feedback needed)
                if action["topic"].endswith("/audio"):
                    self._handle_audio_command(action["message"])
                elif action["topic"].endswith("/video"):
                    self._handle_video_command(action["message"])
                else:
                    # Send MQTT command (with automatic feedback tracking)
                    if mqtt_client:
                        success = mqtt_client.publish(action["topic"], action["message"], retain=False)
                        if not success:
                            self.logger.error(f"Failed to publish MQTT message: {action['topic']}")
        
        return actions
    
    def stop_scene(self, mqtt_client=None):
        """Stop the current scene and disable MQTT feedback tracking."""
        if mqtt_client and hasattr(mqtt_client, 'feedback_tracker'):
            if mqtt_client.feedback_tracker:
                mqtt_client.feedback_tracker.disable_feedback_tracking()
        
        self.logger.info("Scene stopped")

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