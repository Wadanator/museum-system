#!/usr/bin/env python3
"""
System Watchdog for Museum System
Monitors the main process and restarts it if needed
Storage-efficient logging - only logs when action is needed
"""

import os
import sys
import time
import subprocess
import psutil
import logging
from datetime import datetime

from utils.logging_setup import setup_logging

log = setup_logging(log_level=logging.INFO)

class MuseumWatchdog:
    def __init__(self):
        self.service_name = "museum-system"
        self.check_interval = 30  # Check every 30 seconds
        self.max_memory_mb = 512  # Restart if using more than 512MB
        self.max_cpu_percent = 45  # Restart if CPU usage consistently high
        self.high_cpu_count = 0
        self.restart_count = 0
        self.max_restarts_per_hour = 10
        self.last_health_log_time = 0
        self.health_log_interval = 3600  # Log health status every hour
        
        # Log initialization
        log.warning("MuseumWatchdog initialized - monitoring will begin shortly")
        
    def is_service_running(self):
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', self.service_name],
                capture_output=True, text=True
            )
            is_active = result.stdout.strip() == 'active'
            # Add debug logging
            log.debug(f"Service check: {self.service_name} = {result.stdout.strip()}")
            return is_active
        except Exception as e:
            log.error(f"Error checking service status: {e}")
            return False
    
    def get_service_process(self):
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    log.debug(f"Found process: PID {proc.pid}")
                    return proc
        except Exception as e:
            log.debug(f"Process search error: {e}")
            pass
        return None
    
    def check_process_health(self):
        proc = self.get_service_process()
        if not proc:
            return False, "Process not found"
        
        try:
            # Check memory usage
            memory_mb = proc.memory_info().rss / 1024 / 1024
            if memory_mb > self.max_memory_mb:
                return False, f"High memory usage: {memory_mb:.1f}MB"
            
            # Check CPU usage
            cpu_percent = proc.cpu_percent(interval=1)
            if cpu_percent > self.max_cpu_percent:
                self.high_cpu_count += 1
                if self.high_cpu_count >= 2:  # 2 consecutive high CPU readings
                    return False, f"High CPU usage: {cpu_percent:.1f}%"
            else:
                self.high_cpu_count = 0
            
            # Log health status more frequently for debugging
            current_time = time.time()
            if (current_time - self.last_health_log_time > self.health_log_interval or 
                memory_mb > self.max_memory_mb * 0.8 or cpu_percent > self.max_cpu_percent * 0.8):
                log.debug(f"Health check: CPU {cpu_percent:.1f}%, Memory {memory_mb:.1f}MB")
                self.last_health_log_time = current_time
            
            return True, f"Healthy - CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB"
            
        except Exception as e:
            return False, f"Error checking health: {e}"
    
    def restart_service(self, reason):
        self.restart_count += 1
        log.warning(f"Restarting service (#{self.restart_count}) - Reason: {reason}")
        
        try:
            # Stop the service
            subprocess.run(['sudo', 'systemctl', 'stop', self.service_name], 
                         capture_output=True, check=True)
            time.sleep(5)
            
            # Start the service
            subprocess.run(['sudo', 'systemctl', 'start', self.service_name], 
                         capture_output=True, check=True)
            log.warning("Service restarted successfully")
            
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to restart service: {e}")
    
    def check_network_connectivity(self):
        """Check if network is available"""
        try:
            result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                  capture_output=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def run(self):
        """Main watchdog loop"""
        log.warning("Museum System Watchdog started - entering main monitoring loop")
        
        network_down_logged = False
        startup_complete = False
        loop_count = 0
        
        while True:
            try:
                loop_count += 1
                
                # Check if service is running
                service_running = self.is_service_running()
                if not service_running:
                    log.warning("Service not running, attempting to start...")
                    subprocess.run(['sudo', 'systemctl', 'stop', self.service_name], 
                                 capture_output=True)
                    subprocess.run(['sudo', 'systemctl', 'daemon-reload'], 
                                 capture_output=True)
                    subprocess.run(['sudo', 'systemctl', 'start', self.service_name], 
                                 capture_output=True)
                    time.sleep(10)
                    continue
                
                # Check process health
                healthy, status = self.check_process_health()
                
                # Only restart if there's an actual problem (not just "process not found")
                if not healthy and "Process not found" not in status:
                    self.restart_service(status)
                    time.sleep(30)  # Wait longer after restart
                    continue
                elif not healthy and "Process not found" in status:
                    # Process not found - only log if service claims to be running
                    if service_running:
                        log.warning("Service running but process not found")
                
                # Check network connectivity periodically (only log when it goes down/up)
                network_ok = self.check_network_connectivity()
                if not network_ok and not network_down_logged:
                    log.warning("Network connectivity lost")
                    network_down_logged = True
                elif network_ok and network_down_logged:
                    log.warning("Network connectivity restored")
                    network_down_logged = False
                
                # Reset restart count every hour (only log if there were restarts)
                if self.restart_count > 0 and int(time.time()) % 3600 == 0:
                    log.warning(f"Hourly reset - Had {self.restart_count} restarts this hour")
                    self.restart_count = 0
                
                # Log successful startup completion once
                if not startup_complete:
                    log.warning("Watchdog monitoring active - all systems nominal")
                    startup_complete = True
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                log.warning("Watchdog stopped by user")
                break
            except Exception as e:
                log.error(f"Watchdog error: {e}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    # Additional startup logging
    print(f"Watchdog starting at {datetime.now()}")
    log.warning("=== WATCHDOG PROCESS STARTING ===")
    
    watchdog = MuseumWatchdog()
    if len(sys.argv) > 1 and sys.argv[1] == "--test-restart":
        log.warning("Running test mode: restarting service")
        watchdog.restart_service("Test restart")
    else:
        watchdog.run()