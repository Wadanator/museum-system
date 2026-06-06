#!/usr/bin/env python3
"""Run the safe, fast pytest suite for routine Raspberry Pi checks.

Usage from raspberry_pi/:

    python3 tests/run_quick_tests.py

This intentionally excludes manual diagnostics, websocket/service integration
checks, and stress tests. It is the "did I break core code?" test set.
"""

import subprocess
import sys
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]

QUICK_TEST_FILES = [
    "tests/test_schema_validator.py",
    "tests/test_mqtt_feedback_state.py",
    "tests/test_device_status_broadcast.py",
    "tests/test_main_scene_state.py",
    "tests/test_heartbeat.py",
    "tests/test_video_handler_end_detection.py",
    "tests/test_runtime_smoke.py",
]


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *QUICK_TEST_FILES,
    ]
    print("Running quick pytest suite:")
    for path in QUICK_TEST_FILES:
        print(f"  - {path}")
    print()

    result = subprocess.run(cmd, cwd=RPI_DIR)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
