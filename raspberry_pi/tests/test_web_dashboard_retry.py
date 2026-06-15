import threading
import sys
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from Web.app import _run_dashboard_with_retries
from Web.dashboard import WebDashboard


class _FakeSocketIO:
    def __init__(self, error):
        self.error = error
        self.run_calls = 0

    def run(self, *args, **kwargs):
        self.run_calls += 1
        raise self.error


class _FakeDashboard:
    def __init__(self):
        self.controller = None
        self.statuses = []

    def set_web_server_status(self, state, **kwargs):
        self.statuses.append((state, kwargs))


class _ListLogger:
    def __init__(self):
        self.debugs = []
        self.errors = []
        self.warnings = []

    def debug(self, message, *args, **kwargs):
        self.debugs.append(message % args if args else message)

    def error(self, message, *args, **kwargs):
        self.errors.append(message % args if args else message)

    def warning(self, message, *args, **kwargs):
        self.warnings.append(message % args if args else message)


def test_dashboard_retry_enters_degraded_after_fast_retry_budget():
    socketio = _FakeSocketIO(OSError("port busy"))
    dashboard = _FakeDashboard()
    logger = _ListLogger()
    stop_event = threading.Event()
    sleep_calls = []

    def _sleep(delay):
        sleep_calls.append(delay)
        if len(sleep_calls) >= 4:
            stop_event.set()

    _run_dashboard_with_retries(
        object(),
        socketio,
        dashboard,
        5000,
        logger,
        sleep_func=_sleep,
        stop_event=stop_event,
    )

    retry_statuses = [
        status for status in dashboard.statuses if status[0] == "retrying"
    ]
    degraded_statuses = [
        status for status in dashboard.statuses if status[0] == "degraded"
    ]

    assert socketio.run_calls == 4
    assert sleep_calls == [2, 4, 8, 300]
    assert len(retry_statuses) == 3
    assert len(degraded_statuses) == 1
    assert degraded_statuses[0][1]["failed_starts"] == 4
    assert degraded_statuses[0][1]["next_retry_seconds"] == 300
    assert any(
        "Web dashboard degraded after 4 failed starts" in msg
        for msg in logger.errors
    )


def test_web_dashboard_status_helpers_store_diagnostic_snapshot():
    dashboard = WebDashboard.__new__(WebDashboard)
    dashboard._web_server_status_lock = threading.Lock()
    dashboard._web_server_status = {}

    dashboard.set_web_server_status(
        "degraded",
        last_error=RuntimeError("bind failed"),
        failed_starts=4,
        next_retry_seconds=300,
    )

    status = dashboard.get_web_server_status()
    assert status["state"] == "degraded"
    assert status["last_error"] == "bind failed"
    assert status["failed_starts"] == 4
    assert status["next_retry_seconds"] == 300
    assert status["last_changed"] > 0


def test_dashboard_retry_does_not_log_crash_during_controller_shutdown():
    controller = type(
        "Controller",
        (),
        {"shutdown_requested": False, "_cleaned_up": False},
    )()
    socketio = _FakeSocketIO(RuntimeError("server closed"))
    dashboard = _FakeDashboard()
    dashboard.controller = controller
    logger = _ListLogger()
    sleep_calls = []

    def _sleep(delay):
        sleep_calls.append(delay)

    original_run = socketio.run

    def _shutdown_then_raise(*args, **kwargs):
        controller.shutdown_requested = True
        return original_run(*args, **kwargs)

    socketio.run = _shutdown_then_raise

    _run_dashboard_with_retries(
        object(),
        socketio,
        dashboard,
        5000,
        logger,
        sleep_func=_sleep,
    )

    assert socketio.run_calls == 1
    assert sleep_calls == []
    assert logger.errors == []
    assert all(status[0] != "degraded" for status in dashboard.statuses)
