#!/usr/bin/env python3
"""
MQTT Feedback Tracker - Tracks command acknowledgments and responses.

Monitors published commands and waits for corresponding status/feedback messages.
Provides timeout detection for commands that don't receive acknowledgments.
Only active during scene execution to avoid noise during idle periods.
"""

import time
import threading
from utils.logging_setup import get_logger

class MQTTFeedbackTracker:
    """
    Feedback tracker for monitoring MQTT command acknowledgments.
    
    Tracks published commands and waits for corresponding feedback messages.
    Provides timeout detection and is only active during scene execution.
    """
    
    def __init__(self, logger=None, feedback_timeout=5.0):
        """
        Initialize feedback tracker.
        
        Args:
            logger: Logger instance for feedback messages
            feedback_timeout: Timeout in seconds to wait for feedback
        """
        self.logger = logger or get_logger('mqtt_feedback')
        
        # === Feedback Tracking Configuration ===
        self.feedback_enabled = False  # Only enabled during scene execution
        self.feedback_timeout = feedback_timeout
        
        # === Tracking State ===
        # {original_topic: {'command': message, 'timer': threading.Timer}}
        self.pending_feedbacks = {}
        self.lock = threading.Lock() # Thread safety for concurrent access
    
    # ==========================================================================
    # FEEDBACK TRACKING CONTROL
    # ==========================================================================
    
    def enable_feedback_tracking(self):
        """Enable feedback tracking during scene execution."""
        with self.lock:
            if not self.feedback_enabled:
                self.feedback_enabled = True
                self.pending_feedbacks.clear()
                self.logger.info("MQTT feedback tracking enabled")
    
    def disable_feedback_tracking(self):
        """Disable feedback tracking during idle mode."""
        with self.lock:
            if self.feedback_enabled:
                self.feedback_enabled = False
                
                # Cancel any pending timers and log warnings
                for original_topic, data in self.pending_feedbacks.items():
                    data['timer'].cancel()
                    self.logger.warning(f"Scene ended with pending feedback on topic: {original_topic}")
                
                self.pending_feedbacks.clear()
                self.logger.info("MQTT feedback tracking disabled")

    # ==========================================================================
    # COMMAND TRACKING
    # ==========================================================================

    def track_published_message(self, original_topic, message):
        """
        Start tracking a published message for feedback.
        
        Args:
            original_topic: The MQTT topic the command was sent to.
            message: The message payload of the command.
        """
        if not self.feedback_enabled:
            return

        feedback_topic = self._get_feedback_topic(original_topic)
        if feedback_topic is None:
            self.logger.debug(f"Topic {original_topic} is not a device topic, skipping feedback tracking.")
            return

        with self.lock:
            if original_topic in self.pending_feedbacks:
                # Cancel old timer to prevent duplicate timeout messages
                self.pending_feedbacks[original_topic]['timer'].cancel()
            
            # Create a new timer for this command
            timer = threading.Timer(
                self.feedback_timeout, 
                self._handle_feedback_timeout, 
                args=[original_topic, message]
            )
            
            self.pending_feedbacks[original_topic] = {
                'command': message,
                'timer': timer
            }
            timer.start()
            self.logger.debug(f"Tracking feedback for topic '{original_topic}' with message '{message}' on feedback topic '{feedback_topic}'")

    # ==========================================================================
    # FEEDBACK HANDLING
    # ==========================================================================
    
    def handle_feedback_message(self, original_topic):
        """
        Handle an incoming feedback message and stop tracking.
        
        Args:
            original_topic: The original topic of the command that the feedback relates to.
        """
        with self.lock:
            if original_topic in self.pending_feedbacks:
                # Cancel the pending timeout timer
                self.pending_feedbacks[original_topic]['timer'].cancel()
                del self.pending_feedbacks[original_topic]
                self.logger.info(f"Feedback received for command on '{original_topic}'. Tracking stopped.")
            else:
                self.logger.debug(f"Received feedback for an untracked command on '{original_topic}'.")

    def _handle_feedback_timeout(self, original_topic, message):
        """
        Internal method called when a feedback timeout occurs.
        """
        with self.lock:
            if original_topic in self.pending_feedbacks:
                del self.pending_feedbacks[original_topic]
                self.logger.error(f"FEEDBACK TIMEOUT: No response from device. Topic: {original_topic}, Command: {message}")

    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def _get_feedback_topic(self, original_topic):
        """
        Get the corresponding feedback topic based on the original command topic.
        
        Args:
            original_topic: The topic where the command was published.
            
        Returns:
            str: The topic where feedback is expected, or None if not applicable.
        """
        parts = original_topic.split('/')
        
        # Room topics like 'room1/light', 'room1/motor1', 'room1/motor2'
        if len(parts) == 2 and parts[0].startswith('room') and parts[1] not in ['audio', 'video']:
            return f"{original_topic}/feedback"
        
        # Device topics like 'devices/esp32_01/relay'
        if len(parts) == 3 and parts[0] == 'devices' and parts[2] not in ['status', 'feedback']:
            return f"{original_topic}/feedback"
            
        return None