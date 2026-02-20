#!/usr/bin/env python3
"""
Schema Validator - Validácia JSON štruktúry pre scény
"""
from jsonschema import validate, ValidationError

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

def validate_scene_json(data, logger=None):
    """Overí dáta voči schéme. Vráti True/False."""
    try:
        validate(instance=data, schema=SCENE_SCHEMA)
        return True
    except ValidationError as e:
        error_path = " -> ".join([str(p) for p in e.path])
        error_msg = f"Schema validation error at '{error_path}': {e.message}"
        
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
            
        return False