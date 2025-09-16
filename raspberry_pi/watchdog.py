#!/usr/bin/env python3
"""
System Watchdog for Museum System
Monitors the main process and restarts it if needed
Storage-efficient logging - only logs when action is needed
Enhanced logic to avoid unnecessary restarts due to audio issues
"""

import os
import sys
import time
import subprocess
import psutil
import logging
from datetime import datetime

# Add current directory to Python path (same as main.py)
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Initialize configuration and logging (consistent with main.py)
from utils.config_manager import ConfigManager
from utils.logging_setup import setup_logging_from_config, get_logger

# Initialize config manager
config_manager = ConfigManager()

# Get logging configuration and setup logging (consistent with main.py)
logging_config = config_manager.get_logging_config()
log = setup_logging_from_config(logging_config)

# Use the main logger with a watchdog prefix instead of separate logger
# This ensures all watchdog logs go to the same files as the main application
watchdog_log = get_logger('watchdog')  # Use the main logger directly

class MuseumWatchdog:
    def __init__(self):
        self.service_name = "museum-system"  # Match service file name
        self.check_interval = 60  # Check every 60 seconds
        self.max_memory_mb = 1024  # Match service MemoryLimit
        self.max_cpu_percent = 85  # Increased threshold - audio errors can cause temporary spikes
        self.high_cpu_count = 0
        self.cpu_spike_tolerance = 3  # Allow 3 consecutive high CPU readings before restart
        self.restart_count = 0
        self.max_restarts_per_hour = 5  # Reduced from 10 to prevent excessive restarts
        self.last_health_log_time = 0
        self.health_log_interval = 3600  # Log health status every hour
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.audio_error_restart_delay = 300  # Wait 5 minutes before restarting for audio errors
        self.last_audio_error_time = 0
        
    def is_service_running(self):
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', self.service_name],
                capture_output=True, text=True, timeout=10
            )
            is_active = result.stdout.strip() == 'active'
            watchdog_log.debug(f"Service check: {self.service_name} = {result.stdout.strip()}")
            return is_active
        except Exception as e:
            watchdog_log.error(f"Error checking service status: {e}")
            return False
    
    def get_service_process(self):
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    watchdog_log.debug(f"Found process: PID {proc.pid}")
                    return proc
        except Exception as e:
            watchdog_log.debug(f"Process search error: {e}")
            pass
        return None
    
    def check_recent_logs_for_audio_errors(self):
        """Check recent logs for audio initialization errors"""
        try:
            # Look for recent audio errors in logs
            log_files = [
                "/home/admin/Documents/GitHub/museum-system/raspberry_pi/logs/museum.log",
                "/var/log/museum-system.log"  # If logs are elsewhere
            ]
            
            current_time = time.time()
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        # Check last 50 lines for audio errors
                        result = subprocess.run(
                            ['tail', '-n', '50', log_file],
                            capture_output=True, text=True, timeout=5
                        )
                        
                        recent_lines = result.stdout
                        audio_error_patterns = [
                            "Error initializing pygame mixer",
                            "ALSA: Couldn't open audio device",
                            "Audio initialization failed",
                            "Audio permanently disabled"
                        ]
                        
                        for pattern in audio_error_patterns:
                            if pattern in recent_lines:
                                # Extract timestamp if possible and check if recent
                                lines_with_pattern = [line for line in recent_lines.split('\n') if pattern in line]
                                if lines_with_pattern:
                                    self.last_audio_error_time = current_time
                                    return True
                    except Exception:
                        continue
            return False
        except Exception:
            return False
    
    def check_process_health(self):
        proc = self.get_service_process()
        if not proc:
            self.consecutive_failures += 1
            return False, "Process not found"
        
        try:
            # Reset consecutive failures if process is found
            self.consecutive_failures = 0
            
            # Check memory usage - align with SystemMonitor
            memory_mb = proc.memory_info().rss / 1024 / 1024
            if memory_mb > self.max_memory_mb:
                return False, f"High memory usage: {memory_mb:.1f}MB (limit: {self.max_memory_mb}MB)"
            
            # Check CPU usage with enhanced logic
            cpu_percent = proc.cpu_percent(interval=1)
            
            if cpu_percent > self.max_cpu_percent:
                self.high_cpu_count += 1
                
                # Check if this might be audio-related
                is_audio_error_period = (time.time() - self.last_audio_error_time) < 120  # Within 2 minutes of audio error
                
                if self.high_cpu_count >= self.cpu_spike_tolerance:
                    if is_audio_error_period or self.check_recent_logs_for_audio_errors():
                        # Audio-related high CPU - be more tolerant
                        if (time.time() - self.last_audio_error_time) < self.audio_error_restart_delay:
                            watchdog_log.warning(f"High CPU ({cpu_percent:.1f}%) likely due to audio issues - delaying restart")
                            return True, f"High CPU (audio-related): {cpu_percent:.1f}% - monitoring"
                        else:
                            return False, f"Persistent high CPU after audio errors: {cpu_percent:.1f}%"
                    else:
                        return False, f"High CPU usage: {cpu_percent:.1f}% (consecutive: {self.high_cpu_count})"
            else:
                self.high_cpu_count = 0
            
            healthy = True
            status = f"Healthy - CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB"
            
            # Log health issues but be smarter about it
            current_time = time.time()
            is_concerning = (memory_mb > self.max_memory_mb * 0.9 or 
                           cpu_percent > self.max_cpu_percent * 0.8 or 
                           not healthy)
            
            if is_concerning and (current_time - self.last_health_log_time > 60):
                log_level = "WARNING" if healthy else "ERROR"
                watchdog_log.warning(f"Health check issue: CPU {cpu_percent:.1f}%, Memory {memory_mb:.1f}MB")
                self.last_health_log_time = current_time
            
            return healthy, status
            
        except Exception as e:
            return False, f"Error checking health: {e}"
    
    def should_restart_service(self, reason):
        """Enhanced logic to determine if service should be restarted"""
        current_time = time.time()
        
        # Don't restart too frequently
        if self.restart_count >= self.max_restarts_per_hour:
            watchdog_log.error(f"Restart limit reached ({self.max_restarts_per_hour}/hour) - manual intervention required")
            return False
        
        # Be more conservative with process-not-found restarts
        if "Process not found" in reason:
            if self.consecutive_failures < self.max_consecutive_failures:
                watchdog_log.warning(f"Process not found ({self.consecutive_failures}/{self.max_consecutive_failures}) - monitoring...")
                return False
        
        # Check for audio-related issues
        if "audio" in reason.lower() or self.check_recent_logs_for_audio_errors():
            if (current_time - self.last_audio_error_time) < self.audio_error_restart_delay:
                watchdog_log.warning(f"Audio-related issue detected - waiting {self.audio_error_restart_delay}s before restart")
                return False
        
        return True
    
    def restart_service(self, reason):
        if not self.should_restart_service(reason):
            return False
            
        self.restart_count += 1
        watchdog_log.warning(f"Restarting service (#{self.restart_count}) - Reason: {reason}")
        
        try:
            # Stop the service gracefully first
            watchdog_log.info("Attempting graceful service stop...")
            subprocess.run(['sudo', 'systemctl', 'stop', self.service_name], 
                         capture_output=True, check=False, timeout=30)
            time.sleep(10)  # Give more time for cleanup
            
            # Force kill if still running
            proc = self.get_service_process()
            if proc:
                watchdog_log.warning("Process still running, forcing termination...")
                try:
                    proc.terminate()
                    proc.wait(timeout=10)
                except:
                    proc.kill()
                time.sleep(5)
            
            # Reload daemon and start service
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], 
                         capture_output=True, check=False, timeout=10)
            time.sleep(2)
            
            subprocess.run(['sudo', 'systemctl', 'start', self.service_name], 
                         capture_output=True, check=True, timeout=30)
            watchdog_log.warning("Service restarted successfully")
            
            # Reset some counters after successful restart
            self.high_cpu_count = 0
            self.consecutive_failures = 0
            
            return True
            
        except subprocess.CalledProcessError as e:
            watchdog_log.error(f"Failed to restart service: {e}")
            return False
        except Exception as e:
            watchdog_log.error(f"Unexpected error during restart: {e}")
            return False
    
    def check_web_interface(self):
        """Check if web interface is responding"""
        try:
            import requests
            response = requests.get("http://localhost:5000", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def check_network_connectivity(self):
        """Check if network is available"""
        try:
            result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                  capture_output=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def run(self):
        """Main watchdog loop with enhanced monitoring"""
        watchdog_log.info("Museum System Watchdog started - entering enhanced monitoring loop")
        
        network_down_logged = False
        startup_complete = False
        loop_count = 0
        last_restart_count_reset = time.time()
        
        while True:
            try:
                loop_count += 1
                current_time = time.time()
                
                # Reset restart count every hour
                if current_time - last_restart_count_reset > 3600:
                    if self.restart_count > 0:
                        watchdog_log.info(f"Hourly reset - Had {self.restart_count} restarts in last hour")
                    self.restart_count = 0
                    last_restart_count_reset = current_time
                
                # Check if service is running
                service_running = self.is_service_running()
                if not service_running:
                    watchdog_log.warning("Service not running, attempting to start...")
                    try:
                        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], 
                                     capture_output=True, timeout=10)
                        subprocess.run(['sudo', 'systemctl', 'start', self.service_name], 
                                     capture_output=True, check=True, timeout=30)
                        watchdog_log.info("Service started successfully")
                        time.sleep(15)  # Give more time for startup
                        continue
                    except Exception as e:
                        watchdog_log.error(f"Failed to start service: {e}")
                        time.sleep(30)
                        continue
                
                # Check process health
                healthy, status = self.check_process_health()
                
                # Only restart if there's an actual problem and restart conditions are met
                if not healthy:
                    if "Process not found" in status and service_running:
                        # Service claims to be running but no process found
                        watchdog_log.warning("Service running but process not accessible")
                    elif self.should_restart_service(status):
                        if self.restart_service(status):
                            time.sleep(30)  # Wait longer after restart
                        else:
                            watchdog_log.warning("Restart conditions not met, continuing monitoring")
                        continue
                
                # Check network connectivity periodically
                if loop_count % 5 == 0:  # Every 5 minutes
                    network_ok = self.check_network_connectivity()
                    if not network_ok and not network_down_logged:
                        watchdog_log.warning("Network connectivity lost")
                        network_down_logged = True
                    elif network_ok and network_down_logged:
                        watchdog_log.info("Network connectivity restored")
                        network_down_logged = False
                
                # Check web interface occasionally
                if loop_count % 10 == 0:  # Every 10 minutes
                    web_ok = self.check_web_interface()
                    if not web_ok:
                        watchdog_log.debug("Web interface not responding (may be normal)")
                
                # Log successful startup completion once
                if not startup_complete and service_running and healthy:
                    watchdog_log.info("Watchdog monitoring active - all systems nominal")
                    startup_complete = True
                
                # Periodic status log (less frequent)
                if loop_count % 60 == 0:  # Every hour
                    watchdog_log.info(f"System status: Healthy={healthy}, Restarts={self.restart_count}, Uptime={loop_count} minutes")
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                watchdog_log.warning("Watchdog stopped by user")
                break
            except Exception as e:
                watchdog_log.error(f"Watchdog error: {e}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    # Additional startup logging
    watchdog_log.info("=== WATCHDOG PROCESS STARTING ===")
    watchdog = MuseumWatchdog()
    if len(sys.argv) > 1 and sys.argv[1] == "--test-restart":
        watchdog_log.warning("Running test mode: restarting service")
        watchdog.restart_service("Test restart")
    elif len(sys.argv) > 1 and sys.argv[1] == "--status":
        # Status check mode
        service_running = watchdog.is_service_running()
        proc = watchdog.get_service_process()
        print(f"Service active: {service_running}")
        print(f"Process found: {proc is not None}")
        if proc:
            try:
                memory_mb = proc.memory_info().rss / 1024 / 1024
                cpu_percent = proc.cpu_percent(interval=1)
                print(f"Memory: {memory_mb:.1f}MB")
                print(f"CPU: {cpu_percent:.1f}%")
            except:
                print("Could not get process stats")
    else:
        watchdog.run()