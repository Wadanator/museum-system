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

    def reset_runtime_state(self):
        """Resetuje runtime informácie - používa sa pri load/start"""
        self.current_state = None
        self.state_start_time = None
        self.scene_start_time = None
        self.state_history = []

    def _validate_states(self, states):
        """Overí štruktúru stavov, akcií a prechodov"""
        allowed_transition_types = {"timeout", "audioEnd", "videoEnd", "mqttMessage", "always"}

        for state_name, state_data in states.items():
            if not isinstance(state_data, dict):
                self.logger.error(f"State '{state_name}' must be a dict")
                return False

            if not self._validate_actions(state_name, state_data):
                return False

            transitions = state_data.get("transitions", [])
            if transitions and not isinstance(transitions, list):
                self.logger.error(f"Transitions for state '{state_name}' must be a list")
                return False

            for idx, transition in enumerate(transitions):
                if not isinstance(transition, dict):
                    self.logger.error(f"Transition #{idx} in state '{state_name}' must be a dict")
                    return False

                trans_type = transition.get("type")
                if trans_type not in allowed_transition_types:
                    self.logger.error(
                        f"Transition #{idx} in state '{state_name}' has unsupported type '{trans_type}'"
                    )
                    return False

                goto = transition.get("goto")
                if goto is None:
                    self.logger.error(f"Transition #{idx} in state '{state_name}' missing 'goto'")
                    return False

                if goto != "END" and goto not in states:
                    self.logger.error(
                        f"Transition #{idx} in state '{state_name}' references unknown state '{goto}'"
                    )
                    return False

                if trans_type == "timeout":
                    delay = transition.get("delay")
                    if not isinstance(delay, (int, float)) or delay < 0:
                        self.logger.error(
                            f"Transition #{idx} in state '{state_name}' has invalid delay '{delay}'"
                        )
                        return False
                elif trans_type in {"audioEnd", "videoEnd"}:
                    if not transition.get("target"):
                        self.logger.error(
                            f"Transition #{idx} in state '{state_name}' missing target for '{trans_type}'"
                        )
                        return False
                elif trans_type == "mqttMessage":
                    if not transition.get("topic") or transition.get("message") is None:
                        self.logger.error(
                            f"Transition #{idx} in state '{state_name}' missing topic/message for MQTT"
                        )
                        return False

            timeline = state_data.get("timeline", [])
            if timeline and not isinstance(timeline, list):
                self.logger.error(f"Timeline for state '{state_name}' must be a list")
                return False

            for idx, item in enumerate(timeline):
                if not isinstance(item, dict):
                    self.logger.error(f"Timeline item #{idx} in state '{state_name}' must be a dict")
                    return False

                trigger = item.get("at")
                if trigger is None or not isinstance(trigger, (int, float)) or trigger < 0:
                    self.logger.error(
                        f"Timeline item #{idx} in state '{state_name}' has invalid 'at' value '{trigger}'"
                    )
                    return False

                if "action" in item:
                    if not self._validate_action_dict(item):
                        self.logger.error(
                            f"Timeline item #{idx} in state '{state_name}' has invalid action definition"
                        )
                        return False

                if "actions" in item:
                    actions = item["actions"]
                    if not isinstance(actions, list) or not all(self._validate_action_dict(a) for a in actions):
                        self.logger.error(
                            f"Timeline item #{idx} in state '{state_name}' has invalid 'actions' field"
                        )
                        return False

        return True

    def _validate_actions(self, state_name, state_data):
        """Overí onEnter/onExit akcie"""
        for key in ("onEnter", "onExit"):
            actions = state_data.get(key, [])
            if actions and not isinstance(actions, list):
                self.logger.error(f"{key} for state '{state_name}' must be a list")
                return False

            for idx, action in enumerate(actions):
                if not self._validate_action_dict(action):
                    self.logger.error(
                        f"Action #{idx} in '{key}' for state '{state_name}' has invalid format"
                    )
                    return False

        return True

    @staticmethod
    def _validate_action_dict(action):
        """Kontroluje základnú štruktúru akcie"""
        if not isinstance(action, dict):
            return False

        action_type = action.get("action")
        if not action_type:
            return False

        if action_type == "mqtt":
            return bool(action.get("topic")) and action.get("message") is not None

        if action_type in {"audio", "video"}:
            return bool(action.get("message"))

        return False
