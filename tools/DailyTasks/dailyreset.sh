#!/bin/bash
# Script to set up a cron job for Raspberry Pi reboot at a specified time

echo "⏰ Setting up Raspberry Pi reboot schedule"
echo "====================================="

# Default time (midnight) if no arguments provided
HOUR=${1:-0}
MINUTE=${2:-0}

# Validate input time
if ! [[ "$HOUR" =~ ^[0-9]+$ ]] || ! [[ "$MINUTE" =~ ^[0-9]+$ ]] || [ "$HOUR" -gt 23 ] || [ "$MINUTE" -gt 59 ]; then
    echo "❌ Invalid time format. Usage: $0 <hour> <minute> (e.g., $0 3 30 for 3:30 AM)"
    exit 1
fi

# Cron job file
CRON_FILE="/etc/cron.d/museum-system-reboot"

echo "📝 Creating/Updating cron job for reboot at ${HOUR}:${MINUTE}..."
sudo tee "$CRON_FILE" > /dev/null << EOF
# Daily reboot of Raspberry Pi for Museum System at ${HOUR}:${MINUTE}
${MINUTE} ${HOUR} * * * root /sbin/shutdown -r now
EOF

# Set proper permissions
sudo chmod 644 "$CRON_FILE"

# Ensure cron service is enabled
echo "🔄 Enabling cron service..."
sudo systemctl enable cron
sudo systemctl start cron

# Verify cron job
echo "✅ Verifying cron job setup..."
sudo crontab -l -u root 2>/dev/null || echo "No existing root crontabs"
echo "Current reboot schedule:"
sudo cat "$CRON_FILE"

echo ""
echo "✅ Reboot Schedule Setup Complete!"
echo ""
echo "🕛 The Raspberry Pi will now reboot automatically every day at ${HOUR}:${MINUTE}"
echo "To change the time, run: sudo $0 <hour> <minute> (e.g., sudo $0 3 30 for 3:30 AM)"
echo "To check cron status: sudo systemctl status cron"
echo "To view cron logs: sudo journalctl -u cron"
echo "To remove the reboot schedule: sudo rm $CRON_FILE"
echo ""
echo "Note: Ensure system time is correct (check with 'date'). Set timezone with 'sudo dpkg-reconfigure tzdata' if needed."
