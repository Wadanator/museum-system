#!/usr/bin/env python3
"""Run all non-stress checks that are safe for routine Raspberry Pi use.

Default behavior:
  - run the quick pytest suite, including offline runtime smoke checks

It deliberately does NOT run service/web diagnostics unless --include-service
is provided, because those checks talk to the live dashboard and may start/stop
a scene. They are not stress tests, but they are not purely offline either.
"""

import argparse
import subprocess
import sys
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

try:
    from Web.config import Config
    DEFAULT_USER = Config.USERNAME
    DEFAULT_PASSWORD = Config.PASSWORD
except Exception:
    DEFAULT_USER = "admin"
    DEFAULT_PASSWORD = "admin"


def _run(label: str, args: list[str]) -> int:
    print(f"\n== {label} ==")
    result = subprocess.run(args, cwd=RPI_DIR)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run safe non-stress museum-system checks."
    )
    parser.add_argument(
        "--include-service",
        action="store_true",
        help=(
            "Also run the WebSocket/dashboard diagnostic against a running "
            "service. This may start/stop a scene."
        ),
    )
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--password", "--pass", default=DEFAULT_PASSWORD)
    parser.add_argument("--scene", default=None)
    args = parser.parse_args()

    checks = [
        (
            "quick pytest suite",
            [sys.executable, "tests/run_quick_tests.py"],
        )
    ]

    if args.include_service:
        service_cmd = [
            sys.executable,
            "tests/manual_ws_museum_diagnostic.py",
            "--url",
            args.url,
            "--user",
            args.user,
            "--pass",
            args.password,
        ]
        if args.scene:
            service_cmd.extend(["--scene", args.scene])
        checks.append(("live dashboard/WebSocket diagnostic", service_cmd))

    for label, cmd in checks:
        rc = _run(label, cmd)
        if rc != 0:
            print(f"\n[FAIL] {label} failed with exit code {rc}")
            return rc

    print("\nAll requested safe checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
