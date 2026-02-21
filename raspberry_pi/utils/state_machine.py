#!/usr/bin/env python3
"""
State Machine - Finite state machine for scene execution.
"""

import json
import time
from utils.logging_setup import get_logger
from utils.schema_validator import validate_scene_json


class StateMachine:
    """
    Finite state machine that loads, validates, and drives scene execution.

    Manages the current state, elapsed timers, state history, and optional
    change notifications for dashboard integration.
    """

    def __init__(self, logger=None):
        """
        Initialize the state machine with empty scene data.

        Args:
            logger: Logger instance for state machine events.
        """
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

        # Full scene data retained for audio preloading in SceneParser
        self.scene_data = None

        # Optional callback for state change notifications (dashboard updates)
        self.on_state_change = None

    def load_scene(self, scene_file):
        """
        Load and validate a scene from a JSON file.

        Performs schema validation followed by logical validation of all
        state transition targets and global event targets. Stores the full
        scene data for use by SceneParser during audio preloading.

        Args:
            scene_file: Path to the JSON scene file to load.

        Returns:
            bool: True if the scene was loaded and validated successfully,
                False otherwise.
        """
        try:
            with open(scene_file, 'r') as f:
                data = json.load(f)
        except Exception as exc:
            self.logger.error(f"Failed to load scene file: {exc}")
            return False

        # 1. Schema structure validation
        if not validate_scene_json(data, self.logger):
            return False

        # 2. Logical validation — verify all referenced states exist
        states = data["states"]
        initial_state = data["initialState"]

        if initial_state not in states:
            self.logger.error(
                f"Initial state '{initial_state}' is not defined"
            )
            return False

        for state_name, state_data in states.items():
            for idx, transition in enumerate(
                    state_data.get("transitions", [])):
                goto = transition["goto"]
                if goto != "END" and goto not in states:
                    self.logger.error(
                        f"State '{state_name}': Transition #{idx} targets "
                        f"unknown state '{goto}'"
                    )
                    return False

        # Validate globalEvents transition targets
        global_events = data.get("globalEvents", [])
        for idx, event in enumerate(global_events):
            goto = event["goto"]
            if goto != "END" and goto not in states:
                self.logger.error(
                    f"GlobalEvent #{idx} targets unknown state '{goto}'"
                )
                return False

        # 3. Load validated data into state machine
        self.scene_id = data.get("sceneId", "unknown")
        self.states = states
        self.global_events = global_events
        self.initial_state = initial_state

        # Store full data for SceneParser audio preloading
        self.scene_data = data

        self.reset_runtime_state()
        self.total_states = len(self.states)

        self.logger.info(
            f"State machine loaded: {self.scene_id} ({self.total_states} states)"
        )
        return True

    def start(self):
        """
        Start the state machine from the initial state.

        Returns:
            bool: True if the machine started successfully, False if no
                states are loaded or the initial state transition fails.
        """
        if not self.states:
            return False

        self.scene_start_time = time.time()
        if not self.goto_state(self.initial_state):
            return False

        self.logger.info(f"State machine started -> {self.current_state}")
        return True

    def goto_state(self, state_name):
        """
        Transition the machine to the specified state.

        Records the previous state in history, updates the current state,
        resets the state timer, and invokes the on_state_change callback
        if one is registered. The special state name 'END' marks the
        scene as finished without requiring a matching states entry.

        Args:
            state_name: Name of the state to transition to, or 'END'.

        Returns:
            bool: True if the transition succeeded, False if the target
                state does not exist.
        """
        if state_name == "END":
            self.current_state = "END"
            self.state_start_time = None

            # Notify callback on scene end
            if self.on_state_change:
                self.on_state_change("END")

            return True

        if state_name not in self.states:
            self.logger.error(f"State '{state_name}' not found")
            return False

        if self.current_state and self.current_state != state_name:
            self.state_history.append(self.current_state)

        self.current_state = state_name
        self.state_start_time = time.time()

        self.logger.debug(f"State changed -> {state_name}")

        # Notify callback on state change
        if self.on_state_change:
            self.on_state_change(state_name)

        return True

    def get_global_events(self):
        """
        Return the list of global events defined in the scene.

        Returns:
            list: Global event transition definitions.
        """
        return self.global_events

    def get_current_state_data(self):
        """
        Return the data dictionary for the current state.

        Returns:
            dict or None: State definition dict, or None if no current state
                is set. Returns the END state dict if one is defined and the
                machine has reached END.
        """
        if not self.current_state:
            return None

        if self.current_state == "END":
            return self.states.get("END")

        return self.states.get(self.current_state)

    def get_state_elapsed_time(self):
        """
        Return seconds elapsed since the current state was entered.

        Returns:
            float: Elapsed time in seconds, or 0.0 if no state is active.
        """
        return time.time() - self.state_start_time if self.state_start_time else 0.0

    def get_scene_elapsed_time(self):
        """
        Return seconds elapsed since the scene was started.

        Returns:
            float: Elapsed time in seconds, or 0.0 if the scene has not started.
        """
        return time.time() - self.scene_start_time if self.scene_start_time else 0.0

    def is_finished(self):
        """
        Check whether the scene has reached the END state.

        Returns:
            bool: True if the current state is 'END', False otherwise.
        """
        return self.current_state == "END"

    def reset_runtime_state(self):
        """Reset all runtime tracking state without unloading the scene data."""
        self.current_state = None
        self.state_start_time = None
        self.scene_start_time = None
        self.state_history = []