# Raspberry Pi HW Watchdog Setup (SSH)

This guide enables automatic reboot recovery on Raspberry Pi when userspace or systemd gets stuck.

Run all commands on the Raspberry Pi over SSH.

## 1. Connect to RPi

```bash
ssh admin@TechMuzeumRoom1
```

## 2. Enable watchdog in boot config

Use this command to detect the correct config path and append `dtparam=watchdog=on` only if missing.

```bash
BOOTCFG="$( [ -f /boot/firmware/config.txt ] && echo /boot/firmware/config.txt || echo /boot/config.txt )"; \
grep -q '^dtparam=watchdog=on' "$BOOTCFG" || echo 'dtparam=watchdog=on' | sudo tee -a "$BOOTCFG"; \
echo "Using: $BOOTCFG"; \
grep -n '^dtparam=watchdog=on' "$BOOTCFG"
```

## 3. Load BCM watchdog module at boot

```bash
echo 'bcm2835_wdt' | sudo tee /etc/modules-load.d/bcm2835_wdt.conf
sudo modprobe bcm2835_wdt
lsmod | grep bcm2835_wdt
```

## 4. Enable systemd runtime watchdog

```bash
sudo mkdir -p /etc/systemd/system.conf.d
sudo tee /etc/systemd/system.conf.d/99-watchdog.conf > /dev/null << 'EOF'
[Manager]
RuntimeWatchdogSec=15s
RebootWatchdogSec=2min
EOF

sudo systemctl daemon-reexec
systemctl show -p RuntimeWatchdogUSec
```

Expected: `RuntimeWatchdogUSec` should be non-zero.

## 5. Reboot RPi

```bash
sudo reboot
```

Reconnect after reboot.

## 6. Verify after reboot

```bash
ls -l /dev/watchdog /dev/watchdog0
lsmod | grep bcm2835_wdt
systemctl show -p RuntimeWatchdogUSec
journalctl -b | grep -Ei 'watchdog|bcm2835'
```

Success indicators:
- `/dev/watchdog` and `/dev/watchdog0` exist
- `bcm2835_wdt` is loaded
- `RuntimeWatchdogUSec` is not `0`

## 7. Optional one-shot setup block

If you prefer one copy-paste block:

```bash
BOOTCFG="$( [ -f /boot/firmware/config.txt ] && echo /boot/firmware/config.txt || echo /boot/config.txt )" && \
( grep -q '^dtparam=watchdog=on' "$BOOTCFG" || echo 'dtparam=watchdog=on' | sudo tee -a "$BOOTCFG" ) && \
echo 'bcm2835_wdt' | sudo tee /etc/modules-load.d/bcm2835_wdt.conf && \
sudo modprobe bcm2835_wdt && \
sudo mkdir -p /etc/systemd/system.conf.d && \
sudo tee /etc/systemd/system.conf.d/99-watchdog.conf > /dev/null << 'EOF'
[Manager]
RuntimeWatchdogSec=15s
RebootWatchdogSec=2min
EOF
sudo systemctl daemon-reexec && \
systemctl show -p RuntimeWatchdogUSec && \
echo "Done. Reboot now with: sudo reboot"
```

## Rollback

```bash
BOOTCFG="$( [ -f /boot/firmware/config.txt ] && echo /boot/firmware/config.txt || echo /boot/config.txt )"
sudo rm -f /etc/systemd/system.conf.d/99-watchdog.conf
sudo rm -f /etc/modules-load.d/bcm2835_wdt.conf
sudo sed -i '/^dtparam=watchdog=on$/d' "$BOOTCFG"
sudo systemctl daemon-reexec
sudo reboot
```

## Related Runtime Validation Scripts

The following scripts were added during stabilization validation:

- `raspberry_pi/tests/test_main_scene_state.py`
	- Offline P0-2 checks (no pytest required): centralized scene state transitions + idempotent STOP.
- `raspberry_pi/tests/manual_scene_service_stress.py`
	- Runtime API stress for scene start/stop behavior.
- `raspberry_pi/tests/run_scene_stress_scenev01.sh`
	- Preset launcher for `SceneV01.json` stress checks.
- `raspberry_pi/tests/manual_web_retry_p03_test.sh`
	- Runtime P0-3 validation for forced web bind conflict and recovery.

Notes about logging evidence during P0-3 test:

- Depending on log level filters, `Fast retry` / `DEGRADED` messages may not appear in text logs.
- The test script supports both text logs (`museum.log` / `museum-errors.log`) and DB logs (`museum_logs.db`) as evidence sources.

Latest verified status (2026-04-01):

- P0-2: CLOSED and validated on RPi.
- P0-3: CLOSED and validated on RPi.
- Hardware watchdog: enabled and verified via `/dev/watchdog0` and `RuntimeWatchdogUSec`.
