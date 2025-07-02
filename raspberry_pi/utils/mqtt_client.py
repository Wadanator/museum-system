#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
import logging
import sys
import os
from datetime import datetime

class MQTTClient:
    def __init__(self, broker_host, broker_port=1883, client_id=None, use_logging=True, logger=None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.use_logging = use_logging
        self.connected = False
        # Use provided logger or fallback to default
        self.logger = logger if logger else logging.getLogger('museum')
        
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
            if self.use_logging:
                self.logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
        else:
            self.connected = False
            if self.use_logging:
                self.logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if self.use_logging:
            self.logger.warning(f"Disconnected from MQTT broker. Return code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        if self.use_logging:
            self.logger.info(f"Received message: {msg.topic} - {msg.payload.decode()}")
    
    def _on_publish(self, client, userdata, mid):
        if self.use_logging:
            self.logger.info(f"Message published with ID: {mid}")
    
    def connect(self, timeout=10):
        try:
            self.client.connect(self.broker_host, self.broker_port, timeout)
            self.client.loop_start()
            
            # Wait for connection to be established
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected and self.use_logging:
                self.logger.error(f"Connection timeout after {timeout}s")
            return self.connected
        except Exception as e:
            if self.use_logging:
                self.logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            if self.use_logging:
                self.logger.info("MQTT disconnected")
    
    def publish(self, topic, message, qos=0, retain=False):
        if not self.connected:
            if self.use_logging:
                self.logger.warning("Not connected to MQTT broker")
            return False
        
        try:
            # Convert message to JSON string if it's a dict
            if isinstance(message, dict):
                message = json.dumps(message)
            
            result = self.client.publish(topic, message, qos, retain)
            
            if self.use_logging and result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Publishing to {topic}: {message}")
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS and self.use_logging:
                self.logger.error(f"Failed to publish to {topic}: RC {result.rc}")
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            if self.use_logging:
                self.logger.error(f"Error publishing message: {e}")
            return False
    
    def subscribe(self, topic, qos=0):
        if not self.connected:
            if self.use_logging:
                self.logger.warning("Not connected to MQTT broker")
            return False
        
        try:
            result = self.client.subscribe(topic, qos)
            if self.use_logging and result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Subscribed to topic: {topic}")
            elif self.use_logging:
                self.logger.error(f"Failed to subscribe to {topic}: RC {result[0]}")
            return result[0] == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            if self.use_logging:
                self.logger.error(f"Error subscribing to topic: {e}")
            return False
    
    def is_connected(self):
        return self.connected

# Example usage and testing
if __name__ == "__main__":
    # Set up logging same as first code
    from utils.logging_setup import setup_logging
    log = setup_logging()
    
    # Test the MQTT client
    client = MQTTClient("localhost", use_logging=True, logger=log)
    
    if client.connect():
        log.info("Connection successful!")
        
        # Test publishing
        test_message = {"device": "test", "value": 42, "timestamp": time.time()}
        client.publish("test/topic", test_message)
        
        # Test subscribing
        client.subscribe("test/topic")
        
        # Keep alive for a bit
        time.sleep(2)
        
        client.disconnect()
        log.info("Test completed")
    else:
        log.error("Failed to connect to MQTT broker")
        log.info("Make sure your MQTT broker is running on localhost:1883")