#!/usr/bin/env python3
"""Simple Raspberry Pi Temperature Monitor"""

import os
import time
import sys

def get_cpu_temp():
    """Get CPU temperature"""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            return int(f.read().strip()) / 1000.0
    except:
        return None

def temp_status(temp):
    """Return temperature status"""
    if temp is None:
        return "Unable to read"
    elif temp > 80:
        return f"{temp:.1f}°C ⚠️  CRITICAL"
    elif temp > 70:
        return f"{temp:.1f}°C ⚠️  HIGH"
    elif temp > 60:
        return f"{temp:.1f}°C ⚠️  WARM"
    else:
        return f"{temp:.1f}°C ✅ OK"

def monitor_once():
    """Single temperature reading"""
    temp = get_cpu_temp()
    print(f"CPU: {temp_status(temp)}")
    print(f"Time: {time.strftime('%H:%M:%S')}")

def monitor_continuous(interval=5):
    """Continuous monitoring"""
    print(f"Monitoring every {interval}s (Ctrl+C to stop)")
    try:
        while True:
            os.system('clear')
            monitor_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-c', '--continuous']:
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        monitor_continuous(interval)
    else:
        monitor_once()