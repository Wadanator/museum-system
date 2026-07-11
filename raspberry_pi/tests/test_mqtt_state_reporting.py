import sys
import types
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

try:
    import paho.mqtt.client  # noqa: F401
except ModuleNotFoundError:
    sys.modules.setdefault("paho", types.ModuleType("paho"))
    sys.modules.setdefault("paho.mqtt", types.ModuleType("paho.mqtt"))
    sys.modules.setdefault("paho.mqtt.client", types.ModuleType("paho.mqtt.client"))

from utils.mqtt.mqtt_actuator_state_store import MQTTActuatorStateStore
from utils.mqtt.mqtt_feedback_tracker import MQTTFeedbackTracker
from utils.mqtt.mqtt_message_handler import MQTTMessageHandler
from utils.mqtt.mqtt_device_registry import MQTTDeviceRegistry
from utils.mqtt.topic_rules import MQTTTopicRules


class _LoggerStub:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class _Message:
    def __init__(self, topic, payload, retain=False):
        self.topic = topic
        self.payload = payload.encode("utf-8")
        self.retain = retain


class _SceneParserStub:
    def __init__(self):
        self.events = []

    def register_mqtt_event(self, topic, payload):
        self.events.append((topic, payload))


def _devices_config():
    return {
        "motors": [
            {
                "id": "motor1",
                "name": "Motor 1",
                "topic": "room1/motor1",
                "node_id": "Room1_ESP_Motory",
            }
        ],
        "relays": [
            {
                "id": "light_1",
                "name": "Light 1",
                "topic": "room1/light/1",
                "node_id": "Room1_Relays_Ctrl",
            }
        ],
        "windows": [
            {
                "id": "window_left",
                "name": "Window Left",
                "type": "window",
                "topic": "room1/window/left",
                "node_id": "Room1_Window_Ctrl",
            }
        ],
    }


def _store():
    store = MQTTActuatorStateStore(logger=_LoggerStub())
    store.initialize_from_devices_config(_devices_config())
    return store


def test_state_topic_helpers_strip_and_create_suffix():
    assert MQTTTopicRules.is_state_topic("room1/light/1/state")
    assert (
        MQTTTopicRules.original_topic_from_state("room1/light/1/state")
        == "room1/light/1"
    )
    assert (
        MQTTTopicRules.state_topic_for_command("room1/light/1")
        == "room1/light/1/state"
    )


def test_store_bootstrap_starts_configured_outputs_stale_unknown():
    store = _store()

    state = store.get_state("room1/light/1")
    motor_state = store.get_state("room1/motor1")
    window_state = store.get_state("room1/window/left")

    assert state["node_id"] == "Room1_Relays_Ctrl"
    assert state["device_type"] == "relay"
    assert state["confirmed_state"] == "UNKNOWN"
    assert state["stale"] is True
    assert motor_state["device_type"] == "motor"
    assert window_state["device_type"] == "window"


def test_retained_state_without_online_keeps_live_state_stale_unknown():
    store = _store()

    store.update_reported_state(
        "room1/light/1",
        "ON",
        node_id="Room1_Relays_Ctrl",
        node_online=False,
        retained=True,
    )
    state = store.get_state("room1/light/1")

    assert state["reported_state"] == "ON"
    assert state["confirmed_state"] == "UNKNOWN"
    assert state["stale"] is True
    assert state["state_retained"] is True


def test_online_plus_existing_state_report_clears_stale():
    store = _store()
    store.update_reported_state(
        "room1/light/1",
        "ON",
        node_id="Room1_Relays_Ctrl",
        node_online=False,
        retained=True,
    )

    store.mark_node_online("Room1_Relays_Ctrl")
    state = store.get_state("room1/light/1")

    assert state["confirmed_state"] == "ON"
    assert state["stale"] is False


def test_desired_and_feedback_do_not_clear_stale_for_bootstrapped_node():
    store = _store()
    tracker = MQTTFeedbackTracker(logger=_LoggerStub(), feedback_timeout=30)
    tracker.set_state_store(store)
    tracker.enable_feedback_tracking()

    tracker.track_published_message("room1/light/1", "ON")
    tracker.handle_feedback_message("room1/light/1/feedback", "OK")
    state = store.get_state("room1/light/1")

    assert state["desired_state"] == "ON"
    assert state["confirmed_state"] == "ON"
    assert state["stale"] is True


