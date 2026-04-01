#!/usr/bin/env python3
"""Manual stress test for scene start/stop API on a running museum service.

This script uses only Python standard library so it works offline on RPi.
"""

from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class ApiResult:
    ok: bool
    status: int
    body: str


def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _request_json(method: str, url: str, auth: str, timeout: float) -> ApiResult:
    req = urllib.request.Request(url=url, method=method)
    req.add_header("Authorization", auth)
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return ApiResult(ok=True, status=resp.getcode(), body=body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return ApiResult(ok=False, status=exc.code, body=body)
    except Exception as exc:  # noqa: BLE001 - manual diagnostic script
        return ApiResult(ok=False, status=-1, body=str(exc))


def _status(base_url: str, auth: str, timeout: float) -> ApiResult:
    return _request_json("GET", f"{base_url}/api/status", auth, timeout)


def _start_scene(base_url: str, scene_name: str, auth: str, timeout: float) -> ApiResult:
    return _request_json("POST", f"{base_url}/api/run_scene/{scene_name}", auth, timeout)


def _stop_scene(base_url: str, auth: str, timeout: float) -> ApiResult:
    return _request_json("POST", f"{base_url}/api/stop_scene", auth, timeout)


def _scene_exists(base_url: str, scene_name: str, auth: str, timeout: float) -> ApiResult:
    return _request_json("GET", f"{base_url}/api/scene/{scene_name}", auth, timeout)


def _parse_scene_running(status_body: str) -> bool | None:
    try:
        payload = json.loads(status_body)
    except json.JSONDecodeError:
        return None
    value = payload.get("scene_running")
    return bool(value) if isinstance(value, bool) else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Stress test scene API on running service")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Base URL of dashboard service")
    parser.add_argument("--user", default="admin", help="Basic auth username")
    parser.add_argument("--password", default="admin", help="Basic auth password")
    parser.add_argument("--scene", default="room1.json", help="Scene filename for /api/run_scene/<scene>")
    parser.add_argument("--cycles", type=int, default=50, help="Number of start attempts")
    parser.add_argument("--delay", type=float, default=0.15, help="Delay between requests (seconds)")
    parser.add_argument(
        "--mode",
        choices=["start-spam", "start-stop"],
        default="start-stop",
        help="start-spam: fire repeated start requests, start-stop: cycle start then stop",
    )
    parser.add_argument("--status-every", type=int, default=5, help="How often to poll /api/status")
    parser.add_argument(
        "--stop-at-end",
        action="store_true",
        help="Send /api/stop_scene once after spam loop",
    )
    parser.add_argument("--timeout", type=float, default=2.5, help="HTTP timeout per request")
    args = parser.parse_args()

    auth = _auth_header(args.user, args.password)

    initial_status = _status(args.base_url, auth, args.timeout)
    if initial_status.status == 401:
        print("[FAIL] Unauthorized. Check --user/--password.")
        return 2
    if initial_status.status <= 0:
        print(f"[FAIL] Service unreachable: {initial_status.body}")
        return 2

    print(f"[INFO] Initial /api/status: HTTP {initial_status.status}")

    scene_probe = _scene_exists(args.base_url, args.scene, auth, args.timeout)
    if scene_probe.status != 200:
        print(f"[FAIL] Scene '{args.scene}' is not accessible via API. HTTP={scene_probe.status}")
        print("       Fix scene name/path first to avoid false stress-test failures.")
        return 2

    start_200 = 0
    start_400 = 0
    start_other = 0
    stop_200 = 0
    stop_other = 0
    status_fail = 0

    for i in range(1, args.cycles + 1):
        result = _start_scene(args.base_url, args.scene, auth, args.timeout)

        if result.status == 200:
            start_200 += 1
            print(f"[{i:02d}] START -> 200")
        elif result.status == 400:
            start_400 += 1
            print(f"[{i:02d}] START -> 400 (scene already running)")
        else:
            start_other += 1
            print(f"[{i:02d}] START -> {result.status} BODY={result.body[:120]}")

        if args.mode == "start-stop":
            time.sleep(args.delay)
            stop_res = _stop_scene(args.base_url, auth, args.timeout)
            if stop_res.status == 200:
                stop_200 += 1
                print(f"[{i:02d}] STOP  -> 200")
            else:
                stop_other += 1
                print(f"[{i:02d}] STOP  -> {stop_res.status} BODY={stop_res.body[:120]}")

        if args.status_every > 0 and (i % args.status_every == 0 or i == args.cycles):
            s = _status(args.base_url, auth, args.timeout)
            if s.status != 200:
                status_fail += 1
                print(f"[{i:02d}] STATUS -> {s.status} BODY={s.body[:120]}")
            else:
                running = _parse_scene_running(s.body)
                print(f"[{i:02d}] STATUS -> 200 scene_running={running}")

        time.sleep(args.delay)

    stop_status = None
    if args.stop_at_end:
        stop_res = _stop_scene(args.base_url, auth, args.timeout)
        stop_status = stop_res.status
        print(f"[END] STOP -> {stop_res.status} BODY={stop_res.body[:120]}")

    final_status = _status(args.base_url, auth, args.timeout)
    final_running = _parse_scene_running(final_status.body) if final_status.status == 200 else None

    print("\n=== SUMMARY ===")
    print(f"Cycles: {args.cycles}")
    print(f"START 200: {start_200}")
    print(f"START 400 (expected during spam): {start_400}")
    print(f"START other (unexpected): {start_other}")
    if args.mode == "start-stop":
        print(f"STOP 200: {stop_200}")
        print(f"STOP other (unexpected): {stop_other}")
    print(f"STATUS failures: {status_fail}")
    if stop_status is not None:
        print(f"STOP status: {stop_status}")
    print(f"Final status code: {final_status.status}")
    print(f"Final scene_running: {final_running}")

    if start_other > 0 or stop_other > 0 or status_fail > 0:
        print("RESULT: FAIL (unexpected API errors observed)")
        return 1

    print("RESULT: PASS (no unexpected API errors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
