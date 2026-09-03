import sys
import time
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from utils.display_power_manager import DisplayPowerManager


class _Logger:
    def __init__(self):
        self.records = []

    def _record(self, level, *args):
        self.records.append((level, " ".join(str(arg) for arg in args)))

    def debug(self, *args, **_kwargs):
        self._record("debug", *args)

    def info(self, *args, **_kwargs):
        self._record("info", *args)

    def warning(self, *args, **_kwargs):
        self._record("warning", *args)

    def error(self, *args, **_kwargs):
        self._record("error", *args)


class _Backend:
    name = "fake"

    def __init__(self, fail_on=None):
        self.commands = []
        self.fail_on = fail_on

    def power_on(self):
        self.commands.append("on")
        if self.fail_on == "on":
            raise RuntimeError("boom")
        return True

    def standby(self):
        self.commands.append("standby")
        if self.fail_on == "standby":
            raise RuntimeError("boom")
        return True


def _manager(backend=None, idle_timeout_seconds=0.0):
    return DisplayPowerManager(
        enabled=True,
        backend=backend or _Backend(),
        idle_timeout_seconds=idle_timeout_seconds,
        min_seconds_between_power_commands=0.0,
        async_commands=False,
        logger=_Logger(),
    )


def test_request_on_sends_on_once_for_repeated_reason():
    backend = _Backend()
    manager = _manager(backend)

    assert manager.request_on("scene_video") is True
    assert manager.request_on("scene_video") is True

    assert backend.commands == ["on"]
    assert manager.get_status()["active_reasons"] == ["scene_video"]


def test_release_last_reason_sends_standby_after_idle_timeout():
    backend = _Backend()
    manager = _manager(backend, idle_timeout_seconds=0.02)

    manager.request_on("scene_video")
    manager.release("scene_video")
    time.sleep(0.08)

    assert backend.commands == ["on", "standby"]
    assert manager.get_status()["active_reasons"] == []


def test_request_on_cancels_pending_standby():
    backend = _Backend()
    manager = _manager(backend, idle_timeout_seconds=0.05)

    manager.request_on("scene_video")
    manager.release("scene_video")
    assert manager.get_status()["pending_standby_at"] is not None

    manager.request_on("scene_video")
    time.sleep(0.08)

    assert backend.commands == ["on", "on"]
    assert "standby" not in backend.commands
    assert manager.get_status()["pending_standby_at"] is None


def test_force_standby_clears_reasons_and_sends_standby():
    backend = _Backend()
    manager = _manager(backend)

    manager.request_on("scene_video")
    manager.force_standby("mqtt_manual")

    assert backend.commands == ["on", "standby"]
    assert manager.get_status()["active_reasons"] == []


def test_backend_exception_is_recorded_without_raising():
    backend = _Backend(fail_on="on")
    manager = _manager(backend)

    assert manager.request_on("scene_video") is True

    status = manager.get_status()
    assert backend.commands == ["on"]
    assert status["last_result"] is False
    assert "boom" in status["last_error"]
