import sys
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

import main as main_module
from Web.dashboard import WebDashboard
from Web.routes.status import _get_current_status_data


class _MqttStub:
    def is_connected(self):
        return True


class _AmbientStub:
    def __init__(self):
        self.calls = 0

    def get_status(self):
        self.calls += 1
        return {
            "enabled": False,
            "scene": "SceneV01.json",
            "suspended": False,
            "start_policy": "after_initial_connection_attempt",
            "cycle_cleanup": "scene_only",
            "next_restart_at": None,
            "last_outcome": "never_started",
        }


class _ControllerStub:
    def __init__(self):
        self.room_id = "room1"
        self.scene_running = False
        self.current_scene_name = None
        self.current_scene_state = None
        self.mqtt_client = _MqttStub()
        self.config = {
            "startup_mode": "classic",
            "json_file_name": "SceneV01.json",
        }
        self.ambient = _AmbientStub()

    def _ambient_loop_service(self):
        return self.ambient


def test_main_lazy_ambient_loop_service_reports_classic_status():
    controller = main_module.MuseumController.__new__(main_module.MuseumController)
    controller.config = {
        "startup_mode": "classic",
        "json_file_name": "SceneV01.json",
    }
    controller.shutdown_requested = False

    service = controller._ambient_loop_service()

    assert controller._ambient_loop_service() is service
    assert service.get_status() == {
        "enabled": False,
        "scene": "SceneV01.json",
        "suspended": False,
        "start_policy": "after_initial_connection_attempt",
        "cycle_cleanup": "scene_only",
        "next_restart_at": None,
        "last_outcome": "never_started",
    }


def test_rest_status_payload_includes_startup_and_ambient_status():
    controller = _ControllerStub()

    status = _get_current_status_data(controller)

    assert status["startup_mode"] == "classic"
    assert status["default_scene"] == "SceneV01.json"
    assert status["ambient"]["enabled"] is False
    assert status["ambient"]["scene"] == "SceneV01.json"
    assert status["ambient"]["last_outcome"] == "never_started"
    assert controller.ambient.calls == 1


def test_dashboard_status_and_runtime_snapshot_include_ambient_status():
    controller = _ControllerStub()
    dashboard = WebDashboard.__new__(WebDashboard)
    dashboard.controller = controller
    dashboard.log_buffer = []
    dashboard.get_uptime = lambda: 12.5
    dashboard.get_device_runtime_states = lambda: []

    class _Log:
        def error(self, *args, **kwargs):
            pass

    dashboard.log = _Log()

    status = dashboard._get_status_data()
    snapshot = dashboard.get_runtime_snapshot()

    assert status["startup_mode"] == "classic"
    assert status["default_scene"] == "SceneV01.json"
    assert status["ambient"]["scene"] == "SceneV01.json"
    assert status["ambient"]["next_restart_at"] is None
    assert snapshot["status"]["default_scene"] == "SceneV01.json"
    assert snapshot["status"]["ambient"]["last_outcome"] == "never_started"
