#!/usr/bin/env python3
"""
MQTT Message Handler - Routes incoming messages to appropriate handlers.

Receives all incoming MQTT messages and routes them to the correct handlers:
- Device status messages → device registry
- Feedback messages → feedback tracker
- Button commands → scene execution
- MQTT transitions → scene parser (for interactive scenes)
"""

from utils.logging_setup import get_logger

class MQTTMessageHandler:
    """
    Centralized message handler that routes MQTT messages to appropriate handlers.
    
    Routes incoming messages based on topic patterns and delegates processing to
    specialized handlers for device management, feedback tracking, and commands.
    """
    
    def __init__(self, logger=None):
        """
        Initialize message handler.
        
        Args:
            logger: Logger instance for message routing events
        """
        self.logger = logger or get_logger('mqtt_handler')
        
        # === Handler References ===
        self.device_registry = None
        self.feedback_tracker = None
        self.button_callback = None
        self.scene_parser = None  # NEW: For MQTT transitions
    
    # ==========================================================================
    # HANDLER CONFIGURATION
    # ==========================================================================
    
    def set_handlers(self, device_registry=None, feedback_tracker=None, button_callback=None, scene_parser=None):
        """
        Set the handlers for different message types.
        
        Args:
            device_registry: Handler for ESP32 device status updates
            feedback_tracker: Handler for scene command feedback  
            button_callback: Callback for button/scene commands
            scene_parser: Scene parser for MQTT transition events
        """
        self.device_registry = device_registry
        self.feedback_tracker = feedback_tracker
        self.button_callback = button_callback
        self.scene_parser = scene_parser
        self.logger.debug("Message handlers configured")
    
    # ==========================================================================
    # MESSAGE PROCESSING
    # ==========================================================================
    
    def handle_message(self, msg):
        """Process a received MQTT message and route it to the correct handler."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            topic_parts = topic.split('/')
            
            # 1. Handle device status updates (devices/esp32_xx/status)
            if self.device_registry and self._is_device_status_message(topic_parts):
                device_id = topic_parts[1]
                self.device_registry.update_device_status(device_id, payload, is_retained=msg.retain)
                return

            # 2. Handle per-command feedback messages (prefix/motor1/feedback)
            if self.feedback_tracker and self._is_command_feedback_message(topic):
                self.feedback_tracker.handle_feedback_message(topic, payload)
                return
            
            # 3. Handle button commands (prefix/scene = START)
            if self.button_callback and self._is_button_command(topic, payload):
                self.logger.info("Button command received. Starting scene.")
                self.button_callback()
                return
            
            # 4. NEW: Route all other MQTT messages to scene parser for transitions
            # This allows mqttMessage transitions to work (e.g. waiting for button press)
            if self.scene_parser:
                self.scene_parser.register_mqtt_event(topic, payload)
                self.logger.debug(f"MQTT event routed to scene parser: {topic} = {payload}")
                return
            
            # 5. Log any messages that don't match known patterns
            self.logger.debug(f"Received unhandled message on topic {msg.topic}: {payload}")
            
        except Exception as e:
            self.logger.error(f"Error processing message on {msg.topic}: {e}")

    # ==========================================================================
    # MESSAGE TYPE DETECTION
    # ==========================================================================

    def _is_command_feedback_message(self, topic):
        """Check if message is a command feedback message (prefix/motor1/feedback)."""
        return topic.endswith('/feedback')

    def _is_device_status_message(self, topic_parts):
        """Check if message is a device status update (devices/esp32_xx/status)."""
        return (len(topic_parts) == 3 and 
                topic_parts[0] == 'devices' and 
                topic_parts[2] == 'status')

    def _is_button_command(self, topic, payload):
        """Check if message is a button/scene command from ESP32."""
        return topic.endswith('/scene') and payload.upper() == 'START'