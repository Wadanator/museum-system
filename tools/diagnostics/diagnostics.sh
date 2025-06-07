#!/bin/bash
# Museum System Diagnostic and Fix Script

echo "🔍 Museum System Diagnostic Tool"
echo "=================================="
echo ""

# Variables
SERVICE_NAME="museum-system"
PROJECT_DIR="/home/admin/Documents/GitHub/museum-system"
MAIN_SCRIPT="$PROJECT_DIR/raspberry_pi/main.py"

echo "📊 Step 1: Checking service status..."
sudo systemctl status $SERVICE_NAME --no-pager -l
echo ""

echo "📊 Step 2: Checking recent service logs..."
echo "--- Last 50 lines from journalctl ---"
sudo journalctl -u $SERVICE_NAME -n 50 --no-pager
echo ""

echo "📊 Step 3: Checking if main.py exists and is executable..."
if [ -f "$MAIN_SCRIPT" ]; then
    echo "✅ main.py found at: $MAIN_SCRIPT"
    ls -la "$MAIN_SCRIPT"
    echo ""
else
    echo "❌ main.py NOT found at: $MAIN_SCRIPT"
    echo "🔍 Searching for main.py in project directory..."
    find "$PROJECT_DIR" -name "main.py" -type f 2>/dev/null
fi
echo ""

echo "📊 Step 4: Checking Python environment..."
echo "Python3 version:"
/usr/bin/python3 --version
echo ""
echo "Python3 path:"
which python3
echo ""

echo "📊 Step 5: Testing main.py execution manually..."
if [ -f "$MAIN_SCRIPT" ]; then
    echo "🧪 Attempting to run main.py directly..."
    cd "$PROJECT_DIR/raspberry_pi"
    timeout 10s /usr/bin/python3 "$MAIN_SCRIPT" 2>&1 || echo "Script execution failed or timed out"
else
    echo "⚠️  Cannot test - main.py not found"
fi
echo ""

echo "📊 Step 6: Checking project directory structure..."
echo "Contents of $PROJECT_DIR:"
ls -la "$PROJECT_DIR" 2>/dev/null || echo "Directory not accessible"
echo ""
if [ -d "$PROJECT_DIR/raspberry_pi" ]; then
    echo "Contents of $PROJECT_DIR/raspberry_pi:"
    ls -la "$PROJECT_DIR/raspberry_pi"
else
    echo "❌ raspberry_pi directory not found"
fi
echo ""

echo "📊 Step 7: Checking dependencies..."
echo "🔍 Checking if required Python packages are installed..."
/usr/bin/python3 -c "
import sys
packages = ['psutil', 'RPi.GPIO', 'paho.mqtt', 'numpy', 'opencv-python']
missing = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg} - OK')
    except ImportError:
        print(f'❌ {pkg} - MISSING')
        missing.append(pkg)

if missing:
    print(f'\\n📦 Install missing packages with:')
    print(f'pip3 install {\" \".join(missing)}')
"
echo ""

echo "📊 Step 8: Service file analysis..."
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
if [ -f "$SERVICE_FILE" ]; then
    echo "✅ Service file exists at: $SERVICE_FILE"
    echo "🔍 Service file contents:"
    cat "$SERVICE_FILE"
    echo ""
    echo "🔍 Service file permissions:"
    ls -la "$SERVICE_FILE"
else
    echo "❌ Service file not found at: $SERVICE_FILE"
fi
echo ""

echo "📊 Step 9: User and permissions check..."
echo "Current user: $(whoami)"
echo "User 'admin' exists: $(id admin 2>/dev/null && echo 'YES' || echo 'NO')"
echo "Groups for admin user:"
groups admin 2>/dev/null || echo "User admin not found"
echo ""

echo "📊 Step 10: Log files check..."
LOG_FILES=("/var/log/museum-system.log" "/var/log/museum-system-error.log")
for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        echo "✅ $log_file exists"
        echo "   Size: $(du -h "$log_file" | cut -f1)"
        echo "   Permissions: $(ls -la "$log_file")"
        echo "   Last 10 lines:"
        tail -10 "$log_file" 2>/dev/null || echo "   (empty or unreadable)"
    else
        echo "❌ $log_file not found"
    fi
    echo ""
done

echo "🔧 DIAGNOSTIC COMPLETE"
echo "======================"
echo ""
echo "🎯 QUICK FIXES TO TRY:"
echo ""
echo "EOF"
echo "   chmod +x $MAIN_SCRIPT"
echo ""
echo "2️⃣  If Python packages are missing:"
echo "   sudo apt update && sudo apt install python3-pip"
echo "   pip3 install psutil paho-mqtt RPi.GPIO numpy"
echo ""
echo "3️⃣  Reload and restart service:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl restart $SERVICE_NAME"
echo ""
echo "4️⃣  Check status again:"
echo "   sudo systemctl status $SERVICE_NAME"
echo ""
echo "5️⃣  Follow live logs:"
echo "   sudo journalctl -u $SERVICE_NAME -f"