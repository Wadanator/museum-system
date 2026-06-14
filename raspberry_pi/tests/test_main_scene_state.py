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
from utils.runtime.scene_runtime_service import (
    OUTCOME_ERROR,
    OUTCOME_EXPLICIT_STOP,
    OUTCOME_LOAD_FAILURE,
    OUTCOME_MISSING_SCENE,
    OUTCOME_NORMAL_END,
    OUTCOME_SHUTDOWN,
    OUTCOME_START_FAILURE,
)


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


class _SceneParserStub:
    def __init__(
        self,
        *,
        owner=None,
        load_result=True,
        scene_data=None,
        start_result=True,
        process_results=None,
        stop_on_process=False,
        shutdown_on_process=False,
    ):
        self.owner = owner
        self.load_result = load_result
        self.scene_data = {"initialState": "START"} if scene_data is None else scene_data
        self.start_result = start_result
        self.process_results = list(process_results or [False])
        self.stop_on_process = stop_on_process
        self.shutdown_on_process = shutdown_on_process
        self.load_calls = []
        self.start_calls = 0
        self.process_calls = 0

    def load_scene(self, scene_path):
        self.load_calls.append(scene_path)
        return self.load_result

    def start_scene(self):
        self.start_calls += 1
        return self.start_result

    def process_scene(self):
        self.process_calls += 1
        if self.stop_on_process and self.owner:
            self.owner.scene_running = False
        if self.shutdown_on_process and self.owner:
            self.owner.shutdown_requested = True
        if self.process_results:
            return self.process_results.pop(0)
        return False


class _AmbientPolicyStub:
    def __init__(
        self,
        ignore_default=False,
        allow_named=True,
        suspend_on_stop=False,
        boot_result=True,
        restore_result=True,
        enabled=False,
        scene_name="SceneV01.json",
        cycle_cleanup="scene_only",
        restart_results=None,
        restart_delay=0.0,
        wait_results=None,
        failure_retry_results=None,
    ):
        self.ignore_default = ignore_default
        self.allow_named = allow_named
        self.suspend_on_stop = suspend_on_stop
        self.boot_result = boot_result
        self.restore_result = restore_result
        self.enabled = enabled
        self._scene_name = scene_name
        self._cycle_cleanup = cycle_cleanup
        self.restart_results = list(restart_results or [])
        self.restart_delay = restart_delay
        self.wait_results = list(wait_results or [])
        self.failure_retry_results = list(failure_retry_results or [])
        self.boot_calls = 0
        self.restore_calls = 0
        self.suspend_calls = 0
        self.shutdown_calls = 0
        self.restart_calls = []
        self.failure_retry_calls = []
        self.wait_calls = []
        self.recorded_outcomes = []

    def is_enabled(self):
        return self.enabled

    def scene_name(self):
        return self._scene_name

    def cycle_cleanup(self):
        return self._cycle_cleanup

    def should_ignore_default_start(self):
        return self.ignore_default

    def should_allow_named_scene_start(self):
        return self.allow_named

    def should_suspend_on_operator_stop(self):
        return self.suspend_on_stop

    def suspend_by_operator_stop(self):
        self.suspend_calls += 1

    def request_shutdown(self):
        self.shutdown_calls += 1

    def should_restart_after_scene(self, scene_filename, *, normal_end):
        self.restart_calls.append((scene_filename, normal_end))
        if self.restart_results:
            return self.restart_results.pop(0)
        return False

    def should_retry_after_scene_failure(self, scene_filename, outcome):
        self.failure_retry_calls.append((scene_filename, outcome))
        if self.failure_retry_results:
            return self.failure_retry_results.pop(0)
        return False

    def restart_delay_seconds(self, *, normal_end):
        return self.restart_delay

    def wait_for_restart_delay(self, delay_seconds):
        self.wait_calls.append(delay_seconds)
        if self.wait_results:
            return self.wait_results.pop(0)
        return True

    def record_outcome(self, outcome):
        self.recorded_outcomes.append(outcome)

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
    controller._cleaned_up = False
    controller.mqtt_client = None
    controller.services = None
    controller.scene_thread = None
    controller.current_scene_name = None
    controller.current_scene_state = None
    controller.scene_processing_sleep = 0.001
    controller.scenes_dir = "."
    return controller


