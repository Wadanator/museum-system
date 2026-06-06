#!/usr/bin/env python3
"""Compatibility wrapper for the pytest runtime smoke checks.

Run on the Raspberry Pi from raspberry_pi/:

    python3 tests/manual_runtime_refactor_smoke.py

The actual safe offline checks now live in `test_runtime_smoke.py`, so routine
test output uses the same pytest style as the rest of the unit suite.
"""

import subprocess
import sys
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]

def main():
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_main_scene_state.py",
            "tests/test_runtime_smoke.py",
        ],
        cwd=RPI_DIR,
    )


if __name__ == "__main__":
    raise SystemExit(main().returncode)
