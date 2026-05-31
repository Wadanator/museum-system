"""System-level actions exposed to the web dashboard."""

import subprocess
import sys


class SystemActions:
    """Reboot, shutdown, and service restart operations."""

    def __init__(self, owner, logger) -> None:
        self.owner = owner
        self.log = logger

    def system_restart(self) -> None:
        """Reboot the Raspberry Pi."""
        self.log.warning("Initiating System Reboot...")
        try:
            subprocess.Popen(['sudo', 'reboot'], shell=False)
        except Exception as exc:
            self.log.error(f"Failed to initiate reboot: {exc}")

    def system_shutdown(self) -> None:
        """Power off the Raspberry Pi."""
        self.log.warning("Initiating System Shutdown...")
        try:
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'], shell=False)
        except Exception as exc:
            self.log.error(f"Failed to initiate shutdown: {exc}")

    def service_restart(self) -> None:
        """Exit the process so systemd can restart the museum service."""
        self.log.warning("Initiating Service Restart (Exit)...")
        self.owner.shutdown_requested = True
        sys.exit(0)