def _attach_ambient_policy(controller, policy):
    controller._ambient_loop_service = lambda: policy
    return policy


def _touch_scene_file(tmp_dir, scene_name="scene.json"):
    scene_dir = Path(tmp_dir) / "room1"
    scene_dir.mkdir(parents=True, exist_ok=True)
    scene_path = scene_dir / scene_name
    scene_path.write_text("{}", encoding="utf-8")
    return scene_path


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


def test_operator_stop_suspends_ambient_policy_before_full_stop():
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
            policy = _attach_ambient_policy(
                controller,
                _AmbientPolicyStub(suspend_on_stop=True),
            )
            controller.scene_parser = parser
            controller.audio_handler = audio
            controller.video_handler = video
            controller.actuator_state_store = _ActuatorStoreCounter()

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            assert controller.stop_scene() is True
            assert policy.suspend_calls == 1
            assert policy.shutdown_calls == 0
            assert parser.calls == 1
            assert audio.calls == 1
            assert video.calls == 1
            assert stop_calls["count"] == 1
            assert controller.actuator_state_store.sources == ["external_stop"]
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_operator_stop_does_not_suspend_ambient_when_resume_after_delay():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file

            controller = _build_controller(scene_running=True)
            policy = _attach_ambient_policy(
                controller,
                _AmbientPolicyStub(suspend_on_stop=False),
            )
            controller.broadcast_stop = lambda: None

            assert controller.stop_scene() is True
            assert policy.suspend_calls == 0
            assert policy.shutdown_calls == 0
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_shutdown_signal_requests_ambient_shutdown():
    controller = _build_controller(scene_running=False)
    policy = _attach_ambient_policy(controller, _AmbientPolicyStub())

    controller._signal_handler(15, None)

    assert controller.shutdown_requested is True
    assert policy.shutdown_calls == 1


def test_cleanup_requests_ambient_shutdown_without_operator_suspend():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file

            controller = _build_controller(scene_running=True)
            policy = _attach_ambient_policy(
                controller,
                _AmbientPolicyStub(suspend_on_stop=True),
            )
            controller.broadcast_stop = lambda: None

            controller.cleanup()

            assert policy.shutdown_calls >= 1
            assert policy.suspend_calls == 0
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

            outcome = controller._run_scene_logic("missing.json")

            assert outcome == OUTCOME_MISSING_SCENE
            assert controller.scene_running is False
            assert state_file.read_text() == "idle"
            assert controller.web_dashboard.status_calls == 1
        finally:
            main_module._SCENE_STATE_FILE = original_state_file
            main_module.os.path.exists = original_exists


