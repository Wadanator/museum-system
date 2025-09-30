#!/usr/bin/env python3
"""
State Executor - Vykonáva akcie v stavoch
"""
import time
from utils.logging_setup import get_logger

class StateExecutor:
    def __init__(self, mqtt_client=None, audio_handler=None, video_handler=None, logger=None):
        self.mqtt_client = mqtt_client
        self.audio_handler = audio_handler
        self.video_handler = video_handler
        self.logger = logger or get_logger("StateExecutor")
        
        # Tracking
        self.executed_timeline_actions = set()
        
    def execute_onEnter(self, state_data):
        """Vykoná onEnter akcie (okamžite pri vstupe do stavu)"""
        actions = state_data.get("onEnter", [])
        if not actions:
            return
        
        self.logger.debug(f"Executing onEnter: {len(actions)} actions")
        for action in actions:
            self._execute_action(action)
    
    def execute_onExit(self, state_data):
        """Vykoná onExit akcie (pri odchode zo stavu)"""
        actions = state_data.get("onExit", [])
        if not actions:
            return
        
        self.logger.debug(f"Executing onExit: {len(actions)} actions")
        for action in actions:
            self._execute_action(action)
    
    def check_and_execute_timeline(self, state_data, state_elapsed_time):
        """Skontroluje a vykoná timeline akcie (časované v rámci stavu)"""
        timeline = state_data.get("timeline", [])
        if not timeline:
            return
        
        for i, timeline_item in enumerate(timeline):
            trigger_time = timeline_item.get("at", 0)
            action_id = f"{id(state_data)}_{i}_{trigger_time}"
            
            # Ak už bola vykonaná, preskočíme
            if action_id in self.executed_timeline_actions:
                continue
            
            # Ak je čas, vykonáme
            if state_elapsed_time >= trigger_time:
                self.logger.debug(f"Timeline trigger at {trigger_time}s")
                
                # Môže byť jedna akcia alebo viac akcií
                if "action" in timeline_item:
                    self._execute_action(timeline_item)
                elif "actions" in timeline_item:
                    for action in timeline_item["actions"]:
                        self._execute_action(action)
                
                self.executed_timeline_actions.add(action_id)
    
    def reset_timeline_tracking(self):
        """Resetuje tracking timeline akcií (pri zmene stavu)"""
        self.executed_timeline_actions.clear()
    
    def _execute_action(self, action):
        """Vykoná jednu akciu"""
        action_type = action.get("action")
        
        if action_type == "mqtt":
            self._execute_mqtt(action)
        elif action_type == "audio":
            self._execute_audio(action)
        elif action_type == "video":
            self._execute_video(action)
        else:
            self.logger.warning(f"Unknown action type: {action_type}")
    
    def _execute_mqtt(self, action):
        """Pošle MQTT správu"""
        topic = action.get("topic")
        message = action.get("message")
        
        if not topic or not message:
            self.logger.error(f"MQTT action missing topic or message: {action}")
            return
        
        if self.mqtt_client and self.mqtt_client.is_connected():
            success = self.mqtt_client.publish(topic, message, retain=False)
            if success:
                self.logger.info(f"MQTT: {topic} = {message}")
            else:
                self.logger.error(f"MQTT publish failed: {topic}")
        else:
            self.logger.warning(f"MQTT not connected (simulation): {topic} = {message}")
    
    def _execute_audio(self, action):
        """Spustí audio príkaz"""
        message = action.get("message")
        
        if not message:
            self.logger.error(f"Audio action missing message: {action}")
            return
        
        if self.audio_handler:
            success = self.audio_handler.handle_command(message)
            if success:
                self.logger.info(f"Audio: {message}")
            else:
                self.logger.error(f"Audio command failed: {message}")
        else:
            self.logger.warning(f"No audio handler (simulation): {message}")
    
    def _execute_video(self, action):
        """Spustí video príkaz"""
        message = action.get("message")
        
        if not message:
            self.logger.error(f"Video action missing message: {action}")
            return
        
        if self.video_handler:
            success = self.video_handler.handle_command(message)
            if success:
                self.logger.info(f"Video: {message}")
            else:
                self.logger.error(f"Video command failed: {message}")
        else:
            self.logger.warning(f"No video handler (simulation): {message}")