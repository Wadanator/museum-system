import threading
from pathlib import Path
import sys

# Ensure raspberry_pi/ is importable when tests are executed from repository root.
RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from main import MuseumController
from utils.mqtt.mqtt_device_registry import MQTTDeviceRegistry
from Web.dashboard import WebDashboard


class _ActuatorStoreStub:
    def __init__(self):
        self.marked = []

    def mark_node_offline(self, device_id):
        self.marked.append(device_id)


class _RegistryStub:
    def __init__(self, connected_devices):
        self.connected_devices = connected_devices
        self.cleanup_args = []

    def get_connected_devices(self, cleanup=True):
        self.cleanup_args.append(cleanup)
        return self.connected_devices


class _SocketIOStub:
    def __init__(self):
        self.emitted = []

    def emit(self, event, payload, to=None, namespace=None):
        self.emitted.append({
            'event': event,
            'payload': payload,
            'to': to,
            'namespace': namespace,
        })


class _ControllerStub:
    def __init__(self, mqtt_client, mqtt_device_registry, room_id='room1'):
        self.mqtt_client = mqtt_client
        self.mqtt_device_registry = mqtt_device_registry
        self.scene_running = False
        self.room_id = room_id
        self.start_time = 0.0


class _MQTTClientStub:
    def __init__(self, connected=True):
        self._connected = connected

    def is_connected(self):
        return self._connected


def test_device_status_change_broadcasts_existing_stats_flow():
    controller = MuseumController.__new__(MuseumController)
    controller.actuator_state_store = _ActuatorStoreStub()
    controller.web_dashboard = type('WebStub', (), {})()
    controller.web_dashboard.calls = 0

    def _broadcast_stats():
        controller.web_dashboard.calls += 1

    controller.web_dashboard.broadcast_stats = _broadcast_stats

    controller._on_device_status_change('node-1', 'offline')

    assert controller.actuator_state_store.marked == ['node-1']
    assert controller.web_dashboard.calls == 1


def test_broadcast_stats_refreshes_connected_devices_without_reentrant_cleanup():
    socketio = _SocketIOStub()
    registry = _RegistryStub({'node-1': {'status': 'online', 'last_updated': 123.0}})
    controller = _ControllerStub(_MQTTClientStub(), registry)

    dashboard = WebDashboard.__new__(WebDashboard)
    dashboard.controller = controller
    dashboard.socketio = socketio
    dashboard.log = type('LogStub', (), {'error': lambda self, msg: None})()
    dashboard._connected_sids = {'sid-1'}
    dashboard._sids_lock = threading.Lock()
    dashboard.stats = {
        'total_scenes_played': 0,
        'scene_play_counts': {},
        'total_uptime': 0,
        'last_start_time': 1.0,
        'connected_devices': {},
    }

    dashboard.broadcast_stats()

    assert registry.cleanup_args == [False]
    assert dashboard.stats['connected_devices'] == {'node-1': {'status': 'online', 'last_updated': 123.0}}
    assert socketio.emitted[-1]['event'] == 'stats_update'
    assert socketio.emitted[-1]['payload']['connected_devices'] == {'node-1': {'status': 'online', 'last_updated': 123.0}}


def test_device_registry_cleanup_notifies_offline_listener_with_literal_offline():
    registry = MQTTDeviceRegistry()
    calls = []

    registry.on_status_change = lambda device_id, status: calls.append((device_id, status))
    registry.connected_devices['node-1'] = {
        'status': 'online',
        'last_updated': 0.0,
    }
    registry.device_timeout = 0

    registry.cleanup_stale_devices()

    assert calls == [('node-1', 'offline')]


if __name__ == '__main__':
    tests = [
        (
            'device_status_change_broadcasts_existing_stats_flow',
            test_device_status_change_broadcasts_existing_stats_flow,
        ),
        (
            'broadcast_stats_refreshes_connected_devices_without_reentrant_cleanup',
            test_broadcast_stats_refreshes_connected_devices_without_reentrant_cleanup,
        ),
        (
            'device_registry_cleanup_notifies_offline_listener_with_literal_offline',
            test_device_registry_cleanup_notifies_offline_listener_with_literal_offline,
        ),
    ]

    print('Running offline device-status broadcast tests (no pytest required)...')
    failed = 0

    for name, fn in tests:
        try:
            fn()
            print(f'[PASS] {name}')
        except Exception as exc:
            failed += 1
            print(f'[FAIL] {name}: {exc}')

    if failed:
        print(f'Offline tests failed: {failed}/{len(tests)}')
        raise SystemExit(1)

    print(f'Offline tests passed: {len(tests)}/{len(tests)}')