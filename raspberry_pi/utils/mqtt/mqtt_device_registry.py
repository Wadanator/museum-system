#!/usr/bin/env python3
import time
from utils.logging_setup import get_logger

class MQTTDeviceRegistry:
    def __init__(self, logger=None):
        self.logger = logger or get_logger('mqtt_devices')
        self.connected_devices = {}
    
    def update_device_status(self, device_id, status):
        """Update device status and log changes."""
        # Get previous status if device existed
        previous_status = None
        if device_id in self.connected_devices:
            previous_status = self.connected_devices[device_id]['status']
        
        # Log connection if device was offline or didn't exist before
        if ((previous_status is None or previous_status == 'offline') and 
            status == 'online'):
            self.logger.info(f"Device {device_id} connected")
        
        # Log disconnection if device was online
        elif (previous_status == 'online' and status == 'offline'):
            self.logger.warning(f"Device {device_id} disconnected")
        
        # Update device info
        self.connected_devices[device_id] = {
            'status': status,
            'last_updated': time.time()
        }
        
        self.logger.debug(f"Device {device_id} status: {status}")
    
    def get_connected_devices(self):
        """Return the list of connected devices."""
        return {
            device_id: info for device_id, info in self.connected_devices.items()
            if info['status'] == 'online'
        }
    
    def get_all_devices(self):
        """Return all devices with their status."""
        return self.connected_devices.copy()
    
    def clear_devices(self):
        """Clear all device records."""
        self.connected_devices.clear()
        self.logger.info("Device registry cleared")