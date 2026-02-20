#!/usr/bin/env python3
"""
Schema Validator - Validácia JSON štruktúry pre scény
"""
from jsonschema import validate, ValidationError

from utils.mqtt.mqtt_contract import validate_publish

# Definícia akcie (použije sa v onEnter, onExit, timeline)
ACTION_SCHEMA = {
    "type": "object",
    "required": ["action"],
    "properties": {
        "action": {"type": "string", "enum": ["mqtt", "audio", "video"]},
        "topic": {"type": "string"},
        "message": {"type": ["string", "number", "boolean"]},
        "retain": {"type": "boolean"}
    }
}

# Definícia prechodu (použije sa v transitions aj globalEvents)
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

# Hlavná schéma scény
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
                                    "action": {"type": "string", "enum": ["mqtt", "audio", "video"]},
                                    "topic": {"type": "string"},
                                    "message": {"type": ["string", "number", "boolean"]},
                                    "actions": {"type": "array", "items": ACTION_SCHEMA}
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



def _validate_mqtt_actions_semantics(data, logger=None):
    """Semantic validation for MQTT action topic/payload pairs."""

    def _walk(node):
        if isinstance(node, dict):
            if node.get("action") == "mqtt":
                topic = node.get("topic")
                message = node.get("message")
                is_valid, error = validate_publish(topic, message)
                if not is_valid:
                    return False, error

            for value in node.values():
                ok, err = _walk(value)
                if not ok:
                    return False, err

        elif isinstance(node, list):
            for item in node:
                ok, err = _walk(item)
                if not ok:
                    return False, err

        return True, ""

    return _walk(data)

def validate_scene_json(data, logger=None):
    """Overí dáta voči schéme. Vráti True/False."""
    try:
        validate(instance=data, schema=SCENE_SCHEMA)

        semantics_ok, semantics_error = _validate_mqtt_actions_semantics(data, logger)
        if not semantics_ok:
            if logger:
                logger.error(f"MQTT semantic validation error: {semantics_error}")
            else:
                print(f"MQTT semantic validation error: {semantics_error}")
            return False

        return True
    except ValidationError as e:
        error_path = " -> ".join([str(p) for p in e.path])
        error_msg = f"Schema validation error at '{error_path}': {e.message}"
        
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
            
        return False