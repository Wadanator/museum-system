#!/usr/bin/env python3
import time
import threading
from utils.logging_setup import get_logger

class MQTTFeedbackTracker:
    def __init__(self, logger=None, feedback_timeout=1.0):
        self.logger = logger or get_logger('mqtt_feedback')
        
        # Feedback tracking system
        self.feedback_enabled = False  # Only during scene execution
        self.pending_feedbacks = {}  # {topic: {'topic': topic, 'timestamp': time, 'status_topic': status_topic}}
        self.feedback_timeout = feedback_timeout
        self.timeout_threads = {}  # Track timeout threads to prevent duplicates
        self.lock = threading.Lock()  # Thread safety
    
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
                # Log any remaining pending feedbacks as warnings (but only once each)
                logged_topics = set()
                for topic, info in self.pending_feedbacks.items():
                    if topic not in logged_topics:
                        self.logger.warning(f"Scene ended with pending feedback: {topic}")
                        logged_topics.add(topic)
                self.pending_feedbacks.clear()
                self.timeout_threads.clear()
                self.logger.debug("MQTT feedback tracking disabled")
    
    def track_published_message(self, topic, message):
        """Track a published message for feedback if applicable."""
        if not self._should_expect_feedback(topic):
            return
        
        with self.lock:
            if not self.feedback_enabled:
                return
            
            status_topic = self._get_status_topic(topic)
            current_time = time.time()
            
            # Remove any existing pending feedback for the same topic
            if topic in self.pending_feedbacks:
                del self.pending_feedbacks[topic]
            
            # Cancel any existing timeout thread for this topic
            if topic in self.timeout_threads:
                # The old thread will check the lock and find the topic is no longer pending
                pass  # Thread will naturally exit when it checks
            
            # Add new tracking entry using topic as key (prevents duplicates)
            self.pending_feedbacks[topic] = {
                'topic': topic,
                'status_topic': status_topic, 
                'timestamp': current_time
            }
            
            self.logger.debug(f"📤 Sent: {topic} -> expecting feedback on: {status_topic}")
            
            # Start timeout check in background (only one per topic)
            def check_timeout():
                time.sleep(self.feedback_timeout + 0.1)
                # Use lock to ensure thread safety and prevent race conditions
                with self.lock:
                    # Double-check the topic is still pending and matches our timestamp
                    if (topic in self.pending_feedbacks and 
                        self.pending_feedbacks[topic]['timestamp'] == current_time and
                        self.feedback_enabled):
                        
                        elapsed = time.time() - current_time
                        self.logger.warning(f"⏰ Feedback TIMEOUT: {topic} (>{elapsed:.3f}s)")
                        
                        # Remove from pending
                        if topic in self.pending_feedbacks:
                            del self.pending_feedbacks[topic]
                    
                    # Clean up thread tracking
                    if topic in self.timeout_threads:
                        del self.timeout_threads[topic]
            
            # Track the timeout thread
            thread = threading.Thread(target=check_timeout, daemon=True)
            self.timeout_threads[topic] = thread
            thread.start()
    
    def handle_feedback_message(self, status_topic, payload):
        """Process incoming status/feedback messages."""
        with self.lock:
            if not self.feedback_enabled:
                return
                
            current_time = time.time()
            
            # Find matching pending feedback by status_topic
            topic_to_remove = None
            for topic, info in self.pending_feedbacks.items():
                if info['status_topic'] == status_topic:
                    elapsed = current_time - info['timestamp']
                    
                    if payload.upper() == 'OK':
                        self.logger.info(f"✅ Feedback OK: {topic} ({elapsed:.3f}s)")
                    else:
                        self.logger.warning(f"❌ Feedback ERROR: {topic} -> '{payload}' ({elapsed:.3f}s)")
                    
                    topic_to_remove = topic
                    break
            
            # Remove the processed feedback
            if topic_to_remove:
                del self.pending_feedbacks[topic_to_remove]
                # The timeout thread will naturally exit when it checks the lock
                if topic_to_remove in self.timeout_threads:
                    del self.timeout_threads[topic_to_remove]
            else:
                # If no matching pending feedback found, log it as unexpected
                self.logger.debug(f"Unexpected feedback on {status_topic}: {payload}")
    
    def _should_expect_feedback(self, topic):
        """Determine if we should expect feedback for this topic."""
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
        """Get the status topic for feedback based on the original topic."""
        parts = original_topic.split('/')
        
        # Room topics (room1/light, room1/motor, room1/steam)
        if len(parts) >= 2 and parts[0].startswith('room'):
            room_name = parts[0]  # room1, room2, etc.
            return f"{room_name}/status"
        
        # Device topics (devices/esp32_01/relay)
        elif len(parts) >= 3 and parts[0] == 'devices':
            device_id = parts[1]  # esp32_01, esp32_02, etc.
            return f"devices/{device_id}/status"
        
        # Default case: return the last part as status
        else:
            status_parts = parts[:-1] + ['status']
            return '/'.join(status_parts)