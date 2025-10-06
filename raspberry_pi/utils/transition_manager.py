#!/usr/bin/env python3
"""
Transition Manager - Spravuje prechody medzi stavmi
"""
from utils.logging_setup import get_logger


MAX_EVENT_QUEUE = 50

class TransitionManager:
    def __init__(self, logger=None):
        self.logger = logger or get_logger("TransitionManager")
        
        # Event tracking
        self.mqtt_events = []
        self.audio_end_events = []
        self.video_end_events = []
        
    def check_transitions(self, state_data, state_elapsed_time):
        """
        Skontroluje všetky transitions a vráti názov nového stavu alebo None
        """
        transitions = state_data.get("transitions", [])
        if not transitions:
            return None
        
        for transition in transitions:
            trans_type = transition.get("type")

            if trans_type == "timeout":
                next_state = self._check_timeout(transition, state_elapsed_time)
                if next_state:
                    return next_state
            
            elif trans_type == "audioEnd":
                next_state = self._check_audio_end(transition)
                if next_state:
                    return next_state
            
            elif trans_type == "videoEnd":
                next_state = self._check_video_end(transition)
                if next_state:
                    return next_state
            
            elif trans_type == "mqttMessage":
                next_state = self._check_mqtt_message(transition)
                if next_state:
                    return next_state
            
            elif trans_type == "always":
                # Okamžitý prechod
                goto = transition.get("goto")
                if goto is None:
                    self.logger.error(f"Always transition missing goto: {transition}")
                    return None
                return goto

            else:
                self.logger.warning(f"Unknown transition type: {trans_type}")

        return None
    
    def _check_timeout(self, transition, state_elapsed_time):
        """Timeout transition - čaká X sekúnd"""
        delay = transition.get("delay", 0)
        
        if state_elapsed_time >= delay:
            goto = transition.get("goto")
            self.logger.info(f"Timeout triggered ({delay}s) -> {goto}")
            return goto
        
        return None
    
    def _check_audio_end(self, transition):
        """AudioEnd transition - čaká kým audio skončí"""
        target = transition.get("target")
        
        # Skontroluj či máme event o skončení tohto audia
        for index, event in enumerate(list(self.audio_end_events)):
            if event == target:
                goto = transition.get("goto")
                if goto is None:
                    self.logger.error(f"AudioEnd transition missing goto: {transition}")
                    return None
                self.logger.info(f"AudioEnd triggered ({target}) -> {goto}")
                del self.audio_end_events[index]
                return goto
        
        return None
    
    def _check_video_end(self, transition):
        """VideoEnd transition - čaká kým video skončí"""
        target = transition.get("target")
        
        # Skontroluj či máme event o skončení tohto videa
        for index, event in enumerate(list(self.video_end_events)):
            if event == target:
                goto = transition.get("goto")
                if goto is None:
                    self.logger.error(f"VideoEnd transition missing goto: {transition}")
                    return None
                self.logger.info(f"VideoEnd triggered ({target}) -> {goto}")
                del self.video_end_events[index]
                return goto
        
        return None
    
    def _check_mqtt_message(self, transition):
        """MqttMessage transition - čaká na MQTT správu"""
        topic = transition.get("topic")
        message = transition.get("message")
        
        # Skontroluj či máme event s touto topic/message kombináciou
        for index, event in enumerate(list(self.mqtt_events)):
            if event.get("topic") == topic and event.get("message") == message:
                goto = transition.get("goto")
                if goto is None:
                    self.logger.error(f"MQTT transition missing goto: {transition}")
                    return None
                self.logger.info(f"MQTT triggered ({topic}={message}) -> {goto}")
                del self.mqtt_events[index]
                return goto
        
        return None
    
    # Event registration methods (volané zvonku)
    
    def register_mqtt_event(self, topic, message):
        """Zaregistruje MQTT event (volané z MQTT callback)"""
        if topic is None or message is None:
            self.logger.error("MQTT event missing topic or message")
            return

        self.mqtt_events.append({"topic": topic, "message": message})
        self._trim_events(self.mqtt_events)
        self.logger.debug(f"MQTT event registered: {topic}={message}")
    
    def register_audio_end(self, audio_file):
        """Zaregistruje skončenie audia (volané z audio handler)"""
        self.audio_end_events.append(audio_file)
        self._trim_events(self.audio_end_events)
        self.logger.debug(f"AudioEnd event registered: {audio_file}")
    
    def register_video_end(self, video_file):
        """Zaregistruje skončenie videa (volané z video handler)"""
        self.video_end_events.append(video_file)
        self._trim_events(self.video_end_events)
        self.logger.debug(f"VideoEnd event registered: {video_file}")
    
    def clear_events(self):
        """Vyčistí všetky eventy (pri zmene stavu)"""
        cleared_counts = (
            len(self.mqtt_events),
            len(self.audio_end_events),
            len(self.video_end_events)
        )
        self.mqtt_events.clear()
        self.audio_end_events.clear()
        self.video_end_events.clear()
        self.logger.debug(
            f"All events cleared (mqtt={cleared_counts[0]}, audio={cleared_counts[1]}, video={cleared_counts[2]})"
        )

    def _trim_events(self, queue):
        while len(queue) > MAX_EVENT_QUEUE:
            queue.pop(0)
