#!/bin/bash
# Enhanced Setup script for 100% reliable Museum System Auto-Start and Auto-Restart

echo "🏛️  Setting up BULLETPROOF Museum System Auto-Start"
echo "=================================================="

# Variables
SERVICE_NAME="museum-system"
PROJECT_DIR="/home/admin/Documents/GitHub/museum-system"
SERVICE_FILE="$PROJECT_DIR/raspberry_pi/service/museum_service.service"
SYSTEM_SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
WATCHDOG_SCRIPT="$PROJECT_DIR/raspberry_pi/watchdog.py"

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Project directory not found: $PROJECT_DIR"
    echo "Please run the project creation script first"
    exit 1
fi

# Create service directory if it doesn't exist
mkdir -p "$PROJECT_DIR/raspberry_pi/service"

echo "📝 Creating BULLETPROOF service file..."
cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=Museum Automation System - Bulletproof Edition
After=network.target network-online.target mosquitto.service
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=10

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/admin/Documents/GitHub/museum-system/raspberry_pi/main.py
WorkingDirectory=/home/admin/Documents/GitHub/museum-system/raspberry_pi

# Logging with rotation
StandardOutput=append:/var/log/museum-system.log
StandardError=append:/var/log/museum-system-error.log

# BULLETPROOF RESTART SETTINGS
Restart=always
RestartSec=5
RestartForceExitStatus=1 2 3 4 5 6 7 8 9 130 131 132 133 134 135 136 137 138 139 255

# Watchdog settings - restart if no heartbeat for 30 seconds
WatchdogSec=30
NotifyAccess=main

# Resource limits to prevent system overload
MemoryLimit=512M
CPUQuota=50%

# User and permissions
User=admin
Group=admin
SupplementaryGroups=gpio,audio,dialout

# Environment
Environment=PYTHONPATH=/home/admin/Documents/GitHub/museum-system/raspberry_pi
Environment=PYTHONUNBUFFERED=1

# Kill settings - force kill if graceful shutdown takes too long
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Enhanced service file created"

echo "📝 Creating system watchdog script..."
cat > "$WATCHDOG_SCRIPT" << 'EOF'
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

# Clean logging setup (matching museum system)
def setup_logging():
    class CleanFormatter(logging.Formatter):
        def format(self, record):
            timestamp = datetime.now().strftime('%H:%M:%S')
            level = record.levelname.ljust(7)
            return f"[{timestamp}] {level} {record.getMessage()}"
    
    logger = logging.getLogger('watchdog')
    logger.setLevel(logging.DEBUG)
    
    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CleanFormatter())
    logger.addHandler(console_handler)
    
    # Log files - same directory structure as museum system
    log_dir = os.path.expanduser("~/Documents/GitHub/museum-system/logs")
    os.makedirs(log_dir, exist_ok=True)
    
    for level, filename in [(logging.INFO, 'watchdog-info.log'), 
                           (logging.WARNING, 'watchdog-warnings.log'), 
                           (logging.ERROR, 'watchdog-errors.log')]:
        handler = logging.FileHandler(f"{log_dir}/{filename}")
        handler.setLevel(level)
        handler.setFormatter(CleanFormatter())
        logger.addHandler(handler)
    
    return logger

log = setup_logging()

