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
