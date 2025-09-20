#!/usr/bin/env python3
from utils.logging_setup import get_logger

class MQTTMessageHandler:
    def __init__(self, logger=None):
        self.logger = logger or get_logger('mqtt_handler')
        
        # External handlers (will be injected)
        self.feedback_tracker = None
        self.device_registry = None
        self.button_callback = None
    
    def set_handlers(self, feedback_tracker=None, device_registry=None, button_callback=None):
        """Set external handlers for specialized processing."""
        self.feedback_tracker = feedback_tracker
        self.device_registry = device_registry
        self.button_callback = button_callback
    
    def handle_message(self, msg):
        """Process incoming MQTT messages and delegate to appropriate handlers."""
        try:
            topic_parts = msg.topic.split('/')
            payload = msg.payload.decode().strip()
            
            # Handle device status messages
            if self._is_device_status_message(topic_parts):
                if self.device_registry:
                    self.device_registry.update_device_status(topic_parts[1], payload)
                return
            
            # Handle feedback messages
            if self._is_feedback_message(msg.topic):
                if self.feedback_tracker:
                    self.feedback_tracker.handle_feedback_message(msg.topic, payload)
                return
            
            # Handle button/scene commands from ESP32
            if self._is_button_command(msg.topic, payload):
                if self.button_callback:
                    self.logger.info(f"Remote button press received: {msg.topic} = {payload}")
                    self.button_callback()
                else:
                    self.logger.warning(f"Button command received but no callback set: {msg.topic}")
                return
            
            # Log other messages for debugging
            self.logger.debug(f"Unhandled message on {msg.topic}: {payload}")
            
        except Exception as e:
            self.logger.error(f"Error processing message on {msg.topic}: {e}")
    
    def _is_device_status_message(self, topic_parts):
        """Check if message is a device status update."""
        return (len(topic_parts) == 3 and 
                topic_parts[0] == 'devices' and 
                topic_parts[2] == 'status')
    
    def _is_feedback_message(self, topic):
        """Check if message is a feedback/status message."""
        return topic.endswith('/status')
    
    def _is_button_command(self, topic, payload):
        """Check if message is a button/scene command from ESP32."""
        return topic.endswith('/scene') and payload.upper() == 'START'