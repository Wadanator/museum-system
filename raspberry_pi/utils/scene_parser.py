#!/usr/bin/env python3
"""
Scene Parser - Riadi vykonávanie scény
"""
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
        """Načíta scénu cez State Machine"""
        if self.state_machine.load_scene(scene_file):
            self.scene_data = True
            return True
        return False

    def start_scene(self):
        """Spustí načítanú scénu"""
        if not self.scene_data:
            self.logger.error("No scene data loaded")
            return False
            
        self.transition_manager.clear_events()
        self.state_executor.reset_timeline_tracking()
        
        if self.state_machine.start():
            # Okamžite vykonaj onEnter pre prvý stav
            current_data = self.state_machine.get_current_state_data()
            if current_data:
                self.state_executor.execute_onEnter(current_data)
            return True
        return False

    def process_scene(self):
        """Hlavná slučka vykonávania scény"""
        if self.state_machine.is_finished():
            return False

        current_state_data = self.state_machine.get_current_state_data()
        if not current_state_data:
            return False

        # 1. KONTROLA GLOBÁLNYCH EVENTOV (Priorita)
        global_events = self.state_machine.get_global_events()
        if global_events:
            global_context = {"transitions": global_events}
            # Pre globálne eventy používame čas od začiatku scény
            scene_elapsed = self.state_machine.get_scene_elapsed_time()
            
            next_state_global = self.transition_manager.check_transitions(
                global_context, 
                scene_elapsed
            )
            
            if next_state_global:
                self.logger.info(f"GLOBAL EVENT TRIGGERED -> Jumping to {next_state_global}")
                self._change_state(next_state_global, current_state_data)
                return True

        # 2. Bežná kontrola Timeline
        state_elapsed = self.state_machine.get_state_elapsed_time()
        self.state_executor.check_and_execute_timeline(current_state_data, state_elapsed)

        # 3. Bežná kontrola Prechodov
        next_state = self.transition_manager.check_transitions(current_state_data, state_elapsed)
        if next_state:
            self._change_state(next_state, current_state_data)
            
        return True

    def _change_state(self, next_state, current_state_data):
        """Vykoná bezpečný prechod medzi stavmi"""
        # 1. onExit starého stavu
        self.state_executor.execute_onExit(current_state_data)
        
        # 2. Zmena stavu
        self.state_machine.goto_state(next_state)
        
        # 3. Vyčistenie eventov a timeline pre nový stav
        self.transition_manager.clear_events()
        self.state_executor.reset_timeline_tracking()
        
        # 4. onEnter nového stavu
        new_state_data = self.state_machine.get_current_state_data()
        if new_state_data:
            self.state_executor.execute_onEnter(new_state_data)

    def get_progress_info(self):
        return self.state_machine.get_progress_info()
    
    def cleanup(self):
        pass