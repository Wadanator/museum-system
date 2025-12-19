#!/usr/bin/env python3
from utils.logging_setup import get_logger
from utils.state_machine import StateMachine
from utils.transition_manager import TransitionManager
from utils.state_executor import StateExecutor

class SceneParser:
    def __init__(self, mqtt_client=None, audio_handler=None, video_handler=None, logger=None):
        self.logger = logger or get_logger("SceneParser")
        
        self.state_machine = StateMachine(logger=self.logger)
        self.transition_manager = TransitionManager(logger=self.logger)
        self.state_executor = StateExecutor(
            mqtt_client=mqtt_client, 
            audio_handler=audio_handler, 
            video_handler=video_handler,
            logger=self.logger
        )
        
        self.scene_data = None

    def load_scene(self, scene_file):
        if self.state_machine.load_scene(scene_file):
            self.scene_data = True
            return True
        return False

    def start_scene(self):
        if not self.scene_data:
            self.logger.error("No scene data loaded")
            return False
            
        self.transition_manager.clear_events()
        self.state_executor.reset_timeline_tracking()
        
        if self.state_machine.start():
            current_data = self.state_machine.get_current_state_data()
            if current_data:
                self.state_executor.execute_onEnter(current_data)
            return True
        return False

    def process_scene(self):
        if self.state_machine.is_finished():
            return False

        current_state_data = self.state_machine.get_current_state_data()
        if not current_state_data:
            return False

        global_events = self.state_machine.get_global_events()
        if global_events:
            global_context = {"transitions": global_events}
            scene_elapsed = self.state_machine.get_scene_elapsed_time()
            
            next_state_global = self.transition_manager.check_transitions(
                global_context, 
                scene_elapsed
            )
            
            if next_state_global:
                self.logger.info(f"GLOBAL EVENT TRIGGERED -> Jumping to {next_state_global}")
                self._change_state(next_state_global, current_state_data)
                return True

        state_elapsed = self.state_machine.get_state_elapsed_time()
        self.state_executor.check_and_execute_timeline(current_state_data, state_elapsed)

        next_state = self.transition_manager.check_transitions(current_state_data, state_elapsed)
        if next_state:
            self._change_state(next_state, current_state_data)
            
        return True
    
    def stop_scene(self):
        self.logger.info("Stopping scene via SceneParser request...")
        
        if self.state_machine:
            self.state_machine.reset_runtime_state()
            self.state_machine.current_state = "END"

        if self.transition_manager:
            self.transition_manager.clear_events()

        if self.state_executor:
            self.state_executor.reset_timeline_tracking()
            
        self.logger.info("SceneParser internal state reset.")

    def register_mqtt_event(self, topic, payload):
        """Zaregistruje prichádzajúci MQTT event pre TransitionManager"""
        if self.transition_manager:
            self.transition_manager.register_event(topic, payload)
            self.logger.debug(f"MQTT event registered: {topic} = {payload}")

    def _change_state(self, next_state, current_state_data):
        self.state_executor.execute_onExit(current_state_data)
        self.state_machine.goto_state(next_state)
        self.transition_manager.clear_events()
        self.state_executor.reset_timeline_tracking()
        
        new_state_data = self.state_machine.get_current_state_data()
        if new_state_data:
            self.state_executor.execute_onEnter(new_state_data)

    def get_progress_info(self):
        return self.state_machine.get_progress_info()
    
    def cleanup(self):
        pass