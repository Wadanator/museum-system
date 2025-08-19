#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
import threading
from utils.logging_setup import get_logger

class MQTTClient:
    def __init__(self, broker_host, broker_port=1883, client_id=None, logger=None, 
                 retry_attempts=3, retry_sleep=5, connect_timeout=10, 
                 reconnect_timeout=30, reconnect_sleep=5, check_interval=60):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.connected = False
        self.logger = logger or get_logger('mqtt')
        self.connected_devices = {}
        
        # Connection parameters
        self.retry_attempts = retry_attempts
        self.retry_sleep = retry_sleep
        self.connect_timeout = connect_timeout
        self.reconnect_timeout = reconnect_timeout
        self.reconnect_sleep = reconnect_sleep
        self.check_interval = check_interval
        
        # State management
        self.shutdown_requested = False
        self.connection_lost_callback = None
        self.connection_restored_callback = None
        
        # NEW: Feedback tracking system
        self.feedback_enabled = False  # Only during scene execution
        self.pending_feedbacks = {}  # {message_id: {'topic': topic, 'timestamp': time, 'device_topic': device_topic}}
        self.feedback_timeout = 1.0  # 1 second timeout
        
        # Fix for paho-mqtt 2.0+ compatibility
        try:
            self.client = mqtt.Client(
                client_id=client_id,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1
            )
        except TypeError:
            self.client = mqtt.Client(client_id=client_id)
        
        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
    
    def set_connection_callbacks(self, lost_callback=None, restored_callback=None):
        """Set callbacks for connection state changes."""
        self.connection_lost_callback = lost_callback
        self.connection_restored_callback = restored_callback
    
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
                self.logger.warning(f"Scene ended with pending feedback: {info['device_topic']}")
            self.pending_feedbacks.clear()
            self.logger.debug("MQTT feedback tracking disabled")
    
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
        """Convert command topic to expected status topic."""
        # Examples:
        # "room1/led1/brightness" -> "room1/led1/status"  
        # "devices/esp32_01/relay" -> "devices/esp32_01/status"
        
        parts = original_topic.split('/')
        if len(parts) >= 2:
            # Replace last part with 'status'
            status_parts = parts[:-1] + ['status']
            return '/'.join(status_parts)
        return original_topic + '/status'
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            was_connected = self.connected
            self.connected = True
            self.logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            
            # Subscribe to device status topic
            self.subscribe("devices/+/status")
            
            # Subscribe to all possible status topics for feedback
            self.subscribe("+/+/status")  # room*/device*/status
            self.subscribe("devices/+/status")  # devices/esp32_*/status
            
            if not was_connected and self.connection_restored_callback:
                self.connection_restored_callback()
        else:
            self.connected = False
            self.logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        was_connected = self.connected
        self.connected = False
        self.logger.info(f"Disconnected from MQTT broker. Return code: {rc}")
        if was_connected and self.connection_lost_callback:
            self.connection_lost_callback()
    
    def _on_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split('/')
            payload = msg.payload.decode().strip()
            
            # Handle device status messages for connection tracking
            if len(topic_parts) == 3 and topic_parts[0] == 'devices' and topic_parts[2] == 'status':
                device_id = topic_parts[1]
                if (device_id in self.connected_devices and 
                    self.connected_devices[device_id]['status'] == 'online' and 
                    payload == 'offline'):
                    self.logger.warning(f"Device {device_id} disconnected")
                self.connected_devices[device_id] = {
                    'status': payload,
                    'last_updated': time.time()
                }
                self.logger.debug(f"Device {device_id} status: {payload}")
            
            # NEW: Handle feedback messages during scene execution
            if self.feedback_enabled and msg.topic.endswith('/status'):
                self._handle_feedback_message(msg.topic, payload)
                
        except Exception as e:
            self.logger.error(f"Error processing message on {msg.topic}: {e}")
    
    def _handle_feedback_message(self, status_topic, payload):
        """Process incoming status/feedback messages."""
        current_time = time.time()
        
        # Find matching pending feedback
        for msg_id, info in list(self.pending_feedbacks.items()):
            if info['device_topic'] == status_topic:
                elapsed = current_time - info['timestamp']
                
                if payload.upper() == 'OK':
                    self.logger.debug(f"✓ Feedback OK: {info['topic']} ({elapsed:.3f}s)")
                else:
                    self.logger.warning(f"✗ Feedback ERROR: {info['topic']} -> '{payload}' ({elapsed:.3f}s)")
                
                # Remove from pending
                del self.pending_feedbacks[msg_id]
                return
    
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
            self.logger.warning(f"✗ Feedback TIMEOUT: {info['topic']} (>{elapsed:.3f}s)")
            del self.pending_feedbacks[msg_id]
    
    def get_connected_devices(self):
        """Return the list of connected devices."""
        return {
            device_id: info for device_id, info in self.connected_devices.items()
            if info['status'] == 'online'
        }
    
    def _on_publish(self, client, userdata, mid):
        self.logger.debug(f"Message published with ID: {mid}")
    
    def publish(self, topic, message, qos=0, retain=False):
        if not self.connected:
            self.logger.warning("Not connected to MQTT broker")
            return False
        
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
            
            result = self.client.publish(topic, message, qos, retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"Publishing to {topic}: {message}")
                
                # NEW: Track feedback if enabled and applicable
                if self._should_expect_feedback(topic):
                    status_topic = self._get_status_topic(topic)
                    msg_id = f"{topic}_{int(time.time()*1000)}"  # Unique ID
                    
                    self.pending_feedbacks[msg_id] = {
                        'topic': topic,
                        'device_topic': status_topic, 
                        'timestamp': time.time()
                    }
                    
                    self.logger.debug(f"Expecting feedback on: {status_topic}")
                    
                    # Start timeout check in background
                    def check_timeout():
                        time.sleep(self.feedback_timeout + 0.1)  # Small buffer
                        self._check_pending_feedbacks()
                    
                    threading.Thread(target=check_timeout, daemon=True).start()
                
            else:
                self.logger.error(f"Failed to publish to {topic}: RC {result.rc}")
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            return False
    
    # ... rest of the existing methods remain unchanged ...
    def connect(self, timeout=10):
        try:
            self.client.connect(self.broker_host, self.broker_port, timeout)
            self.client.loop_start()
            
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                self.logger.error(f"Connection timeout after {timeout}s")
            return self.connected
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def connect_with_retry(self):
        """Connect to MQTT broker with retry logic."""
        for attempt in range(self.retry_attempts):
            if self.shutdown_requested:
                return False
            
            self.logger.info(f"MQTT connection attempt {attempt + 1}/{self.retry_attempts}")
            
            if self.connect(self.connect_timeout):
                return True
            
            if attempt < self.retry_attempts - 1:
                self.logger.warning(f"Connection failed, retrying in {self.retry_sleep}s...")
                time.sleep(self.retry_sleep)
        
        return False
    
    def establish_initial_connection(self):
        """Establish initial MQTT connection with error handling."""
        if not self.connect_with_retry():
            self.logger.critical("CRITICAL: Unable to establish MQTT connection")
            return False
        return True
    
    def check_and_reconnect(self):
        """Check connection and reconnect if needed."""
        if not self.connected:
            self.logger.warning("MQTT connection lost, attempting to reconnect...")
            if self.connect_with_retry():
                self.logger.info("MQTT connection restored")
                return True
            else:
                self.logger.error("Failed to restore MQTT connection")
                return False
        return True
    
    def manage_connection_health(self):
        """Manage MQTT connection health and return connection status."""
        if not self.check_and_reconnect():
            return False
        elif self.is_connected():
            return True
        return False
    
    def disconnect(self):
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.logger.info("MQTT disconnected")
    
    def subscribe(self, topic, qos=0):
        if not self.connected:
            self.logger.warning("Not connected to MQTT broker")
            return False
        
        try:
            result = self.client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Subscribed to topic: {topic}")
            else:
                self.logger.error(f"Failed to subscribe to {topic}: RC {result[0]}")
            return result[0] == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            self.logger.error(f"Error subscribing to topic: {e}")
            return False
    
    def is_connected(self):
        return self.connected
    
    def cleanup(self):
        """Clean up MQTT resources."""
        self.shutdown_requested = True
        self.disable_feedback_tracking()  # Clean up feedback tracking
        self.connected_devices.clear()
        self.disconnect()
        self.logger.info("MQTT client cleaned up")