#!/usr/bin/env python3
"""Simple Raspberry Pi Temperature Monitor"""

import os
import time
import sys


TEMP_FILE = "/sys/class/thermal/thermal_zone0/temp"


def get_cpu_temp():
    """Get CPU temperature in °C."""
    try:
        with open(TEMP_FILE, "r") as f:
            return int(f.read().strip()) / 1000.0
    except Exception as e:
        print(f"Error reading temperature: {e}")
        return None


def temp_status(temp):
    """Return temperature status."""
    if temp is None:
        return "Unable to read"
    elif temp >= 80:
        return f"{temp:.1f}°C [WARN]  CRITICAL"
    elif temp >= 70:
        return f"{temp:.1f}°C [WARN]  HIGH"
    elif temp >= 60:
        return f"{temp:.1f}°C [WARN]  WARM"
    else:
        return f"{temp:.1f}°C [OK] OK"


def monitor_once():
    """Single temperature reading."""
    temp = get_cpu_temp()
    print(f"CPU:  {temp_status(temp)}")
    print(f"Time: {time.strftime('%H:%M:%S')}")


def monitor_continuous(interval=5):
    """Continuous monitoring."""
    print(f"Monitoring every {interval}s. Press Ctrl+C to stop.")
    time.sleep(1)

    try:
        while True:
            os.system("clear")
            monitor_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-c", "--continuous"]:
        try:
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        except ValueError:
            print("Invalid interval. Using default 5 seconds.")
            interval = 5

        monitor_continuous(interval)
    else:
        monitor_once()