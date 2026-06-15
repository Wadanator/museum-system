import threading

from Web.dashboard import WebDashboard


class _SocketIOStub:
    def __init__(self, fail_emit=False):
        self.fail_emit = fail_emit
        self.emitted = []

    def emit(self, event, payload, to=None, namespace=None):
        if self.fail_emit:
            raise RuntimeError("socket is slow/broken")
        self.emitted.append({
            "event": event,
            "payload": payload,
            "to": to,
            "namespace": namespace,
        })


class _ControllerStub:
    room_id = "room1"
    scene_running = False
    current_scene_name = None
    current_scene_state = None
    mqtt_client = None
    config = {}


def _dashboard_for_log_fanout(queue_limit=500, fail_emit=False):
    dashboard = WebDashboard.__new__(WebDashboard)
    dashboard.controller = _ControllerStub()
    dashboard.socketio = _SocketIOStub(fail_emit=fail_emit)
    dashboard.log_buffer = []
    dashboard._connected_sids = {"sid-1"}
    dashboard._sids_lock = threading.Lock()
    dashboard.LOG_FANOUT_QUEUE_LIMIT = queue_limit
    dashboard.LOG_FANOUT_DROP_WARNING_INTERVAL_SECONDS = 0
    dashboard._setup_log_fanout(start_worker=False)
    return dashboard


def _log_entry(message="runtime log"):
    return {
        "timestamp": "2026-06-15 12:00:00.000",
        "level": "INFO",
        "module": "test",
        "message": message,
    }


def test_add_log_entry_queues_without_synchronous_websocket_emit():
    dashboard = _dashboard_for_log_fanout()
    entry = _log_entry()

    dashboard.add_log_entry(entry)

    assert dashboard.get_log_history() == [entry]
    assert dashboard._log_fanout_queue.qsize() == 1
    assert dashboard.socketio.emitted == []


def test_log_fanout_worker_drain_sends_new_log_event():
    dashboard = _dashboard_for_log_fanout()
    entry = _log_entry()

    dashboard.add_log_entry(entry)

    assert dashboard._drain_log_fanout_once(timeout=0) is True
    assert dashboard.socketio.emitted == [{
        "event": "new_log",
        "payload": entry,
        "to": "sid-1",
        "namespace": "/",
    }]


def test_full_log_fanout_queue_drops_websocket_event_without_blocking():
    dashboard = _dashboard_for_log_fanout(queue_limit=1)
    first = _log_entry("first")
    second = _log_entry("second")

    dashboard.add_log_entry(first)
    dashboard.add_log_entry(second)

    history = dashboard.get_log_history()
    assert first in history
    assert second in history
    assert any(
        log["level"] == "WARNING"
        and "Dashboard log websocket queue full" in log["message"]
        for log in history
    )
    assert dashboard._log_fanout_queue.qsize() == 1
    assert dashboard.socketio.emitted == []


def test_log_fanout_emit_error_does_not_escape_worker_drain():
    dashboard = _dashboard_for_log_fanout(fail_emit=True)

    dashboard.add_log_entry(_log_entry())

    assert dashboard._drain_log_fanout_once(timeout=0) is True
    assert dashboard.socketio.emitted == []
