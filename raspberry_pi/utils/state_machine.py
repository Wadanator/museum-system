#!/usr/bin/env python3
"""
State Machine - Stavový automat pre scény
"""
import json
import time
from utils.logging_setup import get_logger
from utils.schema_validator import validate_scene_json

class StateMachine:
    def __init__(self, logger=None):
        self.logger = logger or get_logger("StateMachine")
        
        self.scene_id = None
        self.states = {}
        self.global_events = []
        self.current_state = None
        self.initial_state = None

        self.state_start_time = None
        self.scene_start_time = None
        self.state_history = []
        self.total_states = 0
        
        self.progress_emitter = None

    def set_progress_emitter(self, emitter_func):
        self.progress_emitter = emitter_func

    def load_scene(self, scene_file):
        try:
            with open(scene_file, 'r') as f:
                data = json.load(f)
        except Exception as exc:
            self.logger.error(f"Failed to load scene file: {exc}")
            return False

        # 1. Validácia štruktúry
        if not validate_scene_json(data, self.logger):
            return False

        # 2. Logická validácia (existencia stavov)
        states = data["states"]
        initial_state = data["initialState"]

        if initial_state not in states:
            self.logger.error(f"Initial state '{initial_state}' is not defined")
            return False

        for state_name, state_data in states.items():
            for idx, transition in enumerate(state_data.get("transitions", [])):
                goto = transition["goto"]
                if goto != "END" and goto not in states:
                    self.logger.error(f"State '{state_name}': Transition #{idx} targets unknown state '{goto}'")
                    return False
        
        # Validácia globalEvents cieľov
        global_events = data.get("globalEvents", [])
        for idx, event in enumerate(global_events):
            goto = event["goto"]
            if goto != "END" and goto not in states:
                self.logger.error(f"GlobalEvent #{idx} targets unknown state '{goto}'")
                return False

        # 3. Načítanie
        self.scene_id = data.get("sceneId", "unknown")
        self.states = states
        self.global_events = global_events
        self.initial_state = initial_state
        self.reset_runtime_state()
        self.total_states = len(self.states)

        self.logger.info(f"State machine loaded: {self.scene_id} ({self.total_states} states)")
        return True

    def start(self):
        if not self.states:
            return False
        
        self.scene_start_time = time.time()
        if not self.goto_state(self.initial_state):
            return False

        self.logger.info(f"State machine started -> {self.current_state}")
        return True
    
    def goto_state(self, state_name):
        if state_name == "END":
            self.current_state = "END"
            self.state_start_time = None
            self._emit_progress()
            return True
        
        if state_name not in self.states:
            self.logger.error(f"State '{state_name}' not found")
            return False
        
        if self.current_state and self.current_state != state_name:
            self.state_history.append(self.current_state)
        
        self.current_state = state_name
        self.state_start_time = time.time()
        
        self.logger.debug(f"State changed -> {state_name}")
        self._emit_progress()
        return True
    
    def get_global_events(self):
        return self.global_events

    def get_current_state_data(self):
        if not self.current_state or self.current_state == "END": return None
        return self.states.get(self.current_state)
    
    def get_state_elapsed_time(self):
        return time.time() - self.state_start_time if self.state_start_time else 0.0
    
    def get_scene_elapsed_time(self):
        return time.time() - self.scene_start_time if self.scene_start_time else 0.0
    
    def is_finished(self):
        return self.current_state == "END"

    def reset_runtime_state(self):
        self.current_state = None
        self.state_start_time = None
        self.scene_start_time = None
        self.state_history = []
        self.progress_emitter = None 

    def _emit_progress(self):
        if self.progress_emitter:
            self.progress_emitter(self.get_progress_info())

    def get_progress_info(self):
        total_definable_states = len([k for k in self.states.keys() if k != "END"])
        return {
            "scene_running": not self.is_finished(),
            "mode": "state_machine",
            "scene_id": self.scene_id,
            "current_state": self.current_state,
            "state_description": self.states.get(self.current_state, {}).get("description", "") if self.current_state != "END" else "Finished",
            "states_completed": len(self.state_history),
            "total_states": total_definable_states,
            "state_elapsed": round(self.get_state_elapsed_time(), 1),
            "scene_elapsed": round(self.get_scene_elapsed_time(), 1),
            "progress": min(1.0, len(self.state_history) / max(total_definable_states, 1)),
        }