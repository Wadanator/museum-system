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


class _ActuatorStoreCounter:
    def __init__(self):
        self.sources = []

    def force_all_off(self, source):
        self.sources.append(source)
        return 1


class _WebDashboardStub:
    def __init__(self):
        self.status_calls = 0

    def broadcast_status(self):
        self.status_calls += 1


class _AmbientPolicyStub:
    def __init__(
        self,
        ignore_default=False,
        allow_named=True,
        boot_result=True,
        restore_result=True,
    ):
        self.ignore_default = ignore_default
        self.allow_named = allow_named
        self.boot_result = boot_result
        self.restore_result = restore_result
        self.boot_calls = 0
        self.restore_calls = 0

    def should_ignore_default_start(self):
        return self.ignore_default

    def should_allow_named_scene_start(self):
        return self.allow_named

    def start_after_boot_if_needed(self):
        self.boot_calls += 1
        return self.boot_result

    def start_after_mqtt_restore_if_needed(self):
        self.restore_calls += 1
        return self.restore_result


class _SystemMonitorStub:
    def __init__(self):
        self.ready_calls = 0

    def send_ready_notification(self):
        self.ready_calls += 1


def _build_controller(scene_running=False):
    controller = MuseumController.__new__(MuseumController)
    controller.config = {
        "startup_mode": "classic",
        "json_file_name": "SceneV01.json",
    }
    controller.scene_lock = threading.Lock()
    controller.scene_running = scene_running
    controller.room_id = "room1"
    controller.json_file_name = "SceneV01.json"
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


def _attach_ambient_policy(controller, policy):
    controller._ambient_loop_service = lambda: policy
    return policy


def test_transition_updates_file_and_is_idempotent():
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


def test_stop_scene_is_idempotent():
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
            controller.actuator_state_store = _ActuatorStoreCounter()

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
            # First STOP handles the active scene, second STOP handles the
            # already-idle "stop all devices" path.
            assert stop_calls["count"] == 2
            assert controller.actuator_state_store.sources == [
                "external_stop",
                "external_stop_idle",
            ]
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_start_scene_by_name_returns_real_start_result():
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


def test_default_scene_start_ignored_by_ambient_policy():
    controller = _build_controller(scene_running=False)
    _attach_ambient_policy(controller, _AmbientPolicyStub(ignore_default=True))

    def _fail_start(scene_filename, log_message):
        raise AssertionError("default scene start should be ignored")

    controller._initiate_scene_start = _fail_start

    assert controller.on_button_press() is False
    assert controller.start_default_scene() is False


def test_default_scene_start_allowed_by_classic_policy():
    controller = _build_controller(scene_running=False)
    _attach_ambient_policy(controller, _AmbientPolicyStub(ignore_default=False))

    start_calls = []

    def _initiate(scene_filename, log_message):
        start_calls.append((scene_filename, log_message))
        return True

    controller._initiate_scene_start = _initiate

    assert controller.on_button_press() is True
    assert controller.start_default_scene() is True
    assert start_calls == [
        ("SceneV01.json", "Button pressed - starting default scene"),
        ("SceneV01.json", "Starting default scene"),
    ]


def test_named_scene_start_can_be_rejected_by_ambient_policy():
    controller = _build_controller(scene_running=False)
    _attach_ambient_policy(controller, _AmbientPolicyStub(allow_named=False))

    def _fail_start(scene_filename, log_message):
        raise AssertionError("named scene start should be rejected")

    controller._initiate_scene_start = _fail_start

    assert controller.start_scene_by_name("manual.json") is False


def test_ambient_boot_policy_hook_is_called_after_initial_connection():
    controller = _build_controller(scene_running=False)
    policy = _attach_ambient_policy(controller, _AmbientPolicyStub(boot_result=True))

    assert controller._start_ambient_after_initial_connection() is True
    assert policy.boot_calls == 1


def test_mqtt_restore_calls_ready_notification_and_ambient_policy():
    controller = _build_controller(scene_running=False)
    controller.system_monitor = _SystemMonitorStub()
    policy = _attach_ambient_policy(controller, _AmbientPolicyStub(restore_result=True))

    controller._on_mqtt_connection_restored()

    assert controller.system_monitor.ready_calls == 1
    assert policy.restore_calls == 1


def test_missing_scene_broadcasts_status_update():
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
        ("transition_updates_file_and_is_idempotent", test_transition_updates_file_and_is_idempotent),
        ("stop_scene_is_idempotent", test_stop_scene_is_idempotent),
        ("start_scene_by_name_returns_real_start_result", test_start_scene_by_name_returns_real_start_result),
        ("missing_scene_broadcasts_status_update", test_missing_scene_broadcasts_status_update),
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
