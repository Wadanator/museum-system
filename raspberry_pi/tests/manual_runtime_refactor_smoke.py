#!/usr/bin/env python3
"""Offline smoke test for the main.py runtime refactor.

Run on the Raspberry Pi from raspberry_pi/:

    python3 tests/manual_runtime_refactor_smoke.py

This intentionally avoids MQTT, GPIO, audio, video, and the Flask server. It
checks that the refactored controller wrappers still preserve the core scene
lifecycle/STOP behavior and that the touched Python modules compile.
"""

import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))


def _run(label, args):
    print(f"\n== {label} ==")
    result = subprocess.run(
        args,
        cwd=RPI_DIR,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def _build_lightweight_controller(main_module):
    controller = main_module.MuseumController.__new__(main_module.MuseumController)
    controller.scene_lock = threading.Lock()
    controller.scene_running = False
    controller.room_id = "room1"
    controller.scene_parser = None
    controller.audio_handler = None
    controller.video_handler = None
    controller.web_dashboard = None
    controller.actuator_state_store = None
    controller.scene_heartbeat_interval = 0.05
    controller._heartbeat_stop_event = threading.Event()
    controller._heartbeat_thread = None
    controller.shutdown_requested = False
    return controller


def _manual_heartbeat_check():
    import main as main_module

    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        controller = _build_lightweight_controller(main_module)
        try:
            main_module._SCENE_STATE_FILE = state_file
            assert controller._set_scene_running(True, "manual-smoke", expect_current=False)
            before = state_file.stat().st_mtime
            time.sleep(0.2)
            after = state_file.stat().st_mtime
            assert after > before, "heartbeat did not refresh the scene-state file"
            assert controller._set_scene_running(False, "manual-smoke-stop")
            stopped_mtime = state_file.stat().st_mtime
            time.sleep(0.15)
            assert state_file.stat().st_mtime == stopped_mtime, "heartbeat kept writing after stop"
        finally:
            controller._set_scene_running(False, "manual-smoke-cleanup")
            main_module._SCENE_STATE_FILE = original_state_file


def main():
    py = sys.executable

    _run(
        "compile touched runtime modules",
        [
            py,
            "-m",
            "py_compile",
            "main.py",
            "utils/runtime/__init__.py",
            "utils/runtime/dashboard_notifier.py",
            "utils/runtime/scene_lifecycle.py",
            "utils/runtime/scene_runtime_service.py",
            "utils/runtime/scene_stop_coordinator.py",
            "utils/runtime/system_actions.py",
        ],
    )

    _run(
        "manual scene-state behavior checks",
        [py, "tests/test_main_scene_state.py"],
    )

    print("\n== manual heartbeat check ==")
    _manual_heartbeat_check()
    print("[PASS] heartbeat refresh/stop behavior")

    print("\nRuntime refactor smoke test passed.")


if __name__ == "__main__":
    main()
