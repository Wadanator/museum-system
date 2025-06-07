#!/usr/bin/env python3
"""
System Watchdog for Museum System
Monitors the main process and restarts it if needed
"""

import os
import sys
import time
import subprocess
import psutil
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - WATCHDOG - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/museum-watchdog.log'),
        logging.StreamHandler()
    ]
)

class MuseumWatchdog:
    def __init__(self):
        self.service_name = "museum-system"
        self.check_interval = 60  # Check every 30 seconds
        self.max_memory_mb = 300  # Restart if using more than 256MB
        self.max_cpu_percent = 80  # Restart if CPU usage consistently high
        self.high_cpu_count = 0
        self.restart_count = 0
        self.max_restarts_per_hour = 10
        
    def is_service_running(self):
        """Check if the museum service is running"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', self.service_name],
                capture_output=True, text=True
            )
            return result.stdout.strip() == 'active'
        except Exception as e:
            logging.error(f"Error checking service status: {e}")
            return False
    
    def get_service_process(self):
        """Find the museum system process"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    return proc
        except Exception as e:
            logging.error(f"Error finding process: {e}")
        return None
    
    def check_process_health(self):
        """Check if the process is consuming too many resources"""
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
                if self.high_cpu_count >= 3:  # 3 consecutive high CPU readings
                    return False, f"High CPU usage: {cpu_percent:.1f}%"
            else:
                self.high_cpu_count = 0
            
            return True, f"Healthy - CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB"
            
        except Exception as e:
            return False, f"Error checking health: {e}"
    
    def restart_service(self, reason):
        """Restart the museum service"""
        self.restart_count += 1
        logging.warning(f"Restarting service (#{self.restart_count}) - Reason: {reason}")
        
        try:
            # Stop the service
            subprocess.run(['sudo', 'systemctl', 'stop', self.service_name], check=True)
            time.sleep(5)
            
            # Start the service
            subprocess.run(['sudo', 'systemctl', 'start', self.service_name], check=True)
            logging.info("Service restarted successfully")
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to restart service: {e}")
    
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
        logging.info("Museum System Watchdog started")
        
        while True:
            try:
                # Check if service is running
                if not self.is_service_running():
                    logging.warning("Service not running, starting it...")
                    subprocess.run(['sudo', 'systemctl', 'stop', self.service_name])
                    subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
                    subprocess.run(['sudo', 'systemctl', 'start', self.service_name])
                    time.sleep(10)
                    continue
                
                # Check process health
                healthy, status = self.check_process_health()
                logging.info(f"Health check: {status}")
                
                if not healthy and "Process not found" not in status:
                    self.restart_service(status)
                    time.sleep(30)  # Wait longer after restart
                    continue
                
                # Check network connectivity periodically
                if not self.check_network_connectivity():
                    logging.warning("Network connectivity issue detected")
                
                # Reset restart count every hour
                if self.restart_count > 0 and int(time.time()) % 3600 == 0:
                    logging.info(f"Hourly reset - Had {self.restart_count} restarts")
                    self.restart_count = 0
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logging.info("Watchdog stopped by user")
                break
            except Exception as e:
                logging.error(f"Watchdog error: {e}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    watchdog = MuseumWatchdog()
    if len(sys.argv) > 1 and sys.argv[1] == "--test-restart":
        logging.info("Running test mode: restarting service")
        watchdog.restart_service("Test restart")
    else:
        watchdog.run()