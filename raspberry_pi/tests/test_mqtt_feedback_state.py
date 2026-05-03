import sys
import types
from pathlib import Path

# Ensure raspberry_pi/ is importable when tests are executed from repository root.
RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

try:
    import paho.mqtt.client  # noqa: F401
except ModuleNotFoundError:
    # These tests do not instantiate MQTTClient, but utils.mqtt.__init__ imports it.
    sys.modules.setdefault("paho", types.ModuleType("paho"))
    sys.modules.setdefault("paho.mqtt", types.ModuleType("paho.mqtt"))
    sys.modules.setdefault("paho.mqtt.client", types.ModuleType("paho.mqtt.client"))

from utils.mqtt.mqtt_actuator_state_store import MQTTActuatorStateStore
from utils.mqtt.mqtt_feedback_tracker import MQTTFeedbackTracker


class _LoggerStub:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


def _build_tracker(timeout=30):
    logger = _LoggerStub()
    store = MQTTActuatorStateStore(logger=logger)
    tracker = MQTTFeedbackTracker(logger=logger, feedback_timeout=timeout)
    tracker.set_state_store(store)
    tracker.enable_feedback_tracking()
    return tracker, store


def _publish_and_feedback(tracker, topic, command, feedback_payload):
    tracker.track_published_message(topic, command)
    tracker.handle_feedback_message(f"{topic}/feedback", feedback_payload)


def test_ok_feedback_confirms_original_motor_command():
    tracker, store = _build_tracker()

    _publish_and_feedback(tracker, "room1/motor1", "ON:70:L:1000", "OK")

    state = store.get_state("room1/motor1")
    assert state["desired_state"] == "ON"
    assert state["confirmed_state"] == "ON"
    assert state["motor_direction"] == "LEFT"
    assert state["motor_speed"] == 70
    assert tracker.pending_feedbacks == {}


def test_active_feedback_confirms_effect_on_from_payload():
    tracker, store = _build_tracker()

    _publish_and_feedback(tracker, "room1/effects/group1", "PULSE", "ACTIVE")

    state = store.get_state("room1/effects/group1")
    assert state["desired_state"] is None
    assert state["confirmed_state"] == "ON"
    assert tracker.pending_feedbacks == {}


def test_inactive_feedback_confirms_effect_off_from_payload():
    tracker, store = _build_tracker()

    _publish_and_feedback(tracker, "room1/effects/group1", "PULSE", "INACTIVE")

    state = store.get_state("room1/effects/group1")
    assert state["desired_state"] is None
    assert state["confirmed_state"] == "OFF"
    assert state["motor_speed"] == 0
    assert tracker.pending_feedbacks == {}


def test_state_feedback_is_case_and_whitespace_insensitive():
    tracker, store = _build_tracker()

    _publish_and_feedback(tracker, "room1/effects/alone", "PULSE", " active ")

    state = store.get_state("room1/effects/alone")
    assert state["confirmed_state"] == "ON"
    assert tracker.pending_feedbacks == {}


def test_error_feedback_does_not_confirm_state():
    tracker, store = _build_tracker()

    _publish_and_feedback(tracker, "room1/light/1", "ON", "ERROR")

    state = store.get_state("room1/light/1")
    assert state["desired_state"] == "ON"
    assert state["confirmed_state"] == "UNKNOWN"
    assert tracker.pending_feedbacks == {}


if __name__ == "__main__":
    tests = [
        (
            "ok_feedback_confirms_original_motor_command",
            test_ok_feedback_confirms_original_motor_command,
        ),
        (
            "active_feedback_confirms_effect_on_from_payload",
            test_active_feedback_confirms_effect_on_from_payload,
        ),
        (
            "inactive_feedback_confirms_effect_off_from_payload",
            test_inactive_feedback_confirms_effect_off_from_payload,
        ),
        (
            "state_feedback_is_case_and_whitespace_insensitive",
            test_state_feedback_is_case_and_whitespace_insensitive,
        ),
        (
            "error_feedback_does_not_confirm_state",
            test_error_feedback_does_not_confirm_state,
        ),
    ]

    print("Running offline MQTT feedback state tests (no pytest required)...")
    failed = 0

    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {name}: {exc}")

    if failed:
        print(f"Offline tests failed: {failed}/{len(tests)}")
        raise SystemExit(1)

    print(f"Offline tests passed: {len(tests)}/{len(tests)}")
