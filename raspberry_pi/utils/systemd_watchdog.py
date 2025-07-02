#!/usr/bin/env python3
"""
SystemdWatchdog Utility for Museum System
Handles systemd watchdog heartbeat notifications
File: raspberry_pi/utils/systemd_watchdog.py
"""

import os
import time
import threading
import logging
from datetime import datetime

class SystemdWatchdog:
    """
    Handles systemd watchdog heartbeat notifications to prevent service restarts.
    
    This class automatically detects if running under systemd supervision with
    watchdog enabled and sends periodic heartbeat notifications to keep the
    service healthy.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the SystemdWatchdog.
        
        Args:
            logger: Optional logger instance. If None, uses default logging.
        """
        self.logger = logger if logger else logging.getLogger(__name__)
        
        # Watchdog state
        self.enabled = False
        self.interval = None
        self.timer = None
        self.running = False
        self.heartbeat_count = 0
        self.failed_heartbeats = 0
        self.last_heartbeat_time = None
        self.start_time = None
        
        # Initialize watchdog configuration
        self._initialize_watchdog()
    
    def _initialize_watchdog(self):
        """Initialize watchdog based on systemd environment variables."""
        # Check if we're running under systemd with watchdog
        watchdog_usec = os.environ.get('WATCHDOG_USEC')
        watchdog_pid = os.environ.get('WATCHDOG_PID')
        notify_socket = os.environ.get('NOTIFY_SOCKET')
        
        self.logger.info("Initializing systemd watchdog...")
        self.logger.info(f"WATCHDOG_USEC: {watchdog_usec}")
        self.logger.info(f"WATCHDOG_PID: {watchdog_pid}")
        self.logger.info(f"NOTIFY_SOCKET: {notify_socket}")
        self.logger.info(f"Current PID: {os.getpid()}")
        
        if watchdog_usec:
            try:
                # Convert microseconds to seconds and use half the interval for safety
                watchdog_timeout = int(watchdog_usec) / 1000000.0
                self.interval = watchdog_timeout / 2.0  # 50% safety margin
                self.enabled = True
                
                self.logger.info("Systemd watchdog ENABLED")
                self.logger.info(f"  - Watchdog timeout: {watchdog_timeout:.1f}s")
                self.logger.info(f"  - Heartbeat interval: {self.interval:.1f}s (50% safety margin)")
                
                # Validate the interval is reasonable
                if self.interval < 1.0:
                    self.logger.warning(f"Very short watchdog interval ({self.interval:.1f}s) - system may be unstable")
                elif self.interval > 60.0:
                    self.logger.warning(f"Very long watchdog interval ({self.interval:.1f}s) - slow failure detection")
                    
            except (ValueError, TypeError) as e:
                self.logger.error(f"Invalid WATCHDOG_USEC value '{watchdog_usec}': {e}")
                self.logger.error("Watchdog DISABLED due to invalid configuration")
                self.enabled = False
        else:
            self.logger.info("No systemd watchdog configured (WATCHDOG_USEC not set)")
            self.logger.info("Running without watchdog supervision")
            
            # Optional: Enable test mode for development
            # Uncomment the lines below to enable watchdog in non-systemd environments
            # self.logger.warning("Enabling test mode watchdog")
            # self.interval = 15.0  # 15 second heartbeat
            # self.enabled = True
    
    def start(self):
        """Start the watchdog heartbeat timer."""
        if not self.enabled:
            self.logger.info("Watchdog start requested but watchdog is disabled")
            return
        
        if self.running:
            self.logger.warning("Watchdog already running")
            return
        
        self.running = True
        self.start_time = time.time()
        self.last_heartbeat_time = time.time()
        
        self.logger.info("Starting systemd watchdog supervision")
        self.logger.info(f"   Initial heartbeat in {self.interval:.1f} seconds")
        
        # Send immediate heartbeat to signal we're starting
        self._send_heartbeat()
    
    def stop(self):
        """Stop the watchdog heartbeat timer."""
        if self.timer:
            self.timer.cancel()
            self.logger.info("Watchdog timer cancelled")
            
        self.running = False
        
        if self.enabled and self.start_time:
            uptime = time.time() - self.start_time
            self.logger.info("Systemd watchdog supervision STOPPED")
            self.logger.info(f"   Total uptime: {uptime:.1f}s")
            self.logger.info(f"   Total heartbeats: {self.heartbeat_count}")
            self.logger.info(f"   Failed heartbeats: {self.failed_heartbeats}")
            
            if self.failed_heartbeats > 0:
                failure_rate = (self.failed_heartbeats / max(self.heartbeat_count, 1)) * 100
                self.logger.warning(f"   Heartbeat failure rate: {failure_rate:.1f}%")
    
    def _send_heartbeat(self):
        """Send a watchdog heartbeat notification to systemd."""
        if not self.running:
            self.logger.debug("Heartbeat cancelled - watchdog not running")
            return
        
        try:
            heartbeat_sent = self._try_send_notification()
            current_time = time.time()
            
            if heartbeat_sent:
                self.heartbeat_count += 1
                self.last_heartbeat_time = current_time
                
                # Detailed logging based on heartbeat count
                if self.heartbeat_count == 1:
                    self.logger.info("First watchdog heartbeat sent successfully")
                elif self.heartbeat_count <= 5:
                    self.logger.info(f"Watchdog heartbeat #{self.heartbeat_count} - system healthy")
                else:
                    self.logger.debug(f"Watchdog heartbeat #{self.heartbeat_count} at {datetime.now().strftime('%H:%M:%S')}")
                
                # Log milestone heartbeats at INFO level
                if self.heartbeat_count % 20 == 0:  # Every ~5 minutes at 15s intervals
                    uptime = current_time - self.start_time if self.start_time else 0
                    self.logger.info(f"Watchdog milestone: {self.heartbeat_count} heartbeats, {uptime/60:.1f}min uptime")
                
            else:
                # All notification methods failed
                self.failed_heartbeats += 1
                self.logger.error(f"Watchdog heartbeat FAILED - all methods unsuccessful")
                self.logger.error(f"   Failed heartbeat #{self.failed_heartbeats}")
                
                # Log critical failure pattern
                if self.failed_heartbeats >= 3:
                    self.logger.critical(f"CRITICAL: {self.failed_heartbeats} consecutive watchdog failures!")
                    self.logger.critical("   Check systemd configuration and systemd-notify availability")
            
            # Schedule next heartbeat regardless of success/failure
            if self.running:
                self.timer = threading.Timer(self.interval, self._send_heartbeat)
                self.timer.daemon = True
                self.timer.start()
                
        except Exception as e:
            self.failed_heartbeats += 1
            self.logger.error(f"Watchdog heartbeat EXCEPTION: {e}")
            self.logger.error(f"   Exception type: {type(e).__name__}")
            self.logger.error(f"   Failed heartbeat #{self.failed_heartbeats}")
            
            # Still schedule next heartbeat to keep trying
            if self.running:
                self.timer = threading.Timer(self.interval, self._send_heartbeat)
                self.timer.daemon = True
                self.timer.start()
    
    def _try_send_notification(self):
        """
        Try multiple methods to send watchdog notification to systemd.
        
        Returns:
            bool: True if notification was sent successfully, False otherwise.
        """
        # Method 1: Use systemd-notify command
        try:
            result = os.system('systemd-notify WATCHDOG=1 2>/dev/null')
            if result == 0:
                self.logger.debug("Used systemd-notify command")
                return True
            else:
                self.logger.debug(f"systemd-notify command failed with exit code: {result}")
        except Exception as e:
            self.logger.debug(f"systemd-notify command exception: {e}")
        
        # Method 2: Try direct socket communication (fallback)
        try:
            notify_socket = os.environ.get('NOTIFY_SOCKET')
            if notify_socket:
                import socket
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                sock.sendto(b'WATCHDOG=1', notify_socket)
                sock.close()
                self.logger.debug("Used direct socket notification")
                return True
        except Exception as e:
            self.logger.debug(f"Direct socket notification failed: {e}")
        
        # Method 3: Check if systemd-notify is available
        try:
            import subprocess
            result = subprocess.run(['which', 'systemd-notify'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # systemd-notify exists, try it directly
                result = subprocess.run(['systemd-notify', 'WATCHDOG=1'], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    self.logger.debug("Used subprocess systemd-notify")
                    return True
        except Exception as e:
            self.logger.debug(f"Subprocess systemd-notify failed: {e}")
        
        # All methods failed
        return False
    
    def get_status(self):
        """
        Get comprehensive watchdog status for health checks.
        
        Returns:
            dict: Status information including health, counts, and timing.
        """
        if not self.enabled:
            return {
                'enabled': False,
                'status': 'disabled',
                'message': 'Watchdog not configured'
            }
        
        current_time = time.time()
        uptime = current_time - self.start_time if self.start_time else 0
        time_since_last = current_time - self.last_heartbeat_time if self.last_heartbeat_time else float('inf')
        
        # Determine status
        if not self.running:
            status = 'stopped'
            message = 'Watchdog supervision stopped'
        elif time_since_last > self.interval * 2:  # More than 2 intervals since last heartbeat
            status = 'stalled'
            message = f'No heartbeat for {time_since_last:.1f}s (expected every {self.interval:.1f}s)'
        elif self.failed_heartbeats > 0:
            failure_rate = (self.failed_heartbeats / max(self.heartbeat_count, 1)) * 100
            if failure_rate > 10:  # More than 10% failure rate
                status = 'degraded'
                message = f'High failure rate: {failure_rate:.1f}%'
            else:
                status = 'healthy'
                message = f'Operating normally with {failure_rate:.1f}% failures'
        else:
            status = 'healthy'
            message = 'Operating normally'
        
        return {
            'enabled': True,
            'running': self.running,
            'status': status,
            'message': message,
            'heartbeat_count': self.heartbeat_count,
            'failed_heartbeats': self.failed_heartbeats,
            'uptime_seconds': uptime,
            'interval_seconds': self.interval,
            'time_since_last_heartbeat': time_since_last
        }
    
    def is_healthy(self):
        """
        Check if the watchdog is operating normally.
        
        Returns:
            bool: True if watchdog is healthy or disabled, False if there are issues.
        """
        status = self.get_status()
        return status['status'] in ['disabled', 'healthy']
    
    def force_heartbeat(self):
        """
        Force an immediate heartbeat (useful for testing).
        
        Returns:
            bool: True if heartbeat was sent successfully.
        """
        if not self.enabled:
            self.logger.warning("Cannot force heartbeat - watchdog disabled")
            return False
        
        self.logger.info("Forcing immediate watchdog heartbeat")
        return self._try_send_notification()
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.stop()
        except:
            pass  # Ignore errors during cleanup