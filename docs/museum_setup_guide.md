# Museum System Service Setup Guide

This guide describes how to deploy the Raspberry Pi controller as a systemd service so the museum room starts automatically on boot and restarts if unexpected failures occur.

---

## Prerequisites

- Raspberry Pi OS (Bullseye or newer) with Python 3.9+
- Project cloned to `/home/<user>/museum-system` (adjust paths if different)
- Virtual environment or system Python with dependencies installed:
  ```bash
  cd /home/<user>/museum-system/raspberry_pi
  pip install -r requirements.txt
  ```
- Updated configuration in `raspberry_pi/config/config.ini`
- Working MQTT broker reachable from the Pi

---

## Install the systemd Service

1. **Make the helper script executable**
   ```bash
   cd /home/<user>/museum-system/raspberry_pi
   chmod +x setup_museum_service.sh
   ```

2. **Run the setup script** – installs the unit file, configures log directories, and reloads systemd.
   ```bash
   ./setup_museum_service.sh
   ```

3. **Enable and start the service**
   ```bash
   sudo systemctl enable museum-system.service
   sudo systemctl start museum-system.service
   ```

The service uses `main.py` as the entry point and exports logs to `/var/log/museum-system/` by default.

---

## Daily Operations

| Command | Purpose |
| --- | --- |
| `sudo systemctl status museum-system` | View service status and last log lines |
| `sudo journalctl -u museum-system -f` | Stream live logs (Ctrl+C to exit) |
| `sudo systemctl restart museum-system` | Restart the controller after configuration updates |
| `sudo systemctl stop museum-system` | Stop the controller (service will remain disabled until started again) |
| `sudo systemctl disable museum-system` | Prevent auto-start on boot |

---

## Troubleshooting

- **Service fails immediately** – Confirm `python3` points to the interpreter that has all dependencies installed. Adjust the `ExecStart` path in `service/museum-system.service` if needed.
- **Configuration errors** – Review `/var/log/museum-system/museum-errors.log` for stack traces. The service will stay running but refuse to process scenes until the configuration is valid.
- **MQTT connection problems** – Verify broker IP/port in `config.ini` and check firewall rules. The controller retries automatically but logs warnings in `museum-warnings.log` when connections flap.
- **Button not responsive** – Ensure the GPIO pin defined in the config matches your wiring and that the user running the service has GPIO permissions (the setup script adds the user to the `gpio` group).

---

## Removing the Service

To uninstall the auto-start service completely:

```bash
sudo systemctl stop museum-system
sudo systemctl disable museum-system
sudo rm /etc/systemd/system/museum-system.service
sudo systemctl daemon-reload
```

Logs under `/var/log/museum-system/` can be deleted manually if desired.
