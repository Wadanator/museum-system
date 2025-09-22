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
    
    def __init__(self, logger=None, feedback_timeout=1.0):
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
        self.pending_feedbacks = {}  # {topic: {'topic': topic, 'timestamp': time, 'status_topic': status_topic}}
        self.timeout_threads = {}    # Track timeout threads to prevent duplicates
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
                self.timeout_threads.clear()
                self.logger.debug("MQTT feedback tracking enabled")
    
    def disable_feedback_tracking(self):
        """Disable feedback tracking during idle mode."""
        with self.lock:
            if self.feedback_enabled:
                self.feedback_enabled = False
                
                # Log any remaining pending feedbacks as warnings (avoid duplicates)
                logged_topics = set()
                for topic, info in self.pending_feedbacks.items():
                    if topic not in logged_topics:
                        self.logger.warning(f"Scene ended with pending feedback: {topic}")
                        logged_topics.add(topic)
                
                # Clear all tracking state
                self.pending_feedbacks.clear()
                self.timeout_threads.clear()
                self.logger.debug("MQTT feedback tracking disabled")
    
    # ==========================================================================
    # COMMAND TRACKING
    # ==========================================================================
    
    def track_published_message(self, topic, message):
        """
        Track a published message for feedback if applicable.
        
        Args:
            topic: MQTT topic where message was published
            message: Message content that was published
        """
        # Only track messages that should expect feedback
        if not self._should_expect_feedback(topic):
            return
        
        with self.lock:
            if not self.feedback_enabled:
                return
            
            status_topic = self._get_status_topic(topic)
            current_time = time.time()
            
            # === Remove Existing Tracking ===
            # Prevent duplicates by removing any existing pending feedback for same topic
            if topic in self.pending_feedbacks:
                del self.pending_feedbacks[topic]
            
            # Cancel any existing timeout thread for this topic
            if topic in self.timeout_threads:
                # The old thread will check the lock and find the topic is no longer pending
                pass  # Thread will naturally exit when it checks
            
            # === Add New Tracking Entry ===
            self.pending_feedbacks[topic] = {
                'topic': topic,
                'status_topic': status_topic, 
                'timestamp': current_time
            }
            
            self.logger.debug(f"📤 Sent: {topic} -> expecting feedback on: {status_topic}")
            
            # === Start Timeout Monitoring ===
            self._start_timeout_thread(topic, current_time)
    
    def _start_timeout_thread(self, topic, timestamp):
        """Start background thread to monitor for feedback timeout."""
        def check_timeout():
            time.sleep(self.feedback_timeout + 0.1)
            
            # Use lock to ensure thread safety and prevent race conditions
            with self.lock:
                # Double-check the topic is still pending and matches our timestamp
                if (topic in self.pending_feedbacks and 
                    self.pending_feedbacks[topic]['timestamp'] == timestamp and
                    self.feedback_enabled):
                    
                    elapsed = time.time() - timestamp
                    self.logger.warning(f"⏰ Feedback TIMEOUT: {topic} (>{elapsed:.3f}s)")
                    
                    # Remove from pending
                    if topic in self.pending_feedbacks:
                        del self.pending_feedbacks[topic]
                
                # Clean up thread tracking
                if topic in self.timeout_threads:
                    del self.timeout_threads[topic]
        
        # Track the timeout thread (only one per topic)
        thread = threading.Thread(target=check_timeout, daemon=True)
        self.timeout_threads[topic] = thread
        thread.start()
    
    # ==========================================================================
    # FEEDBACK PROCESSING
    # ==========================================================================
    
    def handle_feedback_message(self, status_topic, payload):
        """
        Process incoming status/feedback messages.
        
        Args:
            status_topic: Topic where feedback was received
            payload: Feedback message content
        """
        with self.lock:
            if not self.feedback_enabled:
                return
                
            current_time = time.time()
            
            # === Find Matching Pending Feedback ===
            topic_to_remove = None
            for topic, info in self.pending_feedbacks.items():
                if info['status_topic'] == status_topic:
                    elapsed = current_time - info['timestamp']
                    
                    # Log feedback result with appropriate level
                    if payload.upper() == 'OK':
                        self.logger.info(f"✅ Feedback OK: {topic} ({elapsed:.3f}s)")
                    else:
                        self.logger.warning(f"❌ Feedback ERROR: {topic} -> '{payload}' ({elapsed:.3f}s)")
                    
                    topic_to_remove = topic
                    break
            
            # === Remove Processed Feedback ===
            if topic_to_remove:
                del self.pending_feedbacks[topic_to_remove]
                # The timeout thread will naturally exit when it checks the lock
                if topic_to_remove in self.timeout_threads:
                    del self.timeout_threads[topic_to_remove]
            else:
                # Log unexpected feedback for debugging
                self.logger.debug(f"Unexpected feedback on {status_topic}: {payload}")
    
    # ==========================================================================
    # FEEDBACK LOGIC HELPERS
    # ==========================================================================
    
    def _should_expect_feedback(self, topic):
        """
        Determine if we should expect feedback for this topic.
        
        Args:
            topic: MQTT topic to check
            
        Returns:
            bool: True if feedback should be expected
        """
        if not self.feedback_enabled:
            return False
            
        # Skip audio/video topics (handled by RPI locally)
        if topic.endswith('/audio') or topic.endswith('/video'):
            return False
            
        # Skip status topics (these are feedback messages themselves)
        if topic.endswith('/status'):
            return False
            
        # Skip device status topics
        if '/status' in topic:
            return False
            
        return True
    
    def _get_status_topic(self, original_topic):
        """
        Get the corresponding status topic for feedback based on the original topic.
        
        Args:
            original_topic: The topic where command was published
            
        Returns:
            str: The status topic where feedback is expected
        """
        parts = original_topic.split('/')
        
        # === Room Topics ===
        # Examples: room1/light, room1/motor, room1/steam -> room1/status
        if len(parts) >= 2 and parts[0].startswith('room'):
            room_name = parts[0]  # room1, room2, etc.
            return f"{room_name}/status"
        
        # === Device Topics ===
        # Examples: devices/esp32_01/relay -> devices/esp32_01/status
        elif len(parts) >= 3 and parts[0] == 'devices':
            device_id = parts[1]  # esp32_01, esp32_02, etc.
            return f"devices/{device_id}/status"
        
        # === Default Case ===
        # Replace last part with 'status'
        else:
            status_parts = parts[:-1] + ['status']
            return '/'.join(status_parts)