#!/usr/bin/env python3
"""
Scene Parser - State Machine Version
Complete replacement of timestamp system
"""
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
        
        # Connect audio/video end callbacks
        if self.audio_handler:
            self.audio_handler.set_end_callback(self._on_audio_end)
        
        if self.video_handler:
            self.video_handler.set_end_callback(self._on_video_end)
        
        # Scene data reference (for compatibility)
        self.scene_data = None

        self._reset_runtime_state()

    def load_scene(self, scene_file):
        """Load state machine scene"""
        success = self.state_machine.load_scene(scene_file)

        if success:
            self.scene_data = self.state_machine.states
            self._reset_runtime_state()

        return success

    def start_scene(self):
        """Start scene execution"""
        if not self.state_machine.states:
            self.logger.error("No scene loaded")
            return False

        self._reset_runtime_state()
        self.logger.debug("Runtime state cleared before scene start")

        # Enable MQTT feedback tracking
        if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
            if self.mqtt_client.feedback_tracker:
                try:
                    self.mqtt_client.feedback_tracker.enable_feedback_tracking()
                except Exception as exc:
                    self.logger.error(f"Failed to enable MQTT feedback tracking: {exc}")

        # Start state machine
        success = self.state_machine.start()

        if not success:
            if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
                tracker = self.mqtt_client.feedback_tracker
                if tracker:
                    try:
                        tracker.disable_feedback_tracking()
                    except Exception as exc:
                        self.logger.error(f"Failed to disable MQTT feedback tracking after start error: {exc}")
            return False

        # Execute onEnter of initial state
        state_data = self.state_machine.get_current_state_data()
        if state_data:
            self.state_executor.execute_onEnter(state_data)

        return True
        
    def process_scene(self):
        """
        Main processing method - called in loop from main.py
        Returns True if scene is still running, False if finished
        """
        try:
            if self.state_machine.is_finished():
                return False

            # Check if audio/video ended
            if self.audio_handler:
                self.audio_handler.check_if_ended()

            if self.video_handler:
                self.video_handler.check_if_ended()

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
                if not self.state_machine.goto_state(next_state):
                    self.logger.error(f"Failed to change state to '{next_state}'")
                    self.stop_scene(skip_on_exit=True)
                    return False

                # Clear tracking
                self.state_executor.reset_timeline_tracking()
                self.transition_manager.clear_events()

                # If not END, execute onEnter of new state
                if not self.state_machine.is_finished():
                    new_state_data = self.state_machine.get_current_state_data()
                    if new_state_data:
                        self.state_executor.execute_onEnter(new_state_data)

            return True

        except Exception as exc:
            self.logger.exception(f"Scene processing failed: {exc}")
            self.stop_scene()
            return False

    def stop_scene(self, mqtt_client=None, *, skip_on_exit=False):
        """Stop scene execution"""
        mqtt = mqtt_client or self.mqtt_client
        if mqtt and hasattr(mqtt, 'feedback_tracker'):
            if mqtt.feedback_tracker:
                try:
                    mqtt.feedback_tracker.disable_feedback_tracking()
                except Exception as exc:
                    self.logger.error(f"Failed to disable MQTT feedback tracking: {exc}")

        if not skip_on_exit:
            current_state = self.state_machine.get_current_state_data()
            if current_state:
                self.state_executor.execute_onExit(current_state)

        if self.audio_handler:
            try:
                self.audio_handler.stop_audio()
            except Exception as exc:
                self.logger.error(f"Failed to stop audio handler: {exc}")

        if self.video_handler:
            try:
                self.video_handler.stop_video()
            except Exception as exc:
                self.logger.error(f"Failed to stop video handler: {exc}")

        self.state_machine.goto_state("END")
        self._reset_runtime_state()

        self.logger.info("Scene stopped")
    
    def get_progress_info(self):
        """Return progress info for web dashboard"""
        return self.state_machine.get_progress_info()
    
    # ============================================================================
    # AUDIO/VIDEO END CALLBACKS
    # ============================================================================
    
    def _on_audio_end(self, audio_file):
        """Called when audio finishes playing"""
        self.transition_manager.register_audio_end(audio_file)
    
    def _on_video_end(self, video_file):
        """Called when video finishes playing"""
        self.transition_manager.register_video_end(video_file)
    
    # ============================================================================
    # MQTT EVENT REGISTRATION
    # ============================================================================
    
    def register_mqtt_event(self, topic, message):
        """Register MQTT event (called from MQTT callback)"""
        self.transition_manager.register_mqtt_event(topic, message)

    def _reset_runtime_state(self):
        """Clear runtime tracking helpers"""
        self.state_executor.reset_timeline_tracking()
        self.transition_manager.clear_events()
        self.state_machine.reset_runtime_state()
    

