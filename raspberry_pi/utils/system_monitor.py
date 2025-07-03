#!/usr/bin/env python3

import os
import time
import logging

class SystemMonitor:
    def __init__(self, health_check_interval=30, logger=None):
        self.log = logger or logging.getLogger(__name__)
        self.health_check_interval = health_check_interval
        self.last_heartbeat = time.time()
        self._hc_count = 0
        self.hc_log_period = 120
    
    def send_ready_notification(self):
        """Send systemd ready notification"""
        try:
            os.system('systemd-notify READY=1')
            self.log.info("Systemd READY sent")
            return True
        except Exception as e:
            self.log.warning(f"Systemd notify failed: {e}")
            return False
    
    def perform_health_check(self, mqtt_client=None, connected_to_broker=False):
        """Perform comprehensive health check"""
        try:
            self.last_heartbeat = time.time()
            issues = []
            
            # MQTT health checks
            if not connected_to_broker:
                issues.append("MQTT down")
            if not mqtt_client:
                issues.append("MQTT missing")
            
            # Memory check
            try:
                import psutil
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 90:
                    issues.append(f"High mem ({memory_percent:.1f}%)")
                elif memory_percent > 80:
                    # Log warning but don't consider it an issue yet
                    self.log.warning(f"Memory usage: {memory_percent:.1f}%")
            except ImportError:
                # psutil not available, skip memory check
                pass
            except Exception as e:
                self.log.warning(f"Memory check failed: {e}")
            
            # CPU check
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=0.1)
                if cpu_percent > 95:
                    issues.append(f"High CPU ({cpu_percent:.1f}%)")
            except ImportError:
                pass
            except Exception as e:
                self.log.warning(f"CPU check failed: {e}")
            
            # Disk space check
            try:
                import psutil
                disk_usage = psutil.disk_usage('/')
                disk_percent = (disk_usage.used / disk_usage.total) * 100
                if disk_percent > 90:
                    issues.append(f"Low disk ({disk_percent:.1f}% used)")
            except ImportError:
                pass
            except Exception as e:
                self.log.warning(f"Disk check failed: {e}")
            
            # Report results
            if issues:
                self.log.warning(f"Health: {len(issues)} issues: {', '.join(issues)}")
                return False
            else:
                self._hc_count += 1
                # Log every 120th successful health check to avoid spam
                if self._hc_count % self.hc_log_period == 0:
                    self.log.info(f"Health #{self._hc_count}: OK")
                return True
                
        except Exception as e:
            self.log.error(f"Health check failed: {e}")
            return False
    
    def get_system_stats(self):
        """Get current system statistics"""
        stats = {
            'timestamp': time.time(),
            'uptime': time.time() - self.last_heartbeat
        }
        
        try:
            import psutil
            stats.update({
                'memory_percent': psutil.virtual_memory().percent,
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'disk_percent': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            })
        except ImportError:
            self.log.debug("psutil not available for system stats")
        except Exception as e:
            self.log.warning(f"Failed to get system stats: {e}")
        
        return stats
    
    def is_healthy(self, mqtt_client=None, connected_to_broker=False):
        """Quick health check without logging"""
        try:
            issues = 0
            
            if not connected_to_broker or not mqtt_client:
                issues += 1
            
            try:
                import psutil
                if psutil.virtual_memory().percent > 90:
                    issues += 1
                if psutil.cpu_percent(interval=0.1) > 95:
                    issues += 1
            except ImportError:
                pass
            
            return issues == 0
            
        except Exception:
            return False
    
    def log_startup_info(self, room_id, broker_ip, button_pin):
        """Log system startup information"""
        self.log.info("="*40)
        self.log.info("Museum System Starting")
        self.log.info(f"Room: {room_id}")
        self.log.info(f"MQTT Broker: {broker_ip}")
        self.log.info(f"Button GPIO: {button_pin}")
        
        # Log system info if available
        try:
            import psutil
            self.log.info(f"Memory: {psutil.virtual_memory().percent:.1f}% used")
            self.log.info(f"CPU: {psutil.cpu_percent(interval=0.1):.1f}% used")
        except ImportError:
            self.log.debug("psutil not available for startup stats")
        
        self.log.info("="*40)