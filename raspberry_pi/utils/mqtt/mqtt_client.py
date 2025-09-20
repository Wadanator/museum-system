#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
from utils.logging_setup import get_logger

class MQTTClient:
    def __init__(self, broker_host, broker_port=1883, client_id=None, logger=None, 
                 room_id=None, retry_attempts=3, retry_sleep=5, connect_timeout=10, 
                 reconnect_timeout=30, reconnect_sleep=5, check_interval=60):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.room_id = room_id
        self.connected = False
        self.logger = logger or get_logger('mqtt')
        
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
        
        # External handlers (will be injected)
        self.message_handler = None
        self.feedback_tracker = None
        self.device_registry = None
        
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
    
    def set_handlers(self, message_handler=None, feedback_tracker=None, device_registry=None):
        """Set external handlers for message processing."""
        self.message_handler = message_handler
        self.feedback_tracker = feedback_tracker
        self.device_registry = device_registry
    
    def set_connection_callbacks(self, lost_callback=None, restored_callback=None):
        """Set callbacks for connection state changes."""
        self.connection_lost_callback = lost_callback
        self.connection_restored_callback = restored_callback
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            was_connected = self.connected
            self.connected = True
            self.logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            
            # Subscribe len na svoj room a device status
            self.subscribe("devices/+/status")
            self.subscribe(f"{self.room_id}/status")
            self.subscribe(f"{self.room_id}/scene")
            
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
        """Delegate message handling to external handler."""
        if self.message_handler:
            self.message_handler.handle_message(msg)
    
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
                
                # Notify feedback tracker if available
                if self.feedback_tracker:
                    self.feedback_tracker.track_published_message(topic, message)
                    
            else:
                self.logger.error(f"Failed to publish to {topic}: RC {result.rc}")
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            return False
    
    def connect(self, timeout=10):
        try:
            if hasattr(self.client, '_sock') and self.client._sock:
                self.client.disconnect()
                
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
        self.disconnect()
        self.logger.info("MQTT client cleaned up")