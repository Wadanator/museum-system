#!/bin/bash
# Museum System Diagnostic Script
# This script will help identify why the museum-system service won't start

echo "🔍 Museum System Diagnostic Tool"
echo "================================="
echo ""

# Check if running as correct user
echo "👤 Current user: $(whoami)"
echo "📁 Current directory: $(pwd)"
echo ""

# Check service status
echo "🔧 Service Status:"
echo "-------------------"
sudo systemctl status museum-system --no-pager -l
echo ""

# Check recent service logs
echo "📋 Recent Service Logs:"
echo "----------------------"
sudo journalctl -u museum-system -n 20 --no-pager
echo ""

# Check if files exist and permissions
echo "📁 File Permissions Check:"
echo "--------------------------"
PROJECT_DIR="/home/admin/Documents/GitHub/museum-system"
MAIN_PY="$PROJECT_DIR/raspberry_pi/main.py"
SERVICE_FILE="/etc/systemd/system/museum-system.service"

echo "Project directory: $PROJECT_DIR"
ls -la "$PROJECT_DIR" 2>/dev/null || echo "❌ Project directory not found"
echo ""

echo "Main Python file: $MAIN_PY"
ls -la "$MAIN_PY" 2>/dev/null || echo "❌ Main Python file not found"
echo ""

echo "Service file: $SERVICE_FILE"
ls -la "$SERVICE_FILE" 2>/dev/null || echo "❌ Service file not found"
echo ""

# Check Python and dependencies
echo "🐍 Python Environment:"
echo "----------------------"
echo "Python3 location: $(which python3)"
python3 --version 2>/dev/null || echo "❌ Python3 not found"
echo ""

echo "Current working directory test:"
cd "$PROJECT_DIR/raspberry_pi" 2>/dev/null && echo "✅ Can access project directory" || echo "❌ Cannot access project directory"
echo ""

# Check if we can run the main.py manually
echo "🧪 Manual Execution Test:"
echo "-------------------------"
echo "Trying to run main.py manually..."
cd "$PROJECT_DIR/raspberry_pi" 2>/dev/null || exit 1

# Try to run it briefly to see if there are import errors
timeout 5 python3 main.py 2>&1 | head -10
echo ""

# Check user groups
echo "👥 User Groups:"
echo "---------------"
groups admin
echo ""

# Check if GPIO group exists
echo "🔌 GPIO Group Check:"
echo "-------------------"
getent group gpio || echo "❌ GPIO group not found"
echo ""

# Check systemd service file content
echo "📄 Service File Content:"
echo "------------------------"
cat "$SERVICE_FILE" 2>/dev/null || echo "❌ Cannot read service file"
echo ""

# Check for any conflicting processes
echo "🔍 Process Check:"
echo "----------------"
ps aux | grep -i museum | grep -v grep
echo ""

# Check system resources
echo "💾 System Resources:"
echo "-------------------"
echo "Memory usage:"
free -h
echo ""
echo "Disk space:"
df -h / 2>/dev/null
echo ""

echo "🎯 DIAGNOSTIC SUMMARY:"
echo "====================="
echo ""
echo "Next steps to try:"
echo "1. Check the service logs above for specific error messages"
echo "2. Try running the manual execution test results"
echo "3. Verify file permissions and user groups"
echo "4. Check if all dependencies are installed"
echo ""
echo "Common fixes:"
echo "- sudo systemctl daemon-reload"
echo "- sudo systemctl reset-failed museum-system"
echo "- Check if user 'admin' has proper group permissions"
echo "- Ensure all Python dependencies are installed"
echo ""
echo "🔧 Quick fix commands to try:"
echo "sudo systemctl stop museum-system"
echo "sudo systemctl stop museum-watchdog"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl reset-failed museum-system"
echo "sudo systemctl start museum-system"