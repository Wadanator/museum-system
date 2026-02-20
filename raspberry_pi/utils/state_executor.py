#!/usr/bin/env python3
"""
State Executor - Vykonáva akcie v stavoch (Refactored for Expandability)
"""
from utils.logging_setup import get_logger
from utils.mqtt.mqtt_contract import validate_publish

class StateExecutor:
    def __init__(self, mqtt_client=None, audio_handler=None, video_handler=None, logger=None):
        self.mqtt_client = mqtt_client
        self.audio_handler = audio_handler
        self.video_handler = video_handler
        self.logger = logger or get_logger("StateExecutor")
        
        # Tracking
        self.executed_timeline_actions = set()
        
        # --- KROK 1: Registrácia Handlerov ---
        # Tu definujeme, ktorá akcia ("action": "typ") volá ktorú funkciu.
        # Pre pridanie nového typu (napr. "lights") stačí pridať riadok sem.
        self.action_handlers = {
            "mqtt": self._execute_mqtt,
            "audio": self._execute_audio,
            "video": self._execute_video
        }
        
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
            if not isinstance(timeline_item, dict):
                self.logger.error(f"Invalid timeline item at index {i}: {timeline_item}")
                continue

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
                    actions = timeline_item["actions"]
                    if not isinstance(actions, list):
                        self.logger.error(f"Invalid actions list at index {i}: {actions}")
                        continue
                    for action in actions:
                        self._execute_action(action)
                
                self.executed_timeline_actions.add(action_id)
    
    def reset_timeline_tracking(self):
        """Resetuje tracking timeline akcií (pri zmene stavu)"""
        self.executed_timeline_actions.clear()
    
    def _execute_action(self, action):
        """Vykoná jednu akciu dynamicky podľa typu"""
        if not isinstance(action, dict):
            self.logger.error(f"Action must be a dict: {action}")
            return

        action_type = action.get("action")
        if not action_type:
            self.logger.error(f"Action missing 'action' type: {action}")
            return

        # --- KROK 1: Dynamické volanie ---
        handler = self.action_handlers.get(action_type)
        
        if handler:
            try:
                handler(action)
            except Exception as e:
                self.logger.error(f"Error executing action '{action_type}': {e}")
        else:
            self.logger.warning(f"Unknown action type: {action_type}")

    # --- Konkrétne implementácie ---

    def _execute_mqtt(self, action):
        """Pošle MQTT správu"""
        topic = action.get("topic")
        message = action.get("message")

        if not isinstance(topic, str) or not topic.strip():
            self.logger.error(f"MQTT action ignored: invalid or empty topic: {action}")
            return

        # message môže byť bool/number, preto kontrolujeme explicitne len None/empty string
        if message is None or (isinstance(message, str) and not message.strip()):
            self.logger.error(f"MQTT action ignored: message is None/empty string: {action}")
            return

        is_valid, validation_error = validate_publish(topic, message)
        if not is_valid:
            self.logger.error(f"MQTT action ignored by contract validation: {validation_error}")
            return

        if self.mqtt_client and self.mqtt_client.is_connected():
            try:
                success = self.mqtt_client.publish(topic, message, retain=False)
                if success:
                    self.logger.debug(f"MQTT: {topic} = {message}")
                else:
                    self.logger.error(f"MQTT publish failed: {topic}")
            except Exception as exc:
                self.logger.error(f"MQTT publish raised exception for {topic}: {exc}")
        else:
            self.logger.warning(f"MQTT not connected (simulation): {topic} = {message}")

    def _execute_audio(self, action):
        """Spustí audio príkaz"""
        message = action.get("message")

        if not message:
            self.logger.error(f"Audio action missing message: {action}")
            return

        if self.audio_handler:
            try:
                success = self.audio_handler.handle_command(message)
            except Exception as exc:
                self.logger.error(f"Audio handler raised exception for '{message}': {exc}")
                success = False

            if success:
                self.logger.debug(f"Audio: {message}")
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
            try:
                success = self.video_handler.handle_command(message)
            except Exception as exc:
                self.logger.error(f"Video handler raised exception for '{message}': {exc}")
                success = False

            if success:
                self.logger.debug(f"Video: {message}")
            else:
                self.logger.error(f"Video command failed: {message}")
        else:
            self.logger.warning(f"No video handler (simulation): {message}")
