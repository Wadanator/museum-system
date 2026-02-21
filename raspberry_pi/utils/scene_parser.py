#!/usr/bin/env python3
"""
Scene parser for loading, executing, and managing museum room scenes.

Coordinates the state machine, transition manager, and state executor
to drive scene playback, audio/video preloading, and event handling.
"""

from utils.logging_setup import get_logger
from utils.state_machine import StateMachine
from utils.transition_manager import TransitionManager
from utils.state_executor import StateExecutor


class SceneParser:
    """
    Orchestrates scene lifecycle from load through playback to teardown.

    Integrates the state machine, transition manager, and state executor,
    and manages audio/video end callbacks, dynamic SFX preloading, and
    MQTT event forwarding.
    """

    def __init__(self, mqtt_client=None, audio_handler=None,
                 video_handler=None, logger=None):
        """
        Initialize the scene parser and wire up all sub-components.

        Args:
            mqtt_client: MQTT client instance for publishing commands.
            audio_handler: Audio handler for playback and preloading.
            video_handler: Video handler for playback control.
            logger: Logger instance for scene events.
        """
        self.logger = logger or get_logger("SceneParser")

        self.audio_handler = audio_handler
        self.video_handler = video_handler

        self.state_machine = StateMachine(logger=self.logger)
        self.transition_manager = TransitionManager(logger=self.logger)

        if self.audio_handler:
            self.audio_handler.set_end_callback(self._on_audio_ended)

        if self.video_handler:
            self.video_handler.set_end_callback(self._on_video_ended)

        self.state_executor = StateExecutor(
            mqtt_client=mqtt_client,
            audio_handler=audio_handler,
            video_handler=video_handler,
            logger=self.logger
        )

        self.scene_data = None

    def _collect_audio_files(self, data, audio_files):
        """
        Recursively scan scene JSON data and collect all referenced audio filenames.

        Searches for nodes matching {"action": "audio", "message": "<filename>"}
        and extracts the filename, stripping PLAY: prefixes and volume suffixes.

        Args:
            data: Scene data structure (dict or list) to traverse.
            audio_files: Set to populate with discovered audio filenames.
        """
        if isinstance(data, dict):
            # If this node is an audio action, extract the filename
            if data.get("action") == "audio" and "message" in data:
                message = data["message"]
                # Strip PLAY: prefix and optional volume suffix
                if message.startswith("PLAY:"):
                    parts = message.split(":")
                    if len(parts) >= 2:
                        audio_files.add(parts[1])  # filename
                elif ":" in message:  # Handle 'file:volume' format
                    parts = message.split(":")
                    audio_files.add(parts[0])
                else:
                    audio_files.add(message)

            # Recurse into all values in the dictionary
            for key, value in data.items():
                self._collect_audio_files(value, audio_files)

        elif isinstance(data, list):
            # Recurse into all items in the list
            for item in data:
                self._collect_audio_files(item, audio_files)

    def _on_audio_ended(self, filename):
        """
        Handle natural end-of-audio callback from the audio handler.

        Args:
            filename: Filename of the audio track that finished playing.
        """
        self.logger.debug(f"Audio finished callback received: {filename}")
        self.transition_manager.register_audio_end(filename)

    def _on_video_ended(self, filename):
        """
        Handle natural end-of-video callback from the video handler.

        Args:
            filename: Filename of the video that finished playing.
        """
        self.logger.debug(f"Video finished callback received: {filename}")
        self.transition_manager.register_video_end(filename)

    def load_scene(self, scene_file):
        """
        Load a scene file into the state machine.

        Args:
            scene_file: Path to the JSON scene file to load.

        Returns:
            bool: True if the scene was loaded successfully, False otherwise.
        """
        if self.state_machine.load_scene(scene_file):
            self.scene_data = True
            return True
        return False

    def start_scene(self):
        """
        Start the currently loaded scene.

        Scans the scene structure for audio files and preloads SFX files
        into RAM before starting the state machine. Executes the onEnter
        actions of the initial state.

        Returns:
            bool: True if the scene started successfully, False otherwise.
        """
        if not self.scene_data:
            self.logger.error("No scene data loaded")
            return False

        # --- Dynamic Preloading Start ---
        # Scan scene data from state_machine and preload all SFX files into RAM
        if self.audio_handler and self.state_machine.scene_data:
            self.logger.info("Scanning scene for audio files...")
            required_audio = set()

            # 1. Collect all audio filenames referenced in the scene
            self._collect_audio_files(self.state_machine.scene_data, required_audio)

            if required_audio:
                self.logger.info(
                    f"Found {len(required_audio)} audio files required for this scene."
                )
                # 2. Send list to AudioHandler for RAM preloading (acts as a loading screen)
                self.audio_handler.preload_files_for_scene(list(required_audio))
            else:
                self.logger.info("No audio files found in scene structure.")
        # --- Dynamic Preloading End ---

        self.transition_manager.clear_events()
        self.state_executor.reset_timeline_tracking()

        if self.state_machine.start():
            current_data = self.state_machine.get_current_state_data()
            if current_data:
                self.state_executor.execute_onEnter(current_data)
            return True
        return False

    def process_scene(self):
        """
        Advance the scene by one processing tick.

        Checks for completed audio/video, evaluates global and state-level
        transitions, and executes any timeline actions due in the current state.
        Should be called repeatedly from the main loop.

        Returns:
            bool: True if the scene is still running, False if it has finished.
        """
        if self.audio_handler:
            self.audio_handler.check_if_ended()

        if self.video_handler:
            self.video_handler.check_if_ended()

        if self.state_machine.is_finished():
            return False

        current_state_data = self.state_machine.get_current_state_data()
        if not current_state_data:
            return False

        # Evaluate global transitions that can fire from any state
        global_events = self.state_machine.get_global_events()
        if global_events:
            global_context = {"transitions": global_events}
            scene_elapsed = self.state_machine.get_scene_elapsed_time()

            next_state_global = self.transition_manager.check_transitions(
                global_context,
                scene_elapsed
            )

            if next_state_global and next_state_global != self.state_machine.current_state:
                self.logger.debug(
                    f"GLOBAL EVENT TRIGGERED -> Jumping to {next_state_global}"
                )
                self._change_state(next_state_global, current_state_data)
                return True

        # Execute any timeline actions due in the current state
        state_elapsed = self.state_machine.get_state_elapsed_time()
        self.state_executor.check_and_execute_timeline(current_state_data, state_elapsed)

        # Evaluate state-level transitions
        next_state = self.transition_manager.check_transitions(
            current_state_data, state_elapsed
        )
        if next_state:
            self._change_state(next_state, current_state_data)

        return True

    def stop_scene(self):
        """
        Stop the currently running scene and reset all internal state.

        Stops all audio, resets the state machine to END, clears pending
        transition events, and resets the timeline tracker.
        """
        self.logger.warning("Stopping scene via SceneParser request...")

        if self.audio_handler:
            self.audio_handler.stop_all()

        if self.state_machine:
            self.state_machine.reset_runtime_state()
            self.state_machine.current_state = "END"
        if self.transition_manager:
            self.transition_manager.clear_events()
        if self.state_executor:
            self.state_executor.reset_timeline_tracking()
        self.logger.info("SceneParser internal state reset.")

    def register_mqtt_event(self, topic, payload):
        """
        Forward an incoming MQTT event to the transition manager.

        Args:
            topic: The MQTT topic the event was received on.
            payload: The message payload string.
        """
        if self.transition_manager:
            self.transition_manager.register_mqtt_event(topic, payload)

    def _change_state(self, next_state, current_state_data):
        """
        Transition from the current state to a new state.

        Executes the onExit actions for the current state, advances the
        state machine, clears pending events, resets the timeline tracker,
        and executes the onEnter actions for the new state.

        Args:
            next_state: Name of the state to transition to.
            current_state_data: State data dict for the state being exited.
        """
        self.state_executor.execute_onExit(current_state_data)
        self.state_machine.goto_state(next_state)
        self.transition_manager.clear_events()
        self.state_executor.reset_timeline_tracking()

        new_state_data = self.state_machine.get_current_state_data()
        if new_state_data:
            self.state_executor.execute_onEnter(new_state_data)

    def cleanup(self):
        """Release any resources held by the scene parser."""
        pass