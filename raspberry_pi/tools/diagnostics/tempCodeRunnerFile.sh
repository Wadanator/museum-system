#!/bin/bash
# Complete Museum System Fix Script
# This script will fix all common issues preventing the museum system from starting

echo "🏛️ Museum System Complete Fix"
echo "============================="
echo ""

# Variables
PROJECT_DIR="/home/admin/Documents/GitHub/museum-system"
RASPBERRY_PI_DIR="$PROJECT_DIR/raspberry_pi"
SERVICE_NAME="museum-system"
WATCHDOG_NAME="museum-watchdog"

# Function to check if command succeeded
check_success() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
    else
        echo "❌ $1 failed"
        return 1
    fi
}

# Step 1: Stop everything and clean up
echo "🛑 Step 1: Stopping all services and cleaning up..."
sudo systemctl stop $SERVICE_NAME 2>/dev/null
sudo systemctl stop $WATCHDOG_NAME 2>/dev/null
sudo systemctl reset-failed $SERVICE_NAME 2>/dev/null
sudo systemctl reset-failed $WATCHDOG_NAME 2>/dev/null
check_success "Stopped and reset services"

# Step 2: Check and fix project structure
echo ""
echo "📁 Step 2: Checking project structure..."
cd "$RASPBERRY_PI_DIR" || {
    echo "❌ Cannot access $RASPBERRY_PI_DIR"
    exit 1
}
check_success "Accessed project directory"

# Make main.py executable
chmod +x main.py
chmod +x watchdog.py
check_success "Made Python files executable"

# Step 3: Install missing Python packages
echo ""
echo "📦 Step 3: Installing Python dependencies..."
pip3 install --user psutil paho-mqtt flask flask-socketio 2>/dev/null
check_success "Installed Python packages"

# Step 4: Fix user permissions
echo ""
echo "👥 Step 4: Fixing user permissions..."
sudo usermod -a -G gpio admin
sudo usermod -a -G audio admin
sudo usermod -a -G dialout admin
sudo usermod -a -G spi admin
sudo usermod -a -G i2c admin
check_success "Added user to required groups"

# Step 5: Create or fix config file
echo ""
echo "⚙️ Step 5: Checking configuration..."
if [ ! -f "config/config.ini" ]; then
    echo "Creating config.ini..."
    mkdir -p config
    cat > config/config.ini << 'EOF'
[mqtt]
broker_ip = 127.0.0.1
broker_port = 1883
room_id = room1
json_file_name = intro.json

[paths]
scenes_dir = scenes
audio_dir = audio
video_dir = videos

[hardware]
button_pin = 27

[system]
health_check_interval = 60
debounce_time = 2.0
main_loop_sleep = 1
scene_processing_sleep = 0.1
web_dashboard_port = 5000
EOF
    check_success "Created config.ini"
else
    check_success "Config file exists"
fi

# Step 6: Test Python execution
echo ""
echo "🐍 Step 6: Testing Python execution..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from utils.config_manager import ConfigManager
    print('✅ ConfigManager import successful')
    config = ConfigManager()
    print('✅ ConfigManager initialization successful')
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
" || {
    echo "❌ Python execution test failed"
    exit 1
}

# Step 7: Create working service file
echo ""
echo "📝 Step 7: Creating optimized service file..."
cat > /tmp/museum-system-working.service << 'EOF'
[Unit]
Description=Museum Automation System
After=network.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
ExecStart=/usr/bin/python3 -u /home/admin/Documents/GitHub/museum-system/raspberry_pi/main.py
WorkingDirectory=/home/admin/Documents/GitHub/museum-system/raspberry_pi
Restart=on-failure
RestartSec=10
User=admin
Group=admin

# Environment
Environment=PYTHONPATH=/home/admin/Documents/GitHub/museum-system/raspberry_pi
Environment=PYTHONUNBUFFERED=1
Environment=HOME=/home/admin

# Logging
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryLimit=1024M

[Install]
WantedBy=multi-user.target
EOF

# Install the service
sudo cp /tmp/museum-system-working.service /etc/systemd/system/$SERVICE_NAME.service
sudo systemctl daemon-reload
check_success "Installed working service file"

# Step 8: Create simplified watchdog service
echo ""
echo "🛡️ Step 8: Creating simplified watchdog service..."
cat > /tmp/museum-watchdog-simple.service << 'EOF'
[Unit]
Description=Museum System Watchdog
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=/usr/bin/python3 -u /home/admin/Documents/GitHub/museum-system/raspberry_pi/watchdog.py
WorkingDirectory=/home/admin/Documents/GitHub/museum-system/raspberry_pi
Restart=always
RestartSec=30
User=admin
Group=admin

# Environment
Environment=PYTHONPATH=/home/admin/Documents/GitHub/museum-system/raspberry_pi
Environment=PYTHONUNBUFFERED=1
Environment=HOME=/home/admin

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/museum-watchdog-simple.service /etc/systemd/system/$WATCHDOG_NAME.service
sudo systemctl daemon-reload
check_success "Installed simplified watchdog service"

# Step 9: Test the service
echo ""
echo "🚀 Step 9: Testing service startup..."
sudo systemctl start $SERVICE_NAME
sleep 5

if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ SUCCESS! Museum system is running!"
    echo ""
    echo "📊 Service Status:"
    sudo systemctl status $SERVICE_NAME --no-pager -l
    
    echo ""
    echo "🛡️ Starting watchdog..."
    sudo systemctl start $WATCHDOG_NAME
    
    if sudo systemctl is-active --quiet $WATCHDOG_NAME; then
        echo "✅ Watchdog is also running!"
    else
        echo "⚠️ Watchdog failed to start, but main service is working"
    fi
    
else
    echo "❌ Service still not starting. Checking logs..."
    echo ""
    echo "📋 Recent logs:"
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
    echo ""
    echo "🔧 Trying manual execution for debugging..."
    timeout 15 python3 main.py
fi

# Step 10: Enable auto-start
echo ""
echo "🔄 Step 10: Enabling auto-start..."
sudo systemctl enable $SERVICE_NAME
check_success "Enabled museum-system auto-start"

sudo systemctl enable $WATCHDOG_NAME 2>/dev/null
check_success "Enabled watchdog auto-start"

echo ""
echo "🎯 SUMMARY:"
echo "==========="
echo ""
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Museum System is RUNNING!"
    echo "✅ Auto-start is ENABLED!"
    echo ""
    echo "📋 Commands to know:"
    echo "- View status: sudo systemctl status $SERVICE_NAME"
    echo "- View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "- Stop service: sudo systemctl stop $SERVICE_NAME"
    echo "- Start service: sudo systemctl start $SERVICE_NAME"
    echo "- Application logs: tail -f logs/museum.log"
    echo ""
    echo "🎊 Your museum system is ready to go!"
else
    echo "❌ Museum System is NOT running"
    echo ""
    echo "🔧 Manual debugging steps:"
    echo "1. Check logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "2. Try manual run: cd $RASPBERRY_PI_DIR && python3 main.py"
    echo "3. Check permissions: ls -la main.py"
    echo "4. Check Python: python3 --version"
    echo ""
    echo "The service files have been simplified and should work."
    echo "If still having issues, there might be a deeper Python/dependency problem."
fi

echo ""
echo "🏁 Fix script completed!"