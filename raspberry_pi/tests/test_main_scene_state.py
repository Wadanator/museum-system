import threading
import sys
import tempfile
from pathlib import Path

# Ensure raspberry_pi/ is importable when tests are executed from repository root.
RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

import main as main_module
from main import MuseumController


class _Counter:
    def __init__(self):
        self.calls = 0

    def stop_scene(self):
        self.calls += 1

    def stop_audio(self):
        self.calls += 1

    def stop_video(self):
        self.calls += 1


class _WebDashboardStub:
    def __init__(self):
        self.status_calls = 0

    def broadcast_status(self):
        self.status_calls += 1


def _build_controller(scene_running=False):
    controller = MuseumController.__new__(MuseumController)
    controller.scene_lock = threading.Lock()
    controller.scene_running = scene_running
    controller.room_id = "room1"
    controller.scene_parser = None
    controller.audio_handler = None
    controller.video_handler = None
    controller.web_dashboard = None
    return controller


def _manual_test_transition_updates_file_and_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            controller = _build_controller(scene_running=False)

            assert controller._set_scene_running(True, "start", expect_current=False) is True
            assert controller.scene_running is True
            assert state_file.read_text() == "running"

            assert controller._set_scene_running(True, "duplicate-start") is False
            assert controller.scene_running is True
            assert state_file.read_text() == "running"

            assert controller._set_scene_running(False, "stop", expect_current=True) is True
            assert controller.scene_running is False
            assert state_file.read_text() == "idle"
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def _manual_test_stop_scene_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file

            parser = _Counter()
            audio = _Counter()
            video = _Counter()
            stop_calls = {"count": 0}

            controller = _build_controller(scene_running=True)
            controller.scene_parser = parser
            controller.audio_handler = audio
            controller.video_handler = video

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            assert controller.stop_scene() is True
            assert controller.scene_running is False
            assert state_file.read_text() == "idle"

            assert controller.stop_scene() is True
            assert controller.scene_running is False

            assert parser.calls == 1
            assert audio.calls == 1
            assert video.calls == 1
            assert stop_calls["count"] == 1
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def _manual_test_start_scene_by_name_returns_real_start_result():
    controller = _build_controller(scene_running=False)

    start_calls = {"count": 0}

    def _initiate(scene_filename, log_message):
        start_calls["count"] += 1
        if scene_filename == "ok.json":
            return True
        return False

    controller._initiate_scene_start = _initiate

    assert controller.start_scene_by_name("ok.json") is True
    assert controller.start_scene_by_name("already_running.json") is False
    assert start_calls["count"] == 2


def _manual_test_missing_scene_broadcasts_status_update():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        original_exists = main_module.os.path.exists
        try:
            main_module._SCENE_STATE_FILE = state_file

            controller = _build_controller(scene_running=True)
            controller.scenes_dir = tmp_dir
            controller.room_id = "room1"
            controller.scene_parser = object()
            controller.video_handler = None
            controller.web_dashboard = _WebDashboardStub()

            main_module.os.path.exists = lambda _: False

            controller._run_scene_logic("missing.json")

            assert controller.scene_running is False
            assert state_file.read_text() == "idle"
            assert controller.web_dashboard.status_calls == 1
        finally:
            main_module._SCENE_STATE_FILE = original_state_file
            main_module.os.path.exists = original_exists


if __name__ == "__main__":
    print("Running offline P0-2 checks (no pytest required)...")
    tests = [
        ("transition_updates_file_and_is_idempotent", _manual_test_transition_updates_file_and_is_idempotent),
        ("stop_scene_is_idempotent", _manual_test_stop_scene_is_idempotent),
        ("start_scene_by_name_returns_real_start_result", _manual_test_start_scene_by_name_returns_real_start_result),
        ("missing_scene_broadcasts_status_update", _manual_test_missing_scene_broadcasts_status_update),
    ]

    failed = 0
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"[PASS] {test_name}")
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {test_name}: {exc}")

    if failed:
        print(f"Manual offline tests failed: {failed}/{len(tests)}")
        raise SystemExit(1)

    print(f"Manual offline tests passed: {len(tests)}/{len(tests)}")
