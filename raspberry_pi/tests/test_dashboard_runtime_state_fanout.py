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


def _dashboard_for_runtime_state_fanout(queue_limit=500, fail_emit=False):
    dashboard = WebDashboard.__new__(WebDashboard)
    dashboard.controller = _ControllerStub()
    dashboard.socketio = _SocketIOStub(fail_emit=fail_emit)
    dashboard.log_buffer = []
    dashboard._connected_sids = {"sid-1"}
    dashboard._sids_lock = threading.Lock()
    dashboard.LOG_FANOUT_QUEUE_LIMIT = 500
    dashboard.LOG_FANOUT_DROP_WARNING_INTERVAL_SECONDS = 0
    dashboard.RUNTIME_STATE_FANOUT_QUEUE_LIMIT = queue_limit
    dashboard.RUNTIME_STATE_FANOUT_DROP_WARNING_INTERVAL_SECONDS = 0
    dashboard._setup_log_fanout(start_worker=False)
    dashboard._setup_runtime_state_fanout(start_worker=False)
    return dashboard


def _state(topic="room1/light/1", confirmed_state="ON"):
    return {
        "topic": topic,
        "confirmed_state": confirmed_state,
        "desired_state": confirmed_state,
    }


def test_runtime_state_update_queues_without_synchronous_websocket_emit():
    dashboard = _dashboard_for_runtime_state_fanout()
    state = _state()

    dashboard.broadcast_device_runtime_state(state)

    assert dashboard._runtime_state_fanout_queue.qsize() == 1
    assert dashboard.socketio.emitted == []


def test_runtime_state_fanout_worker_sends_device_update_event():
    dashboard = _dashboard_for_runtime_state_fanout()
    state = _state()

    dashboard.broadcast_device_runtime_state(state)

    assert dashboard._drain_runtime_state_fanout_once(timeout=0) is True
    assert dashboard.socketio.emitted == [{
        "event": "device_runtime_state_update",
        "payload": state,
        "to": "sid-1",
        "namespace": "/",
    }]


def test_runtime_state_worker_coalesces_same_topic_to_latest_update():
    dashboard = _dashboard_for_runtime_state_fanout()

    dashboard.broadcast_device_runtime_state(_state(confirmed_state="ON"))
    dashboard.broadcast_device_runtime_state(_state(confirmed_state="OFF"))
    dashboard.broadcast_device_runtime_state(_state(confirmed_state="UNKNOWN"))

    assert dashboard._drain_runtime_state_fanout_once(timeout=0) is True
    assert dashboard.socketio.emitted == [{
        "event": "device_runtime_state_update",
        "payload": _state(confirmed_state="UNKNOWN"),
        "to": "sid-1",
        "namespace": "/",
    }]


def test_full_runtime_state_queue_drops_oldest_without_blocking():
    dashboard = _dashboard_for_runtime_state_fanout(queue_limit=1)
    first = _state("room1/light/1", "ON")
    second = _state("room1/light/2", "OFF")

    dashboard.broadcast_device_runtime_state(first)
    dashboard.broadcast_device_runtime_state(second)

    assert dashboard._runtime_state_fanout_queue.qsize() == 1
    assert dashboard._drain_runtime_state_fanout_once(timeout=0) is True
    assert dashboard.socketio.emitted == [{
        "event": "device_runtime_state_update",
        "payload": second,
        "to": "sid-1",
        "namespace": "/",
    }]
    assert any(
        log["level"] == "WARNING"
        and "Dashboard runtime-state websocket queue full" in log["message"]
        for log in dashboard.get_log_history()
    )


def test_runtime_state_emit_error_does_not_escape_worker_drain():
    dashboard = _dashboard_for_runtime_state_fanout(fail_emit=True)

    dashboard.broadcast_device_runtime_state(_state())

    assert dashboard._drain_runtime_state_fanout_once(timeout=0) is True
    assert dashboard.socketio.emitted == []
