#!/usr/bin/env python3
"""
Schema Validator - JSON structure validation for scene files.
"""

from jsonschema import Draft7Validator
from utils.image_command import parse_image_command

VALID_TRANSITION_TYPES = {
    "timeout",
    "audioEnd",
    "videoEnd",
    "mqttMessage",
    "always",
}


# Action definition (used in onEnter, onExit, and timeline)
ACTION_SCHEMA = {
    "type": "object",
    "required": ["action"],
    "properties": {
        "action": {"type": "string", "enum": ["mqtt", "audio", "video", "image"]},
        "topic": {"type": "string"},
        "message": {"type": ["string", "number", "boolean"]},
        "retain": {"type": "boolean"}
    }
}

# Transition definition (used in transitions and globalEvents)
TRANSITION_SCHEMA = {
    "type": "object",
    "required": ["type", "goto"],
    "properties": {
        "type": {"type": "string"},
        "goto": {"type": "string"},
        "delay": {"type": "number"},
        "target": {"type": "string"},
        "topic": {"type": "string"},
        "message": {"type": ["string", "number", "boolean"]}
    }
}

# Main scene schema
SCENE_SCHEMA = {
    "type": "object",
    "required": ["sceneId", "initialState", "states"],
    "properties": {
        "sceneId": {"type": "string"},
        "version": {"type": "string"},
        "description": {"type": "string"},
        "initialState": {"type": "string"},

        "globalEvents": {
            "type": "array",
            "items": TRANSITION_SCHEMA
        },

        "states": {
            "type": "object",
            "minProperties": 1,
            "patternProperties": {
                "^.*$": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "onEnter": {"type": "array", "items": ACTION_SCHEMA},
                        "onExit": {"type": "array", "items": ACTION_SCHEMA},
                        "transitions": {
                            "type": "array",
                            "items": TRANSITION_SCHEMA
                        },
                        "timeline": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["at"],
                                "properties": {
                                    "at": {"type": "number"},
                                    "action": {
                                        "type": "string",
                                        "enum": ["mqtt", "audio", "video", "image"]
                                    },
                                    "topic": {"type": "string"},
                                    "message": {
                                        "type": ["string", "number", "boolean"]
                                    },
                                    "actions": {
                                        "type": "array",
                                        "items": ACTION_SCHEMA
                                    }
                                }
                            }
                        }
                    },
                    "additionalProperties": False
                }
            }
        }
    }
}


def _format_path(path_parts):
    """Return a compact dotted path for validation messages."""
    parts = [str(part) for part in path_parts]
    return ".".join(parts) if parts else "<root>"


def _make_error(path, message):
    return {
        "path": _format_path(path),
        "message": message,
    }


def _is_blank(value):
    return value is None or (isinstance(value, str) and value == "")


def _validate_action_runtime_shape(action, path, errors):
    action_type = action.get("action")

    if action_type == "mqtt":
        if _is_blank(action.get("topic")):
            errors.append(_make_error(path + ["topic"], "MQTT action requires topic"))
        if _is_blank(action.get("message")):
            errors.append(_make_error(path + ["message"], "MQTT action requires message"))
    elif action_type in {"audio", "video"}:
        if _is_blank(action.get("message")):
            errors.append(
                _make_error(
                    path + ["message"],
                    f"{action_type} action requires message",
                )
            )
    elif action_type == "image":
        message = action.get("message")
        if _is_blank(message):
            errors.append(
                _make_error(path + ["message"], "image action requires message")
            )
            return

        parsed = parse_image_command(message)
        if not parsed.valid:
            errors.append(_make_error(path + ["message"], parsed.error))


def _validate_transition_runtime_shape(transition, path, errors):
    transition_type = transition.get("type")

    if transition_type not in VALID_TRANSITION_TYPES:
        errors.append(
            _make_error(
                path + ["type"],
                f"Unknown transition type '{transition_type}'",
            )
        )
        return

    if transition_type == "mqttMessage":
        if _is_blank(transition.get("topic")):
            errors.append(
                _make_error(path + ["topic"], "mqttMessage transition requires topic")
            )
        if _is_blank(transition.get("message")):
            errors.append(
                _make_error(path + ["message"], "mqttMessage transition requires message")
            )
    elif transition_type in {"audioEnd", "videoEnd"}:
        if _is_blank(transition.get("target")):
            errors.append(
                _make_error(
                    path + ["target"],
                    f"{transition_type} transition requires target",
                )
            )