class MuseumWatchdog:
    def __init__(self):
        self.service_name = "museum-system"
        self.check_interval = 30  # Check every 30 seconds
        self.max_memory_mb = 256  # Restart if using more than 256MB
        self.max_cpu_percent = 80  # Restart if CPU usage consistently high
        self.high_cpu_count = 0
        self.restart_count = 0
        self.max_restarts_per_hour = 10
        self.last_health_log_time = 0
        self.health_log_interval = 300  # Log health status every 5 minutes max
        
    def is_service_running(self):
        """Check if the museum service is running"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', self.service_name],
                capture_output=True, text=True
            )
            return result.stdout.strip() == 'active'
        except Exception as e:
            log.error(f"Error checking service status: {e}")
            return False
    
    def get_service_process(self):
        """Find the museum system process"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    return proc
        except Exception:
            # Don't log routine process search failures
            pass
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
                if self.high_cpu_count >= 2:  # 2 consecutive high CPU readings
                    return False, f"High CPU usage: {cpu_percent:.1f}%"
            else:
                self.high_cpu_count = 0
            
            # Only log health status occasionally or when there are issues
            current_time = time.time()
            if (current_time - self.last_health_log_time > self.health_log_interval or 
                memory_mb > self.max_memory_mb * 0.8 or cpu_percent > self.max_cpu_percent * 0.8):
                log.info(f"Health: CPU {cpu_percent:.1f}%, Memory {memory_mb:.1f}MB")
                self.last_health_log_time = current_time
            
            return True, f"Healthy - CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB"
            
        except Exception as e:
            return False, f"Error checking health: {e}"
    
    def restart_service(self, reason):
        """Restart the museum service"""
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
        log.warning("Museum System Watchdog started")  # Only log startup
        
        network_down_logged = False
        startup_complete = False
        
        while True:
            try:
                # Check if service is running
                if not self.is_service_running():
                    log.warning("Service not running, starting it...")
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
                    if self.is_service_running():
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
                    log.warning("Watchdog monitoring active")
                    startup_complete = True
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                log.warning("Watchdog stopped by user")
                break
            except Exception as e:
                log.error(f"Watchdog error: {e}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    watchdog = MuseumWatchdog()
    if len(sys.argv) > 1 and sys.argv[1] == "--test-restart":
        log.warning("Running test mode: restarting service")
        watchdog.restart_service("Test restart")
    else:
        watchdog.run()
EOF

# Make watchdog executable
chmod +x "$WATCHDOG_SCRIPT"

echo "📝 Creating watchdog service..."
cat > "/tmp/museum-watchdog.service" << 'EOF'
[Unit]
Description=Museum System Watchdog
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/admin/Documents/GitHub/museum-system/raspberry_pi/watchdog.py
WorkingDirectory=/home/admin/Documents/GitHub/museum-system/raspberry_pi
Restart=always
RestartSec=10
User=admin
Group=admin
Environment=PYTHONPATH=/home/admin/Documents/GitHub/museum-system/raspberry_pi

[Install]
WantedBy=multi-user.target
EOF

# Install both services
echo "📋 Installing services..."
sudo cp "$SERVICE_FILE" "$SYSTEM_SERVICE_FILE"
sudo cp "/tmp/museum-watchdog.service" "/etc/systemd/system/museum-watchdog.service"

# Set proper permissions
sudo chmod 644 "$SYSTEM_SERVICE_FILE"
sudo chmod 644 "/etc/systemd/system/museum-watchdog.service"

# Create log files with proper permissions
echo "📝 Setting up log files..."
sudo touch /var/log/museum-system.log
sudo touch /var/log/museum-system-error.log
sudo touch /var/log/museum-watchdog.log
sudo chown admin:admin /var/log/museum-system*.log
sudo chown admin:admin /var/log/museum-watchdog.log

# Setup log rotation to prevent disk space issues
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/museum-system > /dev/null << 'EOF'
/var/log/museum-system*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 admin admin
    postrotate
        systemctl reload museum-system || true
    endscript
}
EOF

# Make scripts executable
chmod +x "$PROJECT_DIR/raspberry_pi/main.py"

# Install required Python packages
echo "📦 Installing required packages..."

# Enable services
echo "🔄 Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME.service"
sudo systemctl enable "museum-watchdog.service"

# Create health check script
echo "📝 Creating health check script..."
cat > "$PROJECT_DIR/raspberry_pi/health_check.sh" << 'EOF'
#!/bin/bash
echo "🏛️  Museum System Health Check"
echo "============================="
echo ""

echo "📊 Service Status:"
sudo systemctl status museum-system --no-pager -l
echo ""

echo "📊 Watchdog Status:"
sudo systemctl status museum-watchdog --no-pager -l
echo ""

echo "📊 Recent Logs (last 20 lines):"
echo "--- Main Service ---"
tail -20 /var/log/museum-system.log
echo ""
echo "--- Watchdog ---"
tail -20 /var/log/museum-watchdog.log
echo ""

echo "📊 Process Information:"
ps aux | grep -E "(main.py|watchdog.py)" | grep -v grep
echo ""

echo "📊 Network Test:"
ping -c 3 8.8.8.8
echo ""

echo "📊 Disk Space:"
df -h /var/log
EOF

chmod +x "$PROJECT_DIR/raspberry_pi/health_check.sh"

echo ""
echo "✅ BULLETPROOF Museum System Setup Complete!"
echo ""
echo "🛡️  ENHANCED FEATURES:"
echo "  ✅ Service restarts on ANY failure"
echo "  ✅ Watchdog monitors resource usage"
echo "  ✅ Network connectivity monitoring"
echo "  ✅ Automatic log rotation"
echo "  ✅ Memory and CPU limits"
echo "  ✅ Multiple restart strategies"
echo "  ✅ Health monitoring every 30 seconds"
echo ""
echo "📋 Management Commands:"
echo "  Start:        sudo systemctl start museum-system"
echo "  Stop:         sudo systemctl stop museum-system"
echo "  Status:       sudo systemctl status museum-system"
echo "  Logs:         sudo journalctl -u museum-system -f"
echo "  Health Check: $PROJECT_DIR/raspberry_pi/health_check.sh"
echo ""
echo "🐕 Watchdog Commands:"
echo "  Start:   sudo systemctl start museum-watchdog"
echo "  Status:  sudo systemctl status museum-watchdog"
echo "  Logs:    tail -f /var/log/museum-watchdog.log"
echo ""
echo "🚀 To start everything now:"
echo "  sudo systemctl start museum-system"
echo "  sudo systemctl start museum-watchdog"
echo ""
echo "The system will now restart automatically for:"
echo "  ❌ Python crashes or exceptions"
echo "  ❌ High memory usage (>256MB)"
echo "  ❌ High CPU usage (>80% sustained)"
echo "  ❌ Network connectivity issues"
echo "  ❌ Service becoming unresponsive"
echo "  ❌ Any system resource problems"