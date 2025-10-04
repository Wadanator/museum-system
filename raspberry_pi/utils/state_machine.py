#!/usr/bin/env python3
"""
State Machine - Stavový automat pre scény
"""
import json
import time
from utils.logging_setup import get_logger

class StateMachine:
    def __init__(self, logger=None):
        self.logger = logger or get_logger("StateMachine")
        
        # Scene data
        self.scene_id = None
        self.states = {}
        self.current_state = None
        self.initial_state = None
        
        # Timing
        self.state_start_time = None
        self.scene_start_time = None
        
        # History
        self.state_history = []
        self.total_states = 0
        
    def load_scene(self, scene_file):
        """Načíta state machine scénu z JSON súboru"""
        try:
            with open(scene_file, 'r') as f:
                data = json.load(f)
            
            # Validácia
            if not isinstance(data, dict):
                self.logger.error("Scene must be a dict (state machine format)")
                return False
            
            if "states" not in data:
                self.logger.error("Scene missing 'states' key")
                return False
            
            if "initialState" not in data:
                self.logger.error("Scene missing 'initialState' key")
                return False
            
            # Ulož dáta
            self.scene_id = data.get("sceneId", "unknown")
            self.states = data["states"]
            self.initial_state = data["initialState"]
            self.current_state = None
            self.state_history = []
            self.total_states = len(self.states)
            
            self.logger.info(f"State machine loaded: {self.scene_id} ({self.total_states} states)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load state machine: {e}")
            return False
    
    def start(self):
        """Spustí state machine - prejde do initial state"""
        if not self.states:
            self.logger.error("No states loaded")
            return False
        
        if self.initial_state not in self.states:
            self.logger.error(f"Initial state '{self.initial_state}' not found")
            return False
        
        self.scene_start_time = time.time()
        self.goto_state(self.initial_state)
        self.logger.info(f"State machine started -> {self.current_state}")
        return True
    
    def goto_state(self, state_name):
        """Prejde do nového stavu"""
        if state_name == "END":
            self.current_state = "END"
            self.state_start_time = None
            return True
        
        if state_name not in self.states:
            self.logger.error(f"State '{state_name}' not found")
            return False
        
        # History
        if self.current_state:
            self.state_history.append(self.current_state)
        
        # Change state
        self.current_state = state_name
        self.state_start_time = time.time()
        
        desc = self.states[state_name].get("description", "")
        self.logger.info(f"State changed -> {state_name} ({desc})")
        return True
    
    def get_current_state_data(self):
        """Vráti data aktuálneho stavu"""
        if not self.current_state or self.current_state == "END":
            return None
        return self.states.get(self.current_state)
    
    def get_state_elapsed_time(self):
        """Vráti čas od vstupu do aktuálneho stavu (v sekundách)"""
        if not self.state_start_time:
            return 0.0
        return time.time() - self.state_start_time
    
    def get_scene_elapsed_time(self):
        """Vráti čas od začiatku scény (v sekundách)"""
        if not self.scene_start_time:
            return 0.0
        return time.time() - self.scene_start_time
    
    def is_finished(self):
        """Skontroluje či je scéna ukončená"""
        return self.current_state == "END"
    
    def get_progress_info(self):
        """Vráti info o progrese pre web dashboard"""
        return {
            "mode": "state_machine",
            "scene_id": self.scene_id,
            "current_state": self.current_state,
            "state_description": self.states.get(self.current_state, {}).get("description", "") if self.current_state != "END" else "Finished",
            "states_completed": len(self.state_history),
            "total_states": self.total_states,
            "state_elapsed": round(self.get_state_elapsed_time(), 1),
            "scene_elapsed": round(self.get_scene_elapsed_time(), 1)
        }