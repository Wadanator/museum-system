#!/bin/bash
# Setup Script for Museum System Auto-Start on New Raspberry Pi

echo "🏛️ Setting up Museum System Auto-Start"
echo "===================================="

# Variables
SERVICE_NAME="museum-system"
WATCHDOG_NAME="museum-watchdog"
PROJECT_DIR="/home/admin/Documents/GitHub/museum-system"
SERVICE_FILE="$PROJECT_DIR/raspberry_pi/service/museum_service.service"
WATCHDOG_SERVICE_FILE="$PROJECT_DIR/raspberry_pi/service/museum-watchdog.service"
SYSTEM_SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
SYSTEM_WATCHDOG_FILE="/etc/systemd/system/$WATCHDOG_NAME.service"
WATCHDOG_SCRIPT="$PROJECT_DIR/raspberry_pi/watchdog.py"

# Check if project directory and required files exist
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Project directory not found: $PROJECT_DIR"
    exit 1
fi

if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

if [ ! -f "$WATCHDOG_SERVICE_FILE" ]; then
    echo "❌ Watchdog service file not found: $WATCHDOG_SERVICE_FILE"
    exit 1
fi

if [ ! -f "$WATCHDOG_SCRIPT" ]; then
    echo "❌ Watchdog script not found: $WATCHDOG_SCRIPT"
    exit 1
fi

# Install services
echo "📋 Installing services..."
sudo cp "$SERVICE_FILE" "$SYSTEM_SERVICE_FILE"
sudo cp "$WATCHDOG_SERVICE_FILE" "$SYSTEM_WATCHDOG_FILE"

# Set proper permissions
sudo chmod 644 "$SYSTEM_SERVICE_FILE"
sudo chmod 644 "$SYSTEM_WATCHDOG_FILE"
sudo chmod +x "$WATCHDOG_SCRIPT"
sudo chmod +x "$PROJECT_DIR/raspberry_pi/main.py"

# Enable services to run in background on boot
echo "🔄 Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME.service"
sudo systemctl enable "$WATCHDOG_NAME.service"

echo ""
echo "✅ Museum System Setup Complete!"
echo ""
echo "🛡️ Features:"
echo "  ✅ Both museum-system and watchdog services start on boot"
echo "  ✅ Automatic restarts on failure"
echo "  ✅ Memory and CPU limits (per existing service files)"
echo "  ✅ Uses existing application logging"
echo ""
echo "📋 Commands:"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    tail -f ~/Documents/GitHub/museum-system/logs/museum.log"
echo "  Watchdog Status: sudo systemctl status $WATCHDOG_NAME"
echo "  Watchdog Logs:   tail -f ~/Documents/GitHub/museum-system/logs/watchdog-info.log"
echo ""
echo "🚀 To start now:"
echo "  sudo systemctl start $SERVICE_NAME"
echo "  sudo systemctl start $WATCHDOG_NAME"