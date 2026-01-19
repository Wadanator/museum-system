#!/usr/bin/env python3
"""
MQTT Device Registry - Tracks connected devices and their status.

Manages device connection status, handles retained message filtering,
and provides device timeout detection to identify offline devices.
"""

import time
from utils.logging_setup import get_logger


class MQTTDeviceRegistry:
    """
    Device registry for tracking MQTT device connections and status.
    
    Handles device status updates, filters stale retained messages,
    and automatically detects offline devices based on timeout.
    """
    
    def __init__(self, logger=None, device_timeout=180):
        """
        Initialize device registry.
        
        Args:
            logger: Logger instance for device status messages
            device_timeout: Seconds after which device is considered offline (default: 3 minutes)
        """
        self.logger = logger or get_logger('mqtt_devices')
        self.connected_devices = {}
        self.device_timeout = device_timeout  # Seconds after which device is considered offline
    
    # ==========================================================================
    # DEVICE STATUS MANAGEMENT
    # ==========================================================================
    
    def update_device_status(self, device_id, status, is_retained=False):
        """
        Update device status and log changes, filtering stale retained messages.
        
        Args:
            device_id: Unique identifier for the device
            status: Current device status ('online' or 'offline')
            is_retained: Whether this is a retained message from broker
        """
        current_time = time.time()

        # === Handle Retained Message Filtering ===
        # Ignore stale retained 'online' messages to prevent false positives
        if is_retained and status.lower() == 'online':
            self.logger.debug(f"Ignoring stale retained 'online' status for {device_id}.")
            
            # Ensure the device is at least registered as offline if we've never seen it
            if device_id not in self.connected_devices:
                self.connected_devices[device_id] = {
                    'status': 'offline',
                    'last_updated': current_time
                }
            return

        # === Status Change Detection and Logging ===
        previous_status = None
        if device_id in self.connected_devices:
            previous_status = self.connected_devices[device_id]['status']
        
        # Log device connection (was offline or new device, now online)
        if ((previous_status is None or previous_status == 'offline') and 
            status == 'online'):
            self.logger.warning(f"Device {device_id} connected")
        
        # Log device disconnection (was online, now offline)
        elif (previous_status == 'online' and status == 'offline'):
            self.logger.warning(f"Device {device_id} disconnected")
        
        # === Update Device Registry ===
        self.connected_devices[device_id] = {
            'status': status,
            'last_updated': current_time
        }
        
        self.logger.debug(f"Device {device_id} status: {status}")
    
    # ==========================================================================
    # DEVICE TIMEOUT MANAGEMENT
    # ==========================================================================
    
    def cleanup_stale_devices(self):
        """
        Check for devices that haven't sent status updates recently and mark them offline.
        
        Automatically detects devices that have timed out and marks them as offline
        to maintain accurate device status tracking.
        """
        current_time = time.time()
        stale_devices = []
        
        # Find devices that haven't updated within timeout period
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
    
    # ==========================================================================
    # DEVICE QUERY METHODS
    # ==========================================================================
    
    def get_connected_devices(self):
        """
        Return the list of currently connected devices.
        
        Performs automatic cleanup of stale devices before returning results.
        
        Returns:
            dict: Dictionary of connected devices with their info
        """
        # Clean up stale devices first
        self.cleanup_stale_devices()
        
        return {
            device_id: info for device_id, info in self.connected_devices.items()
            if info['status'] == 'online'
        }
    
    def get_all_devices(self):
        """
        Return all devices with their current status.
        
        Performs automatic cleanup of stale devices before returning results.
        
        Returns:
            dict: Copy of all device records with current status
        """
        # Clean up stale devices first
        self.cleanup_stale_devices()
        
        return self.connected_devices.copy()
    
    def get_device_status_summary(self):
        """
        Get a summary of device statuses.
        
        Returns:
            dict: Summary containing total, online, and offline device counts
        """
        self.cleanup_stale_devices()
        
        online = sum(1 for info in self.connected_devices.values() if info['status'] == 'online')
        offline = sum(1 for info in self.connected_devices.values() if info['status'] == 'offline')
        
        return {
            'total_devices': len(self.connected_devices),
            'online_devices': online,
            'offline_devices': offline
        }
    
    # ==========================================================================
    # REGISTRY MANAGEMENT
    # ==========================================================================
    
    def clear_devices(self):
        """Clear all device records from registry."""
        self.connected_devices.clear()
        self.logger.debug("Device registry cleared")