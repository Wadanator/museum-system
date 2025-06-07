#!/bin/bash
# Heartbeat Monitor for Museum System

echo "🫀 Museum System Heartbeat Monitor"
echo "=================================="
echo "Monitoring systemd watchdog heartbeats..."
echo "Press Ctrl+C to stop"
echo ""

SERVICE_NAME="museum-system"

# Function to get service status
get_service_info() {
    local status=$(systemctl show $SERVICE_NAME --property=ActiveState --value)
    local main_pid=$(systemctl show $SERVICE_NAME --property=MainPID --value)
    local watchdog_timestamp=$(systemctl show $SERVICE_NAME --property=WatchdogTimestamp --value)
    local watchdog_usec=$(systemctl show $SERVICE_NAME --property=WatchdogUSec --value)
    
    echo "$(date '+%H:%M:%S') - Status: $status | PID: $main_pid | Last Watchdog: $watchdog_timestamp"
}

# Monitor in real-time
while true; do
    get_service_info
    sleep 2
done