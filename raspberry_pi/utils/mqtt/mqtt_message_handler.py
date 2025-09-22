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
    
    # ==========================================================================
    # MESSAGE PROCESSING
    # ==========================================================================
    
    def handle_message(self, msg):
        """
        Process incoming MQTT messages and route to appropriate handlers.
        
        Args:
            msg: MQTT message object containing topic, payload, and metadata
        """
        try:
            topic_parts = msg.topic.split('/')
            payload = msg.payload.decode().strip()
            
            # === Device Status Messages ===
            # Format: devices/{device_id}/status
            if self._is_device_status_message(topic_parts):
                if self.device_registry:
                    # Pass the msg.retain flag to handle stale retained messages
                    self.device_registry.update_device_status(
                        device_id=topic_parts[1], 
                        status=payload, 
                        is_retained=msg.retain
                    )
                return
            
            # === Feedback/Status Messages ===
            # Format: {room_id}/status or devices/{device_id}/status
            if self._is_feedback_message(msg.topic):
                if self.feedback_tracker:
                    self.feedback_tracker.handle_feedback_message(msg.topic, payload)
                return
            
            # === Button/Scene Commands ===
            # Format: {room_id}/scene with payload 'START'
            if self._is_button_command(msg.topic, payload):
                if self.button_callback:
                    self.logger.info(f"Remote button press received: {msg.topic} = {payload}")
                    self.button_callback()
                else:
                    self.logger.warning(f"Button command received but no callback set: {msg.topic}")
                return
            
            # === Unhandled Messages ===
            # Log other messages for debugging purposes
            self.logger.debug(f"Unhandled message on {msg.topic}: {payload}")
            
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
        Check if message is a feedback/status message.
        
        Args:
            topic: Full MQTT topic string
            
        Returns:
            bool: True if this is a feedback message
        """
        return topic.endswith('/status')
    
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