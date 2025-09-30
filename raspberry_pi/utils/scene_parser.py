#!/usr/bin/env python3
"""
Scene Parser - State Machine Version
Kompletná náhrada timestamp systému
"""
import json
import time
from utils.logging_setup import get_logger
from utils.state_machine import StateMachine
from utils.state_executor import StateExecutor
from utils.transition_manager import TransitionManager

class SceneParser:
    def __init__(self, mqtt_client=None, audio_handler=None, video_handler=None, logger=None):
        self.logger = logger or get_logger("Scene_Parser")
        
        # Handlers
        self.mqtt_client = mqtt_client
        self.audio_handler = audio_handler
        self.video_handler = video_handler
        
        # State machine components
        self.state_machine = StateMachine(logger=self.logger)
        self.state_executor = StateExecutor(
            mqtt_client=mqtt_client,
            audio_handler=audio_handler,
            video_handler=video_handler,
            logger=self.logger
        )
        self.transition_manager = TransitionManager(logger=self.logger)
        
        # Scene data reference (pre kompatibilitu)
        self.scene_data = None
        self.start_time = None
    
    def load_scene(self, scene_file):
        """Načíta state machine scénu"""
        success = self.state_machine.load_scene(scene_file)
        
        if success:
            # Pre kompatibilitu s existujúcim kódom
            self.scene_data = self.state_machine.states
        
        return success
    
    def start_scene(self):
        if not self.state_machine.states:
            self.logger.error("No scene loaded")
            return False
        
        self.transition_manager.clear_events()
        self.logger.debug("Cleared old MQTT events before scene start")
        
        # Enable MQTT feedback tracking
        if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
            if self.mqtt_client.feedback_tracker:
                self.mqtt_client.feedback_tracker.enable_feedback_tracking()
        
        # Start state machine
        success = self.state_machine.start()
        
        if success:
            self.start_time = self.state_machine.scene_start_time
            
            # Execute onEnter of initial state
            state_data = self.state_machine.get_current_state_data()
            if state_data:
                self.state_executor.execute_onEnter(state_data)
        
        return success
        
    def process_scene(self):
        """
        Hlavná processing metóda - volá sa v loope z main.py
        Vráti True ak scéna stále beží, False ak skončila
        """
        if self.state_machine.is_finished():
            return False
        
        # Get current state
        state_data = self.state_machine.get_current_state_data()
        if not state_data:
            return False
        
        # Get elapsed time in current state
        state_elapsed = self.state_machine.get_state_elapsed_time()
        
        # Check and execute timeline actions
        self.state_executor.check_and_execute_timeline(state_data, state_elapsed)
        
        # Check transitions
        next_state = self.transition_manager.check_transitions(state_data, state_elapsed)
        
        if next_state:
            # Execute onExit of current state
            self.state_executor.execute_onExit(state_data)
            
            # Change state
            self.state_machine.goto_state(next_state)
            
            # Clear tracking
            self.state_executor.reset_timeline_tracking()
            self.transition_manager.clear_events()
            
            # If not END, execute onEnter of new state
            if not self.state_machine.is_finished():
                new_state_data = self.state_machine.get_current_state_data()
                if new_state_data:
                    self.state_executor.execute_onEnter(new_state_data)
        
        return True
    
    def stop_scene(self, mqtt_client=None):
        """Zastaví scénu"""
        # Disable MQTT feedback tracking
        mqtt = mqtt_client or self.mqtt_client
        if mqtt and hasattr(mqtt, 'feedback_tracker'):
            if mqtt.feedback_tracker:
                mqtt.feedback_tracker.disable_feedback_tracking()
        
        self.logger.info("Scene stopped")
    
    def get_progress_info(self):
        """Vráti progress info pre web dashboard"""
        return self.state_machine.get_progress_info()
    
    def is_scene_complete(self):
        """Skontroluje či scéna skončila"""
        return self.state_machine.is_finished()
    
    # Compatibility methods (pre starý kód)
    
    def get_scene_duration(self):
        """Pre kompatibilitu - vráti 0 (state machine nemá fixed duration)"""
        return 0
    
    def get_scene_progress(self):
        """Pre kompatibilitu - vráti progress na základe stavov"""
        if not self.state_machine.states:
            return 0.0
        
        completed = len(self.state_machine.state_history)
        total = self.state_machine.total_states
        
        if total == 0:
            return 1.0
        
        return min(1.0, completed / total)
    
    def register_mqtt_event(self, topic, message):
        """Registruje MQTT event (volané z MQTT callback)"""
        self.transition_manager.register_mqtt_event(topic, message)