def _validate_timeline_item_runtime_shape(item, path, errors):
    has_action = "action" in item
    has_actions = "actions" in item

    if not has_action and not has_actions:
        errors.append(
            _make_error(
                path,
                "Timeline item requires either action or actions",
            )
        )
        return

    if has_action and has_actions:
        errors.append(
            _make_error(
                path,
                "Timeline item cannot define both action and actions",
            )
        )
        return

    if has_action:
        _validate_action_runtime_shape(item, path, errors)
    else:
        for idx, action in enumerate(item.get("actions", [])):
            _validate_action_runtime_shape(action, path + ["actions", idx], errors)


def _log_validation_errors(errors, logger=None):
    if not logger:
        return
    for error in errors:
        logger.error(
            "Scene validation error at '%s': %s",
            error["path"],
            error["message"],
        )


def validate_scene_payload(data, logger=None):
    """
    Validate parsed scene data and return a JSON-serializable result.

    The result is suitable for API responses and frontend display. It combines
    structural JSON Schema validation with runtime logical checks that the
    StateMachine also depends on, such as initialState and transition targets.
    """
    errors = []
    warnings = []

    if not isinstance(data, dict):
        errors.append(_make_error([], "Scene root must be a JSON object"))
        _log_validation_errors(errors, logger)
        return {"valid": False, "errors": errors, "warnings": warnings}

    validator = Draft7Validator(SCENE_SCHEMA)
    schema_errors = sorted(
        validator.iter_errors(data),
        key=lambda err: list(err.path),
    )

    for err in schema_errors:
        errors.append(_make_error(err.absolute_path, err.message))

    if errors:
        _log_validation_errors(errors, logger)
        return {"valid": False, "errors": errors, "warnings": warnings}

    states = data["states"]
    initial_state = data["initialState"]

    if initial_state not in states:
        errors.append(
            _make_error(
                ["initialState"],
                f"Initial state '{initial_state}' is not defined",
            )
        )

    for state_name, state_data in states.items():
        for idx, action in enumerate(state_data.get("onEnter", [])):
            _validate_action_runtime_shape(
                action,
                ["states", state_name, "onEnter", idx],
                errors,
            )

        for idx, action in enumerate(state_data.get("onExit", [])):
            _validate_action_runtime_shape(
                action,
                ["states", state_name, "onExit", idx],
                errors,
            )

        for idx, item in enumerate(state_data.get("timeline", [])):
            _validate_timeline_item_runtime_shape(
                item,
                ["states", state_name, "timeline", idx],
                errors,
            )

        transitions = state_data.get("transitions", [])
        for idx, transition in enumerate(transitions):
            transition_path = ["states", state_name, "transitions", idx]
            _validate_transition_runtime_shape(transition, transition_path, errors)
            goto = transition["goto"]
            if goto != "END" and goto not in states:
                errors.append(
                    _make_error(
                        transition_path + ["goto"],
                        (
                            f"Transition targets unknown state '{goto}'"
                        ),
                    )
                )

    for idx, event in enumerate(data.get("globalEvents", [])):
        event_path = ["globalEvents", idx]
        _validate_transition_runtime_shape(event, event_path, errors)
        goto = event["goto"]
        if goto != "END" and goto not in states:
            errors.append(
                _make_error(
                    event_path + ["goto"],
                    f"Global event targets unknown state '{goto}'",
                )
            )

    _log_validation_errors(errors, logger)
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def validate_scene_json(data, logger=None):
    """
    Validate scene data against the scene JSON schema.

    Args:
        data: Parsed JSON data (dict) representing the scene to validate.
        logger: Optional logger instance. If provided, validation errors
            are logged at ERROR level; otherwise they are printed.

    Returns:
        bool: True if the data is valid, False if validation fails.
    """
    result = validate_scene_payload(data, logger=logger)
    if not result["valid"] and not logger:
        for error in result["errors"]:
            print(
                f"Schema validation error at '{error['path']}': "
                f"{error['message']}"
            )
    return result["valid"]
