#!/usr/bin/env python3
"""
MQTT contract helpers for topic/payload validation.

Goal: keep existing scene/message formats working while adding a single,
central place for MQTT action validation.
"""

import re
from typing import Optional, Tuple


# Topic patterns used by current scenes/firmware.
ROOM_PREFIX_RE = re.compile(r"^room[\w-]+")
DEVICE_STATUS_RE = re.compile(r"^devices/[^/]+/status$")
ROOM_FEEDBACK_RE = re.compile(r"^room[\w-]+/[^/]+(?:/[^/]+)*/feedback$")
ROOM_SCENE_RE = re.compile(r"^room[\w-]+/scene$")
ROOM_START_SCENE_RE = re.compile(r"^room[\w-]+/start_scene$")

ROOM_LIGHT_RE = re.compile(r"^room[\w-]+/light(?:/[^/]+)?$")
ROOM_MOTOR_RE = re.compile(r"^room[\w-]+/motor(?:\d+)?$")
ROOM_EFFECTS_RE = re.compile(r"^room[\w-]+/effects?(?:/[^/]+)?$")
ROOM_EMERGENCY_RE = re.compile(r"^room[\w-]+/emergency$")

# Namespaces where typos are risky and should not silently pass as room_generic.
RESERVED_ROOM_NAMESPACES = ("light", "motor", "effect", "effects", "scene", "start_scene", "emergency")


ON_OFF_RE = re.compile(r"^(ON|OFF)$", re.IGNORECASE)
SPEED_RE = re.compile(r"^SPEED:\d{1,3}$", re.IGNORECASE)
MOTOR_ON_COMPLEX_RE = re.compile(r"^ON:\d{1,3}:[LR](?::\d+)?$", re.IGNORECASE)


def classify_topic(topic: str) -> str:
    """Classify topic into known buckets. Returns 'unknown' for unmatched topics."""
    if not isinstance(topic, str) or not topic:
        return "invalid"

    if DEVICE_STATUS_RE.match(topic):
        return "device_status"
    if ROOM_FEEDBACK_RE.match(topic):
        return "feedback"
    if ROOM_SCENE_RE.match(topic):
        return "scene_start"
    if ROOM_START_SCENE_RE.match(topic):
        return "named_scene"
    if ROOM_MOTOR_RE.match(topic):
        return "motor"
    if ROOM_LIGHT_RE.match(topic):
        return "light"
    if ROOM_EFFECTS_RE.match(topic):
        return "effects"
    if ROOM_EMERGENCY_RE.match(topic):
        return "emergency"
    if topic.endswith("/STOP"):
        return "global_stop"
    if ROOM_PREFIX_RE.match(topic):
        return "room_generic"

    return "unknown"


def _is_reserved_room_namespace_typo(topic: str) -> bool:
    """Reject likely typos such as room1/lightasdf/fire that should not pass as generic room topics."""
    if not isinstance(topic, str):
        return False

    parts = topic.split("/")
    if len(parts) < 2:
        return False

    room_prefix, namespace = parts[0], parts[1]
    if not ROOM_PREFIX_RE.match(room_prefix):
        return False

    for reserved in RESERVED_ROOM_NAMESPACES:
        if namespace != reserved and namespace.startswith(reserved):
            return True

    return False


def validate_topic(topic: str) -> Tuple[bool, str]:
    topic_type = classify_topic(topic)
    if topic_type in {"invalid", "unknown"}:
        return False, f"Unsupported MQTT topic format: {topic}"

    if topic_type == "room_generic" and _is_reserved_room_namespace_typo(topic):
        return False, f"Malformed room topic namespace (possible typo): {topic}"

    return True, ""


def validate_payload_for_topic(topic: str, message) -> Tuple[bool, str]:
    """
    Validate payload with minimal rules that preserve current behavior.

    Returns tuple: (is_valid, error_message)
    """
    topic_type = classify_topic(topic)

    # Keep backwards compatibility with numeric/bool payloads from schema.
    if isinstance(message, (int, float, bool)):
        return True, ""

    if not isinstance(message, str) or not message.strip():
        return False, f"MQTT payload must be a non-empty string/number/bool for topic {topic}"

    normalized = message.strip()

    if topic_type == "motor":
        if ON_OFF_RE.match(normalized) or normalized.upper() == "STOP" or SPEED_RE.match(normalized) or MOTOR_ON_COMPLEX_RE.match(normalized):
            return True, ""
        return False, f"Invalid motor payload '{message}' for topic {topic}"

    if topic_type in {"light", "effects", "emergency", "global_stop"}:
        if ON_OFF_RE.match(normalized) or normalized.upper() in {"STOP", "RESET", "BLINK"}:
            return True, ""
        return False, f"Invalid on/off payload '{message}' for topic {topic}"

    if topic_type == "scene_start":
        if normalized.upper() == "START":
            return True, ""
        return False, f"Scene trigger topic expects START payload, got '{message}'"

    if topic_type == "named_scene":
        if normalized.endswith(".json"):
            return True, ""
        return False, f"Named scene topic expects '<name>.json', got '{message}'"

    # For status/feedback/generic topics, keep permissive behavior for compatibility.
    return True, ""


def validate_publish(topic: str, message) -> Tuple[bool, str]:
    """Combined topic+payload check for publish paths."""
    topic_ok, topic_err = validate_topic(topic)
    if not topic_ok:
        return False, topic_err

    payload_ok, payload_err = validate_payload_for_topic(topic, message)
    if not payload_ok:
        return False, payload_err

    return True, ""


def get_expected_feedback_topic(original_topic: str) -> Optional[str]:
    """Derive expected feedback topic for command topics, else None."""
    topic_type = classify_topic(original_topic)

    if topic_type in {"motor", "light", "effects", "room_generic"}:
        return f"{original_topic}/feedback"

    return None
