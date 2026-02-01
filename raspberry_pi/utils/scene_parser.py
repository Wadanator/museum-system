#!/usr/bin/env python3
from utils.logging_setup import get_logger
from utils.state_machine import StateMachine
from utils.transition_manager import TransitionManager
from utils.state_executor import StateExecutor

class SceneParser:
    def __init__(self, mqtt_client=None, audio_handler=None, video_handler=None, logger=None):
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
        Rekurzívne prejde JSON scény a nájde všetky audio súbory.
        Hľadá kľúče: {"action": "audio", "message": "filename.mp3"}
        """
        if isinstance(data, dict):
            # Ak je tento uzol audio akcia
            if data.get("action") == "audio" and "message" in data:
                message = data["message"]
                # Extrahujeme názov súboru (odstránime PLAY: alebo :hlasitosť)
                if message.startswith("PLAY:"):
                    parts = message.split(":")
                    if len(parts) >= 2:
                        audio_files.add(parts[1]) # filename
                elif ":" in message: # Handle 'file:vol'
                     parts = message.split(":")
                     audio_files.add(parts[0])
                else:
                    audio_files.add(message)
            
            # Rekurzia do hĺbky pre všetky hodnoty v dictionary
            for key, value in data.items():
                self._collect_audio_files(value, audio_files)
                
        elif isinstance(data, list):
            # Rekurzia pre položky v zozname
            for item in data:
                self._collect_audio_files(item, audio_files)

    def _on_audio_ended(self, filename):
        self.logger.debug(f"Audio finished callback received: {filename}")
        self.transition_manager.register_audio_end(filename)

    def _on_video_ended(self, filename):
        self.logger.debug(f"Video finished callback received: {filename}")
        self.transition_manager.register_video_end(filename)

    def load_scene(self, scene_file):
        if self.state_machine.load_scene(scene_file):
            self.scene_data = True
            return True
        return False

    def start_scene(self):
        if not self.scene_data:
            self.logger.error("No scene data loaded")
            return False

        # --- DYNAMIC PRELOADING START ---
        # Tu využívame self.state_machine.scene_data, ktoré sme opravili v state_machine.py
        if self.audio_handler and self.state_machine.scene_data:
            self.logger.info("Scanning scene for audio files...")
            required_audio = set()
            
            # 1. Získame zoznam všetkých zvukov v scéne
            self._collect_audio_files(self.state_machine.scene_data, required_audio)
            
            if required_audio:
                self.logger.info(f"Found {len(required_audio)} audio files required for this scene.")
                # 2. Pošleme ich do AudioHandlera na načítanie do RAM
                # (Toto chvíľu potrvá - 'loading screen')
                self.audio_handler.preload_files_for_scene(list(required_audio))
            else:
                self.logger.info("No audio files found in scene structure.")
        # --- DYNAMIC PRELOADING END ---
            
        self.transition_manager.clear_events()
        self.state_executor.reset_timeline_tracking()
        
        if self.state_machine.start():
            current_data = self.state_machine.get_current_state_data()
            if current_data:
                self.state_executor.execute_onEnter(current_data)
            return True
        return False

    def process_scene(self):
        if self.audio_handler:
            self.audio_handler.check_if_ended()
            
        if self.video_handler:
            self.video_handler.check_if_ended()

        if self.state_machine.is_finished():
            return False

        current_state_data = self.state_machine.get_current_state_data()
        if not current_state_data:
            return False

        # Global events
        global_events = self.state_machine.get_global_events()
        if global_events:
            global_context = {"transitions": global_events}
            scene_elapsed = self.state_machine.get_scene_elapsed_time()
            
            next_state_global = self.transition_manager.check_transitions(
                global_context, 
                scene_elapsed
            )
            
            if next_state_global and next_state_global != self.state_machine.current_state:
                self.logger.debug(f"GLOBAL EVENT TRIGGERED -> Jumping to {next_state_global}")
                self._change_state(next_state_global, current_state_data)
                return True

        # Timeline logic
        state_elapsed = self.state_machine.get_state_elapsed_time()
        self.state_executor.check_and_execute_timeline(current_state_data, state_elapsed)

        # Transition logic
        next_state = self.transition_manager.check_transitions(current_state_data, state_elapsed)
        if next_state:
            self._change_state(next_state, current_state_data)
            
        return True
    
    def stop_scene(self):
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
        if self.transition_manager:
            self.transition_manager.register_mqtt_event(topic, payload)

    def _change_state(self, next_state, current_state_data):
        self.state_executor.execute_onExit(current_state_data)
        self.state_machine.goto_state(next_state)
        self.transition_manager.clear_events()
        self.state_executor.reset_timeline_tracking()
        
        new_state_data = self.state_machine.get_current_state_data()
        if new_state_data:
            self.state_executor.execute_onEnter(new_state_data)

    def cleanup(self):
        pass