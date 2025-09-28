#!/usr/bin/env python3
"""
MQTT Message Handler - Routes and processes incoming MQTT messages.

Handles message routing to appropriate processors including:
- Device status updates
- Feedback/acknowledgment messages  
- Button/scene command processing
"""

from utils.logging_setup import get_logger


class MQTTMessageHandler:
    """
    Message handler for routing incoming MQTT messages to appropriate processors.
    
    Processes different types of MQTT messages and delegates them to specialized
    handlers for device status, feedback tracking, and button commands.
    """
    
    def __init__(self, logger=None):
        """
        Initialize message handler.
        
        Args:
            logger: Logger instance for message handling
        """
        self.logger = logger or get_logger('mqtt_handler')
        
        # === External Handler References ===
        # These are injected after initialization
        self.feedback_tracker = None
        self.device_registry = None
        self.button_callback = None
    
    # ==========================================================================
    # HANDLER INJECTION
    # ==========================================================================
    
    def set_handlers(self, feedback_tracker=None, device_registry=None, button_callback=None):
        """
        Set external handlers for specialized message processing.
        
        Args:
            feedback_tracker: Handler for feedback/acknowledgment messages
            device_registry: Handler for device status updates
            button_callback: Callback function for button/scene commands
        """
        self.feedback_tracker = feedback_tracker
        self.device_registry = device_registry
        self.button_callback = button_callback
        self.logger.info("MQTT message handlers set.")
    
    # ==========================================================================
    # MESSAGE PROCESSING
    # ==========================================================================
    
    def handle_message(self, msg):
        """
        Process a received MQTT message and route it to the correct handler.
        
        Args:
            msg: The MQTT message object
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            topic_parts = topic.split('/')
            
            # Handle device status updates
            if self.device_registry and self._is_device_status_message(topic_parts):
                device_id = topic_parts[1]
                self.device_registry.update_device_status(device_id, payload, is_retained=msg.retain)
                return

            # Handle feedback messages
            if self.feedback_tracker and self._is_feedback_message(topic):
                # We need to derive the original topic from the feedback topic
                original_topic = '/'.join(topic_parts[:-1])
                self.feedback_tracker.handle_feedback_message(original_topic)
                return
            
            # Handle button commands
            if self.button_callback and self._is_button_command(topic, payload):
                self.logger.info("Button command received. Starting scene.")
                self.button_callback(payload)
                return
            
            # Log any messages that don't match the known patterns
            self.logger.debug(f"Received unhandled message on topic {msg.topic}: {payload}")
            
        except Exception as e:
            self.logger.error(f"Error processing message on {msg.topic}: {e}")
    
    # ==========================================================================
    # MESSAGE TYPE DETECTION
    # ==========================================================================
    
    def _is_device_status_message(self, topic_parts):
        """
        Check if message is a device status update.
        
        Args:
            topic_parts: List of topic parts split by '/'
            
        Returns:
            bool: True if this is a device status message
        """
        return (len(topic_parts) == 3 and 
                topic_parts[0] == 'devices' and 
                topic_parts[2] == 'status')
    
    def _is_feedback_message(self, topic):
        """
        Check if message is a feedback message.
        
        Args:
            topic: Full MQTT topic string
            
        Returns:
            bool: True if this is a feedback message
        """
        return topic.endswith('/feedback')
    
    def _is_button_command(self, topic, payload):
        """
        Check if message is a button/scene command from ESP32.
        
        Args:
            topic: Full MQTT topic string
            payload: Message payload content
            
        Returns:
            bool: True if this is a button command
        """
        return topic.endswith('/scene') and payload.upper() == 'START'