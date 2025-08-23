#!/usr/bin/env python3
import time
import threading
from utils.logging_setup import get_logger

class MQTTFeedbackTracker:
    def __init__(self, logger=None, feedback_timeout=1.0):
        self.logger = logger or get_logger('mqtt_feedback')
        
        # Feedback tracking system
        self.feedback_enabled = False  # Only during scene execution
        self.pending_feedbacks = {}  # {message_id: {'topic': topic, 'timestamp': time, 'status_topic': status_topic}}
        self.feedback_timeout = feedback_timeout
    
    def enable_feedback_tracking(self):
        """Enable feedback tracking during scene execution."""
        if not self.feedback_enabled:
            self.feedback_enabled = True
            self.pending_feedbacks.clear()
            self.logger.debug("MQTT feedback tracking enabled")
    
    def disable_feedback_tracking(self):
        """Disable feedback tracking during idle mode."""
        if self.feedback_enabled:
            self.feedback_enabled = False
            # Log any remaining pending feedbacks as warnings
            for msg_id, info in self.pending_feedbacks.items():
                self.logger.warning(f"Scene ended with pending feedback: {info['topic']}")
            self.pending_feedbacks.clear()
            self.logger.debug("MQTT feedback tracking disabled")
    
    def track_published_message(self, topic, message):
        """Track a published message for feedback if applicable."""
        if not self._should_expect_feedback(topic):
            return
        
        status_topic = self._get_status_topic(topic)
        msg_id = f"{topic}_{int(time.time()*1000)}"  # Unique ID
        
        self.pending_feedbacks[msg_id] = {
            'topic': topic,
            'status_topic': status_topic, 
            'timestamp': time.time()
        }
        
        self.logger.debug(f"📤 Sent: {topic} -> expecting feedback on: {status_topic}")
        
        # Start timeout check in background
        def check_timeout():
            time.sleep(self.feedback_timeout + 0.1)  # Small buffer
            self._check_pending_feedbacks()
        
        threading.Thread(target=check_timeout, daemon=True).start()
    
    def handle_feedback_message(self, status_topic, payload):
        """Process incoming status/feedback messages."""
        if not self.feedback_enabled:
            return
            
        current_time = time.time()
        
        # Find matching pending feedback
        for msg_id, info in list(self.pending_feedbacks.items()):
            if info['status_topic'] == status_topic:
                elapsed = current_time - info['timestamp']
                
                if payload.upper() == 'OK':
                    self.logger.info(f"✅ Feedback OK: {info['topic']} ({elapsed:.3f}s)")
                else:
                    self.logger.warning(f"❌ Feedback ERROR: {info['topic']} -> '{payload}' ({elapsed:.3f}s)")
                
                # Remove from pending
                del self.pending_feedbacks[msg_id]
                return
        
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
    
    def _check_pending_feedbacks(self):
        """Check for timed out feedback messages."""
        if not self.feedback_enabled:
            return
            
        current_time = time.time()
        timed_out = []
        
        for msg_id, info in self.pending_feedbacks.items():
            elapsed = current_time - info['timestamp']
            if elapsed > self.feedback_timeout:
                timed_out.append(msg_id)
        
        # Log timeouts and remove from pending
        for msg_id in timed_out:
            info = self.pending_feedbacks[msg_id]
            elapsed = current_time - info['timestamp']
            self.logger.warning(f"⏰ Feedback TIMEOUT: {info['topic']} (>{elapsed:.3f}s)")
            del self.pending_feedbacks[msg_id]