#!/usr/bin/env python3
"""
MQTT Device Registry - Tracks connected devices and their status.

Manages device connection status, handles retained message filtering,
and provides device timeout detection to identify offline devices.
"""

import threading
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
            logger: Logger instance for device status messages.
            device_timeout: Seconds after which a device is considered
                offline (default: 3 minutes).
        """
        self.logger = logger or get_logger('mqtt_devices')
        self.connected_devices = {}
        self._lock = threading.Lock()
        # Seconds after which a device is considered offline
        self.device_timeout = device_timeout
        # Optional callback triggered immediately on each status change.
        self.on_status_change = None

    # ==========================================================================
    # DEVICE STATUS MANAGEMENT
    # ==========================================================================

    def update_device_status(self, device_id, status, is_retained=False):
        """
        Update device status and log changes, filtering stale retained messages.

        Args:
            device_id: Unique identifier for the device.
            status: Current device status ('online' or 'offline').
            is_retained: Whether this is a retained message from the broker.
        """
        current_time = time.time()

        with self._lock:
            # === Handle Retained Message Filtering ===
            if is_retained and status.lower() == 'online':
                self.logger.debug(
                    f"Ignoring stale retained 'online' status for {device_id}."
                )
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

            if ((previous_status is None or previous_status == 'offline') and
                    status == 'online'):
                self.logger.warning(f"Device {device_id} connected")
            elif previous_status == 'online' and status == 'offline':
                self.logger.warning(f"Device {device_id} disconnected")

            # === Update Device Registry ===
            self.connected_devices[device_id] = {
                'status': status,
                'last_updated': current_time
            }

        self.logger.debug(f"Device {device_id} status: {status}")

        # Notify subscribers only when the status actually changed (outside lock).
        if self.on_status_change and previous_status != status:
            self.on_status_change(device_id, status)

    # ==========================================================================
    # DEVICE TIMEOUT MANAGEMENT
    # ==========================================================================

    def cleanup_stale_devices(self):
        """
        Check for devices that have not sent status updates recently and mark them offline.

        Automatically detects devices that have timed out and marks them as
        offline to maintain accurate device status tracking.
        """
        current_time = time.time()
        stale_devices = []

        with self._lock:
            for device_id, info in self.connected_devices.items():
                if info['status'] == 'online':
                    if current_time - info['last_updated'] > self.device_timeout:
                        stale_devices.append(device_id)

            for device_id in stale_devices:
                self.logger.warning(
                    f"Device {device_id} timeout - marking as offline "
                    f"(last seen {self.device_timeout}s ago)"
                )
                self.connected_devices[device_id]['status'] = 'offline'
                self.connected_devices[device_id]['last_updated'] = current_time

        # Notify subscribers outside the lock
        for device_id in stale_devices:
            if self.on_status_change:
                self.on_status_change(device_id, 'offline')

    # ==========================================================================
    # DEVICE QUERY METHODS
    # ==========================================================================

    def get_connected_devices(self, cleanup=True):
        """
        Return the list of currently connected devices.

        Performs automatic cleanup of stale devices before returning results.

        Returns:
            dict: Dictionary of connected devices with their info.
        """
        if cleanup:
            self.cleanup_stale_devices()

        with self._lock:
            return {
                device_id: info
                for device_id, info in self.connected_devices.items()
                if info['status'] == 'online'
            }

    def get_all_devices(self):
        """
        Return all devices with their current status.

        Performs automatic cleanup of stale devices before returning results.

        Returns:
            dict: Copy of all device records with current status.
        """
        self.cleanup_stale_devices()

        with self._lock:
            return self.connected_devices.copy()

    def get_device_status_summary(self):
        """
        Get a summary of device statuses.

        Returns:
            dict: Summary containing total, online, and offline device counts.
        """
        self.cleanup_stale_devices()

        with self._lock:
            online = sum(
                1 for info in self.connected_devices.values()
                if info['status'] == 'online'
            )
            offline = sum(
                1 for info in self.connected_devices.values()
                if info['status'] == 'offline'
            )
            total = len(self.connected_devices)

        return {
            'total_devices': total,
            'online_devices': online,
            'offline_devices': offline
        }

    # ==========================================================================
    # REGISTRY MANAGEMENT
    # ==========================================================================

    def clear_devices(self):
        """Clear all device records from the registry."""
        with self._lock:
            self.connected_devices.clear()
        self.logger.debug("Device registry cleared")