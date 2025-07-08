#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
from utils.logging_setup import get_logger

class MQTTClient:
    def __init__(self, broker_host, broker_port=1883, client_id=None, logger=None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.connected = False
        # Use provided logger or get component-specific logger
        self.logger = logger if logger else get_logger('mqtt')
        
        # Fix for paho-mqtt 2.0+ compatibility
        try:
            # Try the new API first (paho-mqtt 2.0+)
            self.client = mqtt.Client(
                client_id=client_id,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1
            )
        except TypeError:
            # Fallback to old API (paho-mqtt 1.x)
            self.client = mqtt.Client(client_id=client_id)
        
        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
        else:
            self.connected = False
            self.logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.logger.info(f"Disconnected from MQTT broker. Return code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        self.logger.debug(f"Received message: {msg.topic} - {msg.payload.decode()}")
    
    def _on_publish(self, client, userdata, mid):
        self.logger.debug(f"Message published with ID: {mid}")
    
    def connect(self, timeout=10):
        try:
            self.client.connect(self.broker_host, self.broker_port, timeout)
            self.client.loop_start()
            
            # Wait for connection to be established
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                self.logger.error(f"Connection timeout after {timeout}s")
            return self.connected
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.logger.info("MQTT disconnected")
    
    def publish(self, topic, message, qos=0, retain=False):
        if not self.connected:
            self.logger.warning("Not connected to MQTT broker")
            return False
        
        try:
            # Convert message to JSON string if it's a dict
            if isinstance(message, dict):
                message = json.dumps(message)
            
            result = self.client.publish(topic, message, qos, retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"Publishing to {topic}: {message}")
            else:
                self.logger.error(f"Failed to publish to {topic}: RC {result.rc}")
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            return False
    
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

# Example usage and testing
if __name__ == "__main__":
    from utils.logging_setup import setup_logging
    logger = setup_logging()
    
    # Test the MQTT client
    client = MQTTClient("localhost", logger=logger)
    
    if client.connect():
        logger.info("Connection successful!")
        
        # Test publishing
        test_message = {"device": "test", "value": 42, "timestamp": time.time()}
        client.publish("test/topic", test_message)
        
        # Test subscribing
        client.subscribe("test/topic")
        
        # Keep alive for a bit
        time.sleep(2)
        
        client.disconnect()
        logger.info("Test completed")
    else:
        logger.error("Failed to connect to MQTT broker")
        logger.info("Make sure your MQTT broker is running on localhost:1883")