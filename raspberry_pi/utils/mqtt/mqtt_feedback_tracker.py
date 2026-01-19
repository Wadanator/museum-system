#!/usr/bin/env python3
"""
MQTT Feedback Tracker - Per-command feedback tracking.

Tracks each published command individually and waits for specific feedback.
Example: prefix/motor1 -> expects prefix/motor1/feedback
"""

import time
import threading
from utils.logging_setup import get_logger

class MQTTFeedbackTracker:
    def __init__(self, logger=None, feedback_timeout=2):
        self.logger = logger or get_logger('mqtt_feedback')
        self.feedback_enabled = False
        self.feedback_timeout = feedback_timeout
        
        # {original_topic: {'command': message, 'timer': Timer, 'start_time': time}}
        self.pending_feedbacks = {}
        self.lock = threading.Lock()
    
    def enable_feedback_tracking(self):
        with self.lock:
            if not self.feedback_enabled:
                self.feedback_enabled = True
                self.pending_feedbacks.clear()
                self.logger.info("MQTT feedback tracking enabled")
    
    def disable_feedback_tracking(self):
        with self.lock:
            if self.feedback_enabled:
                self.feedback_enabled = False
                
                for original_topic, data in self.pending_feedbacks.items():
                    data['timer'].cancel()
                    self.logger.warning(f"Scene ended with pending feedback on topic: {original_topic}")
                
                self.pending_feedbacks.clear()
                self.logger.info("MQTT feedback tracking disabled")

    def track_published_message(self, original_topic, message):
        """Track each command individually."""
        if not self.feedback_enabled:
            return

        # Skip audio/video (handled locally)
        if original_topic.endswith('/audio') or original_topic.endswith('/video'):
            self.logger.debug(f"Skipping feedback tracking for local topic: {original_topic}")
            return

        expected_feedback_topic = self._get_expected_feedback_topic(original_topic)
        if expected_feedback_topic is None:
            self.logger.debug(f"No feedback expected for topic: {original_topic}")
            return

        with self.lock:
            if original_topic in self.pending_feedbacks:
                # Cancel old timer for same command
                self.pending_feedbacks[original_topic]['timer'].cancel()
            
            timer = threading.Timer(
                self.feedback_timeout, 
                self._handle_feedback_timeout, 
                args=[original_topic, message]
            )
            
            self.pending_feedbacks[original_topic] = {
                'command': message,
                'timer': timer,
                'start_time': time.time(),
                'expected_feedback_topic': expected_feedback_topic
            }
            timer.start()
            self.logger.debug(f"📤 Sent: {original_topic} -> expecting feedback on: {expected_feedback_topic}")

    def handle_feedback_message(self, feedback_topic, feedback_payload):
        """Handle specific feedback message."""
        # Find which command this feedback belongs to
        original_topic = self._get_original_topic_from_feedback(feedback_topic)
        
        with self.lock:
            if original_topic and original_topic in self.pending_feedbacks:
                start_time = self.pending_feedbacks[original_topic]['start_time']
                elapsed_time = time.time() - start_time
                
                self.pending_feedbacks[original_topic]['timer'].cancel()
                del self.pending_feedbacks[original_topic]
                
                if feedback_payload.upper() == "OK":
                    self.logger.info(f"✅ Feedback OK: {original_topic} ({elapsed_time:.3f}s)")
                else:
                    self.logger.warning(f"⚠️ Feedback ERROR: {original_topic} -> {feedback_payload} ({elapsed_time:.3f}s)")
            else:
                self.logger.debug(f"Received feedback on {feedback_topic} with no pending command.")

    def _handle_feedback_timeout(self, original_topic, message):
        with self.lock:
            if original_topic in self.pending_feedbacks:
                expected_topic = self.pending_feedbacks[original_topic]['expected_feedback_topic']
                del self.pending_feedbacks[original_topic]
                self.logger.error(f"⏰ FEEDBACK TIMEOUT: No response from device. Topic: {original_topic}, Command: {message}, Expected: {expected_topic}")

    def _get_expected_feedback_topic(self, original_topic):
        """Get expected feedback topic for a command."""
        parts = original_topic.split('/')
        
        # NOVÉ: Ignoruj STOP príkazy a iné globálne správy
        if parts[-1].upper() in ['STOP', 'RESET', 'GLOBAL']:
            return None

        # Room device topics: prefix/motor1 -> prefix/motor1/feedback
        if len(parts) == 2 and parts[0].startswith('room'):
            return f"{original_topic}/feedback"
        
        # Device topics: devices/esp32_01/relay -> devices/esp32_01/relay/feedback
        if len(parts) >= 3 and parts[0] == 'devices':
            return f"{original_topic}/feedback"
            
        return None

    def _get_original_topic_from_feedback(self, feedback_topic):
        """Extract original topic from feedback topic."""
        if feedback_topic.endswith('/feedback'):
            return feedback_topic[:-9]  # Remove '/feedback'
        return None