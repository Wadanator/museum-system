# raspberry_pi/utils/transition_manager.py
#!/usr/bin/env python3
"""
Transition Manager - Spravuje prechody medzi stavmi (Thread-Safe & Optimized)
"""
from collections import deque
from threading import Lock
from utils.logging_setup import get_logger

class TransitionManager:
    def __init__(self, logger=None):
        self.logger = logger or get_logger("TransitionManager")
        self.lock = Lock()
        
        # Event tracking - použitie deque pre automatické mazanie starých eventov
        self.mqtt_events = deque(maxlen=50)
        self.audio_end_events = deque(maxlen=50)
        self.video_end_events = deque(maxlen=50)

        # Dispatch dictionary pre handlery prechodov
        # Kľúč: typ prechodu, Hodnota: funkcia
        self.transition_handlers = {
            "timeout": self._check_timeout,
            "audioEnd": self._check_audio_end,
            "videoEnd": self._check_video_end,
            "mqttMessage": self._check_mqtt_message,
            "always": self._check_always
        }
        
    def check_transitions(self, state_data, state_elapsed_time):
        """
        Skontroluje všetky transitions a vráti názov nového stavu alebo None
        """
        transitions = state_data.get("transitions", [])
        if not transitions:
            return None
        
        # Thread-safe prístup k eventom počas kontroly
        with self.lock:
            for transition in transitions:
                trans_type = transition.get("type")
                handler = self.transition_handlers.get(trans_type)

                if handler:
                    # Voláme handler so štandardizovanými argumentmi
                    next_state = handler(transition, state_elapsed_time)
                    if next_state:
                        return next_state
                else:
                    self.logger.warning(f"Unknown transition type: {trans_type}")

        return None
    
    # --- Internal Check Methods ---
    # Všetky prijímajú (transition, state_elapsed_time) pre jednotné volanie

    def _check_timeout(self, transition, state_elapsed_time):
        """Timeout transition - čaká X sekúnd"""
        delay = transition.get("delay", 0)

        if state_elapsed_time >= delay:
            return self._get_goto(transition, f"Timeout triggered ({delay}s)")
        return None
    
    def _check_audio_end(self, transition, _):
        """AudioEnd transition - čaká kým audio skončí"""
        target = transition.get("target")
        
        # Iterujeme kópiu alebo priamo deque (vďaka Locku je to bezpečné)
        for event in list(self.audio_end_events):
            if event == target:
                self.audio_end_events.remove(event) # Odstránime spracovaný event
                return self._get_goto(transition, f"AudioEnd triggered ({target})")
        return None
    
    def _check_video_end(self, transition, _):
        """VideoEnd transition - čaká kým video skončí"""
        target = transition.get("target")
        
        for event in list(self.video_end_events):
            if event == target:
                self.video_end_events.remove(event)
                return self._get_goto(transition, f"VideoEnd triggered ({target})")
        return None
    
    def _check_mqtt_message(self, transition, _):
        """MqttMessage transition - čaká na MQTT správu"""
        topic = transition.get("topic")
        message = transition.get("message")
        
        for event in list(self.mqtt_events):
            if event.get("topic") == topic and event.get("message") == message:
                self.mqtt_events.remove(event)
                return self._get_goto(transition, f"MQTT triggered ({topic}={message})")
        return None

    def _check_always(self, transition, _):
        """Always transition - okamžitý prechod"""
        return self._get_goto(transition, "Always transition")

    def _get_goto(self, transition, log_msg):
        """Helper na získanie 'goto' a logovanie"""
        goto = transition.get("goto")
        if goto is None:
            self.logger.error(f"Transition missing 'goto': {transition}")
            return None
        self.logger.info(f"{log_msg} -> {goto}")
        return goto
    
    # --- Event registration methods (Thread-Safe) ---
    
    def register_mqtt_event(self, topic, message):
        """Zaregistruje MQTT event (volané z MQTT callback)"""
        if topic is None or message is None:
            self.logger.error("MQTT event missing topic or message")
            return

        with self.lock:
            self.mqtt_events.append({"topic": topic, "message": message})
        
        self.logger.debug(f"MQTT event registered: {topic}={message}")
    
    def register_audio_end(self, audio_file):
        """Zaregistruje skončenie audia"""
        with self.lock:
            self.audio_end_events.append(audio_file)
        self.logger.debug(f"AudioEnd event registered: {audio_file}")
    
    def register_video_end(self, video_file):
        """Zaregistruje skončenie videa"""
        with self.lock:
            self.video_end_events.append(video_file)
        self.logger.debug(f"VideoEnd event registered: {video_file}")
    
    def clear_events(self):
        """Vyčistí všetky eventy (pri zmene stavu)"""
        with self.lock:
            cleared_counts = (len(self.mqtt_events), len(self.audio_end_events), len(self.video_end_events))
            self.mqtt_events.clear()
            self.audio_end_events.clear()
            self.video_end_events.clear()
            
        self.logger.debug(
            f"All events cleared (mqtt={cleared_counts[0]}, audio={cleared_counts[1]}, video={cleared_counts[2]})"
        )