#!/usr/bin/env python3
import time
from utils.logging_setup import get_logger

class MQTTDeviceRegistry:
    def __init__(self, logger=None, device_timeout=180):  # 3 minutes timeout
        self.logger = logger or get_logger('mqtt_devices')
        self.connected_devices = {}
        self.device_timeout = device_timeout  # Seconds after which device is considered offline
    
    def update_device_status(self, device_id, status, is_retained=False):
        """Update device status and log changes, ignoring stale retained 'online' messages."""
        current_time = time.time()

        if is_retained and status.lower() == 'online':
            self.logger.debug(f"Ignoring stale retained 'online' status for {device_id}.")
            
            # Ensure the device is at least registered as offline if we've never seen it
            if device_id not in self.connected_devices:
                self.connected_devices[device_id] = {
                    'status': 'offline',
                    'last_updated': current_time
                }
            return

        # Get previous status if device existed
        previous_status = None
        if device_id in self.connected_devices:
            previous_status = self.connected_devices[device_id]['status']
        
        # Log connection if device was offline or didn't exist before
        if ((previous_status is None or previous_status == 'offline') and 
            status == 'online'):
            self.logger.warning(f"Device {device_id} connected")
        
        # Log disconnection if device was online
        elif (previous_status == 'online' and status == 'offline'):
            self.logger.warning(f"Device {device_id} disconnected")
        
        # Update device info
        self.connected_devices[device_id] = {
            'status': status,
            'last_updated': current_time
        }
        
        self.logger.debug(f"Device {device_id} status: {status}")
    
    def cleanup_stale_devices(self):
        """Check for devices that haven't sent status updates recently and mark them offline."""
        current_time = time.time()
        stale_devices = []
        
        for device_id, info in self.connected_devices.items():
            if info['status'] == 'online':
                time_since_update = current_time - info['last_updated']
                if time_since_update > self.device_timeout:
                    stale_devices.append(device_id)
        
        # Mark stale devices as offline
        for device_id in stale_devices:
            self.logger.warning(f"Device {device_id} timeout - marking as offline (last seen {self.device_timeout}s ago)")
            self.connected_devices[device_id]['status'] = 'offline'
            self.connected_devices[device_id]['last_updated'] = current_time
    
    def get_connected_devices(self):
        """Return the list of actually connected devices (with timeout cleanup)."""
        # Clean up stale devices first
        self.cleanup_stale_devices()
        
        return {
            device_id: info for device_id, info in self.connected_devices.items()
            if info['status'] == 'online'
        }
    
    def get_all_devices(self):
        """Return all devices with their status (with timeout cleanup)."""
        # Clean up stale devices first
        self.cleanup_stale_devices()
        
        return self.connected_devices.copy()
    
    def clear_devices(self):
        """Clear all device records."""
        self.connected_devices.clear()
        self.logger.info("Device registry cleared")
    
    def get_device_status_summary(self):
        """Get a summary of device statuses."""
        self.cleanup_stale_devices()
        
        online = sum(1 for info in self.connected_devices.values() if info['status'] == 'online')
        offline = sum(1 for info in self.connected_devices.values() if info['status'] == 'offline')
        
        return {
            'total_devices': len(self.connected_devices),
            'online_devices': online,
            'offline_devices': offline
        }