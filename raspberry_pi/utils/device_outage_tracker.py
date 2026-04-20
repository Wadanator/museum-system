#!/usr/bin/env python3
"""
Device Outage Tracker - Tracks ESP device outages (< 2 minutes).
Ignores disconnections >= 2 minutes (those are not outages, just offline devices).

Saves stats as JSON only, no logging.
"""

import json
import time
from pathlib import Path
from datetime import datetime


class DeviceOutageTracker:
    """Tracks device outages and saves statistics to JSON."""

    # Outages shorter than 2 minutes (120s) are tracked as outages
    # Longer outages are considered disconnections and ignored
    OUTAGE_THRESHOLD_SECONDS = 120

    def __init__(self, stats_file: str = None):
        """
        Initialize outage tracker.

        Args:
            stats_file: Path to JSON file for saving stats (default: Web/device_outages.json)
        """
        if stats_file is None:
            # Default location relative to this script's parent
            stats_file = Path(__file__).parent.parent / 'Web' / 'device_outages.json'
        
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)

        # In-memory tracking: device_id -> {'went_offline_at': timestamp}
        self.offline_times = {}

        # Load existing stats or start fresh
        self.stats = self._load_stats()

    def _load_stats(self) -> dict:
        """Load stats from JSON, or create empty structure if file doesn't exist."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return {'devices': {}}

    def _save_stats(self):
        """Save stats to JSON file."""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except OSError as e:
            import logging
            logging.getLogger('museum.device_outage_tracker').error(
                f"Failed to save outage stats to {self.stats_file}: {e}"
            )

    def on_device_status_change(self, device_id: str, status: str):
        """
        Handle device status change (online/offline).

        Args:
            device_id: Device identifier (e.g., 'room1/device/motor_1')
            status: 'online' or 'offline'
        """
        current_time = time.time()

        if status == 'offline':
            # Device went offline - record the time
            self.offline_times[device_id] = current_time

        elif status == 'online':
            # Device came back online - check if it was a short outage
            if device_id in self.offline_times:
                went_offline_at = self.offline_times[device_id]
                outage_duration = current_time - went_offline_at

                # Only track outages < 2 minutes (120s)
                # Longer outages are considered disconnections
                if outage_duration < self.OUTAGE_THRESHOLD_SECONDS:
                    self._record_outage(device_id, went_offline_at, current_time, outage_duration)

                del self.offline_times[device_id]

    def _record_outage(self, device_id: str, start_time: float, end_time: float, duration: float):
        """Record an outage event for a device."""
        # Ensure device entry exists
        if device_id not in self.stats['devices']:
            self.stats['devices'][device_id] = {
                'outage_count': 0,
                'total_outage_time_seconds': 0.0,
                'outages': []
            }

        device_stats = self.stats['devices'][device_id]

        # Update counts
        device_stats['outage_count'] += 1
        device_stats['total_outage_time_seconds'] += duration

        # Record individual outage
        device_stats['outages'].append({
            'start': datetime.fromtimestamp(start_time).isoformat(),
            'end': datetime.fromtimestamp(end_time).isoformat(),
            'duration_seconds': round(duration, 2)
        })

        # Save immediately
        self._save_stats()

    def get_stats(self) -> dict:
        """Return current statistics."""
        return self.stats.copy()