def test_force_all_off_keeps_stale_node_unknown():
    store = _store()

    store.force_all_off(source="pytest")
    state = store.get_state("room1/light/1")

    assert state["desired_state"] == "OFF"
    assert state["confirmed_state"] == "UNKNOWN"
    assert state["stale"] is True


def test_message_handler_routes_state_report_before_scene_parser():
    store = _store()
    registry = MQTTDeviceRegistry(logger=_LoggerStub(), device_timeout=30)
    registry.update_device_status("Room1_Relays_Ctrl", "online")
    scene_parser = _SceneParserStub()
    handler = MQTTMessageHandler(logger=_LoggerStub(), room_id="room1")
    handler.set_handlers(
        device_registry=registry,
        actuator_state_store=store,
        scene_parser=scene_parser,
    )

    handler.handle_message(_Message("room1/light/1/state", "ON", retain=True))
    state = store.get_state("room1/light/1")

    assert scene_parser.events == []
    assert state["topic"] == "room1/light/1"
    assert state["confirmed_state"] == "ON"
    assert state["stale"] is False


def test_online_state_report_clears_stale_desired_state():
    store = _store()
    store.mark_node_online("Room1_Relays_Ctrl")

    store.update_desired("room1/light/1", "ON")
    store.update_reported_state(
        "room1/light/1",
        "OFF",
        node_id="Room1_Relays_Ctrl",
        node_online=True,
    )
    state = store.get_state("room1/light/1")

    assert state["desired_state"] is None
    assert state["confirmed_state"] == "OFF"
    assert state["reported_state"] == "OFF"
    assert state["stale"] is False


def test_online_after_retained_state_report_clears_stale_desired_state():
    store = _store()

    store.update_desired("room1/light/1", "ON")
    store.update_reported_state(
        "room1/light/1",
        "OFF",
        node_id="Room1_Relays_Ctrl",
        node_online=False,
        retained=True,
    )
    store.mark_node_online("Room1_Relays_Ctrl")
    state = store.get_state("room1/light/1")

    assert state["desired_state"] is None
    assert state["confirmed_state"] == "OFF"
    assert state["reported_state"] == "OFF"
    assert state["stale"] is False


def test_window_json_state_report_uses_window_states_and_speed():
    store = _store()
    registry = MQTTDeviceRegistry(logger=_LoggerStub(), device_timeout=30)
    registry.update_device_status("Room1_Window_Ctrl", "online")
    handler = MQTTMessageHandler(logger=_LoggerStub(), room_id="room1")
    handler.set_handlers(device_registry=registry, actuator_state_store=store)

    handler.handle_message(_Message(
        "room1/window/left/state",
        '{"state":"OPENING","direction":"OPENING","speed":30,"node_id":"Room1_Window_Ctrl"}',
    ))
    state = store.get_state("room1/window/left")

    assert state["device_type"] == "window"
    assert state["confirmed_state"] == "OPENING"
    assert state["reported_state"] == "OPENING"
    assert state["motor_direction"] == "OPENING"
    assert state["motor_speed"] == 30
    assert state["stale"] is False


def test_window_command_payload_sets_speed_and_stop_state():
    store = _store()

    store.update_desired("room1/window/left", "OPEN:30")
    state = store.get_state("room1/window/left")

    assert state["desired_state"] == "OPENING"
    assert state["motor_direction"] == "OPENING"
    assert state["motor_speed"] == 30

    store.update_confirmed("room1/window/left", "STOP")
    state = store.get_state("room1/window/left")

    assert state["confirmed_state"] == "STOPPED"
    assert state["motor_direction"] is None
    assert state["motor_speed"] == 0


def test_force_all_off_maps_windows_to_stopped():
    store = _store()
    store.update_reported_state(
        "room1/window/left",
        '{"state":"OPENING","speed":30,"node_id":"Room1_Window_Ctrl"}',
        node_id="Room1_Window_Ctrl",
        node_online=True,
    )

    store.force_all_off(source="pytest")
    state = store.get_state("room1/window/left")

    assert state["desired_state"] == "STOPPED"
    assert state["confirmed_state"] == "STOPPED"
    assert state["reported_state"] == "STOPPED"

