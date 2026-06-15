import sys
import types
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

try:
    import paho.mqtt.client  # noqa: F401
except ModuleNotFoundError:
    mqtt_module = types.ModuleType("paho.mqtt.client")

    class _BootstrapClient:
        def __init__(self, *args, **kwargs):
            pass

    mqtt_module.Client = _BootstrapClient
    mqtt_module.CallbackAPIVersion = types.SimpleNamespace(VERSION2=2)
    mqtt_module.MQTT_ERR_SUCCESS = 0

    sys.modules.setdefault("paho", types.ModuleType("paho"))
    sys.modules.setdefault("paho.mqtt", types.ModuleType("paho.mqtt"))
    sys.modules.setdefault("paho.mqtt.client", mqtt_module)

from utils.mqtt.mqtt_client import MQTTClient


class _LoggerStub:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class _FakePahoClient:
    def __init__(self, connect_rc=None, connect_error=None,
                 callback_shape="v2"):
        self.connect_rc = connect_rc
        self.connect_error = connect_error
        self.callback_shape = callback_shape
        self._sock = None
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None
        self.on_publish = None
        self.connect_calls = 0
        self.loop_start_calls = 0
        self.loop_stop_calls = 0
        self.disconnect_calls = 0
        self.subscriptions = []

    def connect(self, _host, _port, _timeout):
        self.connect_calls += 1
        if self.connect_error:
            raise self.connect_error
        self._sock = object()

    def loop_start(self):
        self.loop_start_calls += 1
        if self.connect_rc is not None and self.on_connect:
            if self.callback_shape == "v1":
                self.on_connect(self, None, {}, self.connect_rc)
            else:
                self.on_connect(self, None, {}, self.connect_rc, None)
        return 0

    def loop_stop(self):
        self.loop_stop_calls += 1

    def disconnect(self):
        self.disconnect_calls += 1
        self._sock = None

    def subscribe(self, topic, qos=0):
        self.subscriptions.append((topic, qos))
        return (0, None)


def _mqtt_client(fake_client):
    client = MQTTClient.__new__(MQTTClient)
    client.broker_host = "broker.local"
    client.broker_port = 1883
    client.room_id = "room1"
    client.connected = False
    client.logger = _LoggerStub()
    client.retry_attempts = 1
    client.retry_sleep = 0
    client.connect_timeout = 0.01
    client.reconnect_timeout = 0.01
    client.reconnect_sleep = 0
    client.check_interval = 60
    client.shutdown_requested = False
    client.connection_lost_callback = None
    client.connection_restored_callback = None
    client._network_loop_started = False
    client._last_connect_rc = None
    client._callback_api_version = 2
    client.message_handler = None
    client.feedback_tracker = None
    client.device_registry = None
    client.client = fake_client
    fake_client.on_connect = client._on_connect
    fake_client.on_disconnect = client._on_disconnect
    fake_client.on_message = client._on_message
    fake_client.on_publish = client._on_publish
    return client


def test_connect_timeout_stops_loop_and_disconnects_socket():
    fake_client = _FakePahoClient()
    client = _mqtt_client(fake_client)

    assert client.connect(timeout=0.01) is False

    assert fake_client.loop_start_calls == 1
    assert fake_client.loop_stop_calls == 1
    assert fake_client.disconnect_calls == 1
    assert client.connected is False
    assert client._network_loop_started is False


def test_refused_connect_stops_loop_and_disconnects_socket():
    fake_client = _FakePahoClient(connect_rc=5)
    client = _mqtt_client(fake_client)

    assert client.connect(timeout=1) is False

    assert fake_client.loop_start_calls == 1
    assert fake_client.loop_stop_calls == 1
    assert fake_client.disconnect_calls == 1
    assert fake_client.subscriptions == []
    assert client.connected is False
    assert client._network_loop_started is False


def test_connect_exception_disconnects_socket_without_stopping_unstarted_loop():
    fake_client = _FakePahoClient(connect_error=RuntimeError("boom"))
    client = _mqtt_client(fake_client)

    assert client.connect(timeout=1) is False

    assert fake_client.loop_start_calls == 0
    assert fake_client.loop_stop_calls == 0
    assert fake_client.disconnect_calls == 1
    assert client.connected is False
    assert client._network_loop_started is False


def test_successful_connect_keeps_network_loop_running():
    fake_client = _FakePahoClient(connect_rc=0)
    client = _mqtt_client(fake_client)

    assert client.connect(timeout=1) is True

    assert fake_client.loop_start_calls == 1
    assert fake_client.loop_stop_calls == 0
    assert fake_client.disconnect_calls == 0
    assert fake_client.subscriptions
    assert client.connected is True
    assert client._network_loop_started is True


def test_legacy_disconnect_callback_shape_is_still_accepted():
    fake_client = _FakePahoClient(connect_rc=0)
    client = _mqtt_client(fake_client)
    lost_events = []
    client.set_connection_callbacks(lost_callback=lambda: lost_events.append(True))
    client.connected = True

    client._on_disconnect(fake_client, None, 7)

    assert client.connected is False
    assert lost_events == [True]


def test_legacy_connect_callback_shape_is_still_accepted():
    fake_client = _FakePahoClient(connect_rc=0, callback_shape="v1")
    client = _mqtt_client(fake_client)

    assert client.connect(timeout=1) is True

    assert fake_client.loop_start_calls == 1
    assert fake_client.loop_stop_calls == 0
    assert client.connected is True
