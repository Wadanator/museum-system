# Stop services
sudo systemctl stop museum-watchdog
sudo systemctl stop museum-system

# Wait for ports to clear
sleep 1

# Start services
sudo systemctl start museum-system
sudo systemctl start museum-watchdog