def test_normal_scene_completion_returns_outcome_and_preserves_full_cleanup():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "normal.json")

            controller = _build_controller(scene_running=True)
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "normal.json"
            controller.scene_parser = _SceneParserStub(process_results=[False])
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            stop_calls = {"count": 0}

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            outcome = controller._run_scene_logic("normal.json")

            assert outcome == OUTCOME_NORMAL_END
            assert controller.scene_running is False
            assert controller.current_scene_name is None
            assert controller.audio_handler.calls == 1
            assert controller.video_handler.calls == 2
            assert controller.actuator_state_store.sources == ["scene_end"]
            assert stop_calls["count"] == 1
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_scene_load_failure_returns_outcome_without_full_cleanup():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "bad.json")

            controller = _build_controller(scene_running=True)
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "bad.json"
            controller.scene_parser = _SceneParserStub(load_result=False)
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            stop_calls = {"count": 0}

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            outcome = controller._run_scene_logic("bad.json")

            assert outcome == OUTCOME_LOAD_FAILURE
            assert controller.scene_running is False
            assert controller.audio_handler.calls == 0
            assert controller.video_handler.calls == 0
            assert controller.actuator_state_store.sources == []
            assert stop_calls["count"] == 0
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_scene_start_failure_returns_outcome_and_preserves_full_cleanup():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "start-fails.json")

            controller = _build_controller(scene_running=True)
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "start-fails.json"
            controller.scene_parser = _SceneParserStub(start_result=False)
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            stop_calls = {"count": 0}

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            outcome = controller._run_scene_logic("start-fails.json")

            assert outcome == OUTCOME_START_FAILURE
            assert controller.scene_running is False
            assert controller.audio_handler.calls == 1
            assert controller.video_handler.calls == 1
            assert controller.actuator_state_store.sources == ["scene_end"]
            assert stop_calls["count"] == 1
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_external_stop_during_processing_returns_outcome_without_duplicate_stop():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "external-stop.json")

            controller = _build_controller(scene_running=True)
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "external-stop.json"
            controller.scene_parser = _SceneParserStub(
                owner=controller,
                stop_on_process=True,
                process_results=[False],
            )
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            stop_calls = {"count": 0}

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            outcome = controller._run_scene_logic("external-stop.json")

            assert outcome == OUTCOME_EXPLICIT_STOP
            assert controller.scene_running is False
            assert controller.audio_handler.calls == 1
            assert controller.video_handler.calls == 2
            assert controller.actuator_state_store.sources == []
            assert stop_calls["count"] == 0
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_shutdown_during_processing_returns_outcome_and_preserves_cleanup():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "shutdown.json")

            controller = _build_controller(scene_running=True)
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "shutdown.json"
            controller.scene_parser = _SceneParserStub(
                owner=controller,
                shutdown_on_process=True,
                process_results=[False],
            )
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            stop_calls = {"count": 0}

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            outcome = controller._run_scene_logic("shutdown.json")

            assert outcome == OUTCOME_SHUTDOWN
            assert controller.scene_running is False
            assert controller.audio_handler.calls == 1
            assert controller.video_handler.calls == 2
            assert controller.actuator_state_store.sources == ["scene_end"]
            assert stop_calls["count"] == 1
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_ambient_scene_only_restarts_without_global_stop_between_cycles():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "ambient.json")

            controller = _build_controller(scene_running=True)
            controller.config["startup_mode"] = "ambient"
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "ambient.json"
            controller.scene_parser = _SceneParserStub(process_results=[False, False])
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            stop_calls = {"count": 0}
            policy = _attach_ambient_policy(
                controller,
                _AmbientPolicyStub(
                    enabled=True,
                    scene_name="ambient.json",
                    cycle_cleanup="scene_only",
                    restart_results=[True, False],
                    restart_delay=0.0,
                ),
            )

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            outcome = controller._run_scene_logic("ambient.json")

            assert outcome == OUTCOME_NORMAL_END
            assert controller.scene_parser.start_calls == 2
            assert controller.scene_running is False
            assert controller.current_scene_name is None
            assert policy.recorded_outcomes == [OUTCOME_NORMAL_END, OUTCOME_NORMAL_END]
            assert policy.wait_calls == [0.0]
            assert controller.audio_handler.calls == 2
            assert controller.video_handler.calls == 4
            assert controller.actuator_state_store.sources == []
            assert stop_calls["count"] == 0
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_ambient_full_stop_cleanup_runs_between_cycles():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "ambient.json")

            controller = _build_controller(scene_running=True)
            controller.config["startup_mode"] = "ambient"
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "ambient.json"
            controller.scene_parser = _SceneParserStub(process_results=[False, False])
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            stop_calls = {"count": 0}
            policy = _attach_ambient_policy(
                controller,
                _AmbientPolicyStub(
                    enabled=True,
                    scene_name="ambient.json",
                    cycle_cleanup="full_stop",
                    restart_results=[True, False],
                    restart_delay=0.0,
                ),
            )

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            outcome = controller._run_scene_logic("ambient.json")

            assert outcome == OUTCOME_NORMAL_END
            assert controller.scene_parser.start_calls == 2
            assert policy.recorded_outcomes == [OUTCOME_NORMAL_END, OUTCOME_NORMAL_END]
            assert controller.actuator_state_store.sources == [
                "scene_end",
                "scene_end",
            ]
            assert stop_calls["count"] == 2
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_ambient_restart_wait_cancel_stops_loop_after_first_cycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "ambient.json")

            controller = _build_controller(scene_running=True)
            controller.config["startup_mode"] = "ambient"
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "ambient.json"
            controller.scene_parser = _SceneParserStub(process_results=[False, False])
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            policy = _attach_ambient_policy(
                controller,
                _AmbientPolicyStub(
                    enabled=True,
                    scene_name="ambient.json",
                    cycle_cleanup="scene_only",
                    restart_results=[True],
                    restart_delay=2.0,
                    wait_results=[False],
                ),
            )

            outcome = controller._run_scene_logic("ambient.json")

            assert outcome == OUTCOME_NORMAL_END
            assert controller.scene_parser.start_calls == 1
            assert policy.recorded_outcomes == [OUTCOME_NORMAL_END]
            assert policy.wait_calls == [2.0]
            assert controller.scene_running is False
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_ambient_missing_scene_retries_after_error_delay_with_full_cleanup():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file

            controller = _build_controller(scene_running=True)
            controller.config["startup_mode"] = "ambient"
            controller.scenes_dir = tmp_dir
            controller.scene_parser = object()
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            stop_calls = {"count": 0}
            policy = _attach_ambient_policy(
                controller,
                _AmbientPolicyStub(
                    enabled=True,
                    scene_name="missing.json",
                    failure_retry_results=[True, False],
                    restart_delay=12.0,
                ),
            )

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            outcome = controller._run_scene_logic("missing.json")

            assert outcome == OUTCOME_MISSING_SCENE
            assert controller.scene_running is False
            assert controller.current_scene_name is None
            assert policy.recorded_outcomes == [
                OUTCOME_MISSING_SCENE,
                OUTCOME_MISSING_SCENE,
            ]
            assert policy.failure_retry_calls == [
                ("missing.json", OUTCOME_MISSING_SCENE),
                ("missing.json", OUTCOME_MISSING_SCENE),
            ]
            assert policy.wait_calls == [12.0]
            assert controller.audio_handler.calls == 1
            assert controller.video_handler.calls == 1
            assert controller.actuator_state_store.sources == [
                "ambient_recoverable_failure"
            ]
            assert stop_calls["count"] == 1
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_ambient_start_failure_retries_without_duplicate_full_cleanup():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "ambient.json")

            controller = _build_controller(scene_running=True)
            controller.config["startup_mode"] = "ambient"
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "ambient.json"
            controller.scene_parser = _SceneParserStub(start_result=False)
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            stop_calls = {"count": 0}
            policy = _attach_ambient_policy(
                controller,
                _AmbientPolicyStub(
                    enabled=True,
                    scene_name="ambient.json",
                    failure_retry_results=[True, False],
                    restart_delay=3.0,
                ),
            )

            def _broadcast_stop():
                stop_calls["count"] += 1

            controller.broadcast_stop = _broadcast_stop

            outcome = controller._run_scene_logic("ambient.json")

            assert outcome == OUTCOME_START_FAILURE
            assert controller.scene_parser.start_calls == 2
            assert policy.recorded_outcomes == [
                OUTCOME_START_FAILURE,
                OUTCOME_START_FAILURE,
            ]
            assert policy.wait_calls == [3.0]
            assert controller.audio_handler.calls == 2
            assert controller.video_handler.calls == 2
            assert controller.actuator_state_store.sources == [
                "scene_end",
                "scene_end",
            ]
            assert stop_calls["count"] == 2
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


def test_ambient_runtime_error_does_not_retry_in_v1():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "museum_scene_state"
        original_state_file = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            _touch_scene_file(tmp_dir, "ambient.json")

            controller = _build_controller(scene_running=True)
            controller.config["startup_mode"] = "ambient"
            controller.scenes_dir = tmp_dir
            controller.current_scene_name = "ambient.json"
            controller.scene_parser = _SceneParserStub()
            controller.audio_handler = _Counter()
            controller.video_handler = _Counter()
            controller.actuator_state_store = _ActuatorStoreCounter()
            policy = _attach_ambient_policy(
                controller,
                _AmbientPolicyStub(
                    enabled=True,
                    scene_name="ambient.json",
                    failure_retry_results=[True],
                ),
            )

            def _raise_runtime_error():
                raise RuntimeError("boom")

            controller.run_scene = _raise_runtime_error

            outcome = controller._run_scene_logic("ambient.json")

            assert outcome == OUTCOME_ERROR
            assert policy.recorded_outcomes == [OUTCOME_ERROR]
            assert policy.failure_retry_calls == []
            assert policy.wait_calls == []
            assert controller.scene_running is False
        finally:
            main_module._SCENE_STATE_FILE = original_state_file


if __name__ == "__main__":
    print("Running offline P0-2 checks (no pytest required)...")
    tests = [
        ("transition_updates_file_and_is_idempotent", test_transition_updates_file_and_is_idempotent),
        ("stop_scene_is_idempotent", test_stop_scene_is_idempotent),
        ("operator_stop_suspends_ambient_policy_before_full_stop", test_operator_stop_suspends_ambient_policy_before_full_stop),
        ("operator_stop_does_not_suspend_ambient_when_resume_after_delay", test_operator_stop_does_not_suspend_ambient_when_resume_after_delay),
        ("shutdown_signal_requests_ambient_shutdown", test_shutdown_signal_requests_ambient_shutdown),
        ("cleanup_requests_ambient_shutdown_without_operator_suspend", test_cleanup_requests_ambient_shutdown_without_operator_suspend),
        ("start_scene_by_name_returns_real_start_result", test_start_scene_by_name_returns_real_start_result),
        ("missing_scene_broadcasts_status_update", test_missing_scene_broadcasts_status_update),
        ("normal_scene_completion_returns_outcome_and_preserves_full_cleanup", test_normal_scene_completion_returns_outcome_and_preserves_full_cleanup),
        ("scene_load_failure_returns_outcome_without_full_cleanup", test_scene_load_failure_returns_outcome_without_full_cleanup),
        ("scene_start_failure_returns_outcome_and_preserves_full_cleanup", test_scene_start_failure_returns_outcome_and_preserves_full_cleanup),
        ("external_stop_during_processing_returns_outcome_without_duplicate_stop", test_external_stop_during_processing_returns_outcome_without_duplicate_stop),
        ("shutdown_during_processing_returns_outcome_and_preserves_cleanup", test_shutdown_during_processing_returns_outcome_and_preserves_cleanup),
        ("ambient_scene_only_restarts_without_global_stop_between_cycles", test_ambient_scene_only_restarts_without_global_stop_between_cycles),
        ("ambient_full_stop_cleanup_runs_between_cycles", test_ambient_full_stop_cleanup_runs_between_cycles),
        ("ambient_restart_wait_cancel_stops_loop_after_first_cycle", test_ambient_restart_wait_cancel_stops_loop_after_first_cycle),
        ("ambient_missing_scene_retries_after_error_delay_with_full_cleanup", test_ambient_missing_scene_retries_after_error_delay_with_full_cleanup),
        ("ambient_start_failure_retries_without_duplicate_full_cleanup", test_ambient_start_failure_retries_without_duplicate_full_cleanup),
        ("ambient_runtime_error_does_not_retry_in_v1", test_ambient_runtime_error_does_not_retry_in_v1),
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
