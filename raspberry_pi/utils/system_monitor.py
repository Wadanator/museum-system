#!/usr/bin/env python3

import os
import time
import logging
from utils.logging_setup import get_logger

class SystemMonitor:
    def __init__(self, health_check_interval=60, logger=None):
        self.logger = logger or get_logger('sys_monitor')
        self.health_check_interval = health_check_interval
        self.last_heartbeat = time.time()
        self._hc_count = 0
        self.hc_log_period = 120
    
    def send_ready_notification(self):
        """Send systemd ready notification"""
        try:
            os.system('systemd-notify READY=1')
            return True
        except Exception as e:
            self.logger.warning(f"Systemd notify failed: {e}")
            return False
    
    def perform_health_check(self, mqtt_client=None, connected_to_broker=False):
        try:
            self.last_heartbeat = time.time()
            issues = []
            
            if not connected_to_broker:
                issues.append("MQTT down")
            if not mqtt_client:
                issues.append("MQTT missing")
            
            try:
                import psutil
                mem = psutil.virtual_memory()
                memory_mb = mem.used / 1024 / 1024
                cpu_percent = psutil.cpu_percent(interval=0.2)
                disk_usage = psutil.disk_usage('/')
                disk_percent = (disk_usage.used / disk_usage.total) * 100
                
                if memory_mb > 1024:
                    issues.append(f"High mem ({memory_mb:.1f}MB)")
                elif memory_mb > 900:
                    self.logger.warning(f"Memory usage: {memory_mb:.1f}MB")
                
                if cpu_percent > 45:
                    issues.append(f"High CPU ({cpu_percent:.1f}%)")
                
                if disk_percent > 90:
                    issues.append(f"Low disk ({disk_percent:.1f}% used)")
            except ImportError:
                pass
            except Exception as e:
                self.logger.warning(f"System checks failed: {e}")
            
            if issues:
                self.logger.warning(f"Health: {len(issues)} issues: {', '.join(issues)}")
                return False
            else:
                self._hc_count += 1
                if self._hc_count % self.hc_log_period == 0:
                    self.logger.debug(f"Health #{self._hc_count}: OK")
                return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def log_startup_info(self, room_id, broker_ip, button_pin):
        """Log system startup information"""
        self.logger.info("="*40)
        self.logger.info("Museum System Starting")
        self.logger.info(f"Room: {room_id}")
        self.logger.info(f"MQTT Broker: {broker_ip}")
        self.logger.info(f"Button GPIO: {button_pin}")
        
        # Log system info if available
        try:
            import psutil
            self.logger.info(f"Memory: {psutil.virtual_memory().percent:.1f}% used")
            self.logger.info(f"CPU: {psutil.cpu_percent(interval=0.1):.1f}% used")
        except ImportError:
            self.logger.debug("psutil not available for startup stats")
        
        self.logger.info("="*40)