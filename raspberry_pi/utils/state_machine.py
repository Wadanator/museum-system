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
        
        self.progress_emitter = None

    def set_progress_emitter(self, emitter_func):
        """Nastaví funkciu, ktorá bude volaná pri zmene stavu na notifikáciu dashboardu."""
        self.progress_emitter = emitter_func
        # ------------------------------------------------------------------
        
    def load_scene(self, scene_file):
        """Načíta state machine scénu z JSON súboru"""
        try:
            with open(scene_file, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Scene file not found: {scene_file}")
            return False
        except json.JSONDecodeError as exc:
            self.logger.error(f"Invalid JSON in scene file: {exc}")
            return False
        except Exception as exc:
            self.logger.error(f"Failed to load state machine: {exc}")
            return False

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

        states = data["states"]
        if not isinstance(states, dict) or not states:
            self.logger.error("Scene 'states' must be a non-empty dict")
            return False

        initial_state = data["initialState"]
        if initial_state not in states:
            self.logger.error(f"Initial state '{initial_state}' not found in states")
            return False

        if not self._validate_states(states):
            return False

        # Ulož dáta
        self.scene_id = data.get("sceneId", "unknown")
        self.states = states
        self.initial_state = initial_state
        self.reset_runtime_state()
        self.total_states = len(self.states)

        self.logger.info(f"State machine loaded: {self.scene_id} ({self.total_states} states)")
        return True

    def start(self):
        """Spustí state machine - prejde do initial state"""
        if not self.states:
            self.logger.error("No states loaded")
            return False

        if self.initial_state not in self.states:
            self.logger.error(f"Initial state '{self.initial_state}' not found")
            return False

        self.scene_start_time = time.time()
        if not self.goto_state(self.initial_state):
            self.logger.error("Failed to enter initial state")
            return False

        self.logger.info(f"State machine started -> {self.current_state}")
        return True
    
    def goto_state(self, state_name):
        """Prejde do nového stavu"""
        if state_name == "END":
            self.current_state = "END"
            self.state_start_time = None
            
            if self.progress_emitter:
                self.progress_emitter(self.get_progress_info())
            
            return True
        
        if state_name not in self.states:
            self.logger.error(f"State '{state_name}' not found")
            return False
        
        # History
        if self.current_state and self.current_state != state_name:
            self.state_history.append(self.current_state)
        
        # Change state
        self.current_state = state_name
        self.state_start_time = time.time()
        
        desc = self.states[state_name].get("description", "")
        self.logger.info(f"State changed -> {state_name} ({desc})")

        if self.progress_emitter:
            self.progress_emitter(self.get_progress_info())
        
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
        """Vráti info o progrese pre web dashboard. Pridáme scene_running=True."""
        
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

    def reset_runtime_state(self):
        """Resetuje runtime informácie - používa sa pri load/start"""
        self.current_state = None
        self.state_start_time = None
        self.scene_start_time = None
        self.state_history = []
        self.progress_emitter = None 

    def _validate_states(self, states):
        """Overí štruktúru stavov a prechodov"""
        for state_name, state_data in states.items():
            if not isinstance(state_data, dict):
                self.logger.error(f"State '{state_name}' must be a dict")
                return False

            transitions = state_data.get("transitions", [])
            if transitions and not isinstance(transitions, list):
                self.logger.error(f"Transitions for state '{state_name}' must be a list")
                return False

            for idx, transition in enumerate(transitions):
                if not isinstance(transition, dict):
                    self.logger.error(f"Transition #{idx} in state '{state_name}' must be a dict")
                    return False

                goto = transition.get("goto")
                if goto is None:
                    self.logger.error(f"Transition #{idx} in state '{state_name}' missing 'goto'")
                    return False

                if goto != "END" and goto not in states:
                    self.logger.error(f"Transition #{idx} in state '{state_name}' references unknown state '{goto}'")
                    return False

            timeline = state_data.get("timeline", [])
            if timeline and not isinstance(timeline, list):
                self.logger.error(f"Timeline for state '{state_name}' must be a list")
                return False

            for idx, item in enumerate(timeline):
                if not isinstance(item, dict):
                    self.logger.error(f"Timeline item #{idx} in state '{state_name}' must be a dict")
                    return False

                if "actions" in item and not isinstance(item["actions"], list):
                    self.logger.error(f"Timeline item #{idx} in state '{state_name}' has invalid 'actions' field")
                    return False

        return True