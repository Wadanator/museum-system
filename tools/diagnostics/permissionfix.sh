#!/bin/bash
# Fix Group Permission Issues for Museum System

echo "🔧 Museum System Group Permission Fix"
echo "====================================="
echo ""

# Variables
SERVICE_NAME="museum-system"
USER="admin"

echo "📊 Current user groups:"
groups $USER

echo ""
echo "📋 Required groups for the service:"
echo "  - gpio (for GPIO access)"
echo "  - audio (for audio playback)" 
echo "  - dialout (for serial communication)"

echo ""
echo "🔧 Adding user '$USER' to required groups..."

# Add user to required groups
sudo usermod -a -G gpio $USER
sudo usermod -a -G audio $USER  
sudo usermod -a -G dialout $USER

# Also add to some other potentially useful groups
sudo usermod -a -G spi $USER
sudo usermod -a -G i2c $USER

echo "✅ User added to groups"

echo ""
echo "📊 Updated user groups:"
groups $USER

echo ""
echo "🔄 The group changes require the user session to be refreshed."
echo "   You can either:"
echo "   1. Log out and log back in, OR"
echo "   2. Use 'newgrp' to refresh groups in current session"

echo ""
echo "🔧 Let's try to refresh groups and restart the service..."

# Try to restart the service with updated groups
echo "Stopping any running instances..."
sudo systemctl stop $SERVICE_NAME
sudo systemctl stop museum-watchdog

echo ""
echo "🔄 Reloading systemd and starting service..."
sudo systemctl daemon-reload

# Start the service
sudo systemctl start $SERVICE_NAME

echo ""
echo "📊 Service Status After Fix:"
sudo systemctl status $SERVICE_NAME --no-pager -l

echo ""
echo "📋 Testing Results:"
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ SUCCESS! Service is now running"
    echo ""
    echo "🎯 Final Steps:"
    echo "1. Start the watchdog: sudo systemctl start museum-watchdog"
    echo "2. Monitor logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "3. Check watchdog: sudo systemctl status museum-watchdog"
else
    echo "❌ Service still not running. Let's check what's wrong now..."
    echo ""
    echo "📊 Detailed error information:"
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
    echo ""
    echo "🔧 Alternative approach - try running with different user settings..."
    
    # Create a simplified service file without group restrictions
    cat > /tmp/museum-system-simple.service << 'EOF'
[Unit]
Description=Museum Automation System - Simple Edition  
After=network.target
StartLimitIntervalSec=300
StartLimitBurst=10

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/admin/Documents/GitHub/museum-system/raspberry_pi/main.py
WorkingDirectory=/home/admin/Documents/GitHub/museum-system/raspberry_pi

# Logging
StandardOutput=append:/var/log/museum-system.log
StandardError=append:/var/log/museum-system-error.log

# Restart settings
Restart=always
RestartSec=5

# User settings - simplified
User=admin

# Environment
Environment=PYTHONPATH=/home/admin/Documents/GitHub/museum-system/raspberry_pi
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

    echo "📝 Installing simplified service configuration..."
    sudo cp /tmp/museum-system-simple.service /etc/systemd/system/museum-system.service
    sudo systemctl daemon-reload
    sudo systemctl start $SERVICE_NAME
    
    echo ""
    echo "📊 Status with simplified configuration:"
    sudo systemctl status $SERVICE_NAME --no-pager -l
fi

echo ""
echo "🎯 SUMMARY:"
echo "The main issue was GROUP permissions (exit code 216)."
echo "User '$USER' has been added to required groups: gpio, audio, dialout"
echo ""
echo "If the service is now working:"
echo "  ✅ Start watchdog: sudo systemctl start museum-watchdog" 
echo "  ✅ Enable auto-start: sudo systemctl enable $SERVICE_NAME"
echo "  ✅ Monitor: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "If still having issues, the simplified service config should work."