import py_compile
import sys
import tempfile
import threading
import time
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

import main as main_module


RUNTIME_MODULES = [
    "main.py",
    "utils/runtime/__init__.py",
    "utils/runtime/dashboard_notifier.py",
    "utils/runtime/scene_lifecycle.py",
    "utils/runtime/scene_runtime_service.py",
    "utils/runtime/scene_stop_coordinator.py",
    "utils/runtime/system_actions.py",
]


def _build_lightweight_controller():
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


def test_touched_runtime_modules_compile():
    for relative_path in RUNTIME_MODULES:
        py_compile.compile(str(RPI_DIR / relative_path), doraise=True)


def test_heartbeat_refreshes_running_state_and_stops_cleanly():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        controller = _build_lightweight_controller()
        try:
            main_module._SCENE_STATE_FILE = state_file
            assert controller._set_scene_running(
                True,
                "pytest-smoke",
                expect_current=False,
            )
            before = state_file.stat().st_mtime
            time.sleep(0.2)
            after = state_file.stat().st_mtime
            assert after > before

            assert controller._set_scene_running(False, "pytest-smoke-stop")
            stopped_mtime = state_file.stat().st_mtime
            time.sleep(0.15)
            assert state_file.stat().st_mtime == stopped_mtime
        finally:
            controller._set_scene_running(False, "pytest-smoke-cleanup")
            main_module._SCENE_STATE_FILE = original_state_file
