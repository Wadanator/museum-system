# Museum System Auto-Start Setup

## Quick Setup

1. **Save the script**:
   ```bash
   cd /home/admin/Documents/GitHub/museum-system/
   nano setup_museum_service.sh
   ```
   Paste the script content, save (Ctrl+X, Y, Enter)

2. **Make executable and run**:
   ```bash
   chmod +x setup_museum_service.sh
   ./setup_museum_service.sh
   ```

3. **Start the service**:
   ```bash
   sudo systemctl start museum-system
   ```

## Management Commands

- **Check status**: `sudo systemctl status museum-system`
- **View logs**: `sudo journalctl -u museum-system -f`
- **Stop service**: `sudo systemctl stop museum-system`
- **Restart service**: `sudo systemctl restart museum-system`

## What This Does

- ✅ Starts museum system automatically on boot
- ✅ Automatically restarts if it crashes
- ✅ Creates log files for troubleshooting
- ✅ Proper GPIO permissions for Raspberry Pi

## Troubleshooting

If setup fails, check:
- Project exists at `/home/admin/Documents/GitHub/museum-system/`
- Main script exists at `raspberry_pi/main.py`
- You have sudo privileges


## Commands
✅ Museum System Auto-Start Setup Complete!

Service Management Commands:
  Start:   sudo systemctl start museum-system
  Stop:    sudo systemctl stop museum-system
  Status:  sudo systemctl status museum-system
  Logs:    sudo journalctl -u museum-system -f
  Disable: sudo systemctl disable museum-system

The service will now:
  ✅ Start automatically on boot
  ✅ Restart automatically if it crashes
  ✅ Wait for network before starting
  ✅ Retry up to 5 times if startup fails

To start the service now, run:
  sudo systemctl start museum-system