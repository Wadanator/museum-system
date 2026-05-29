import pytest
# Import function under test.
from utils.schema_validator import validate_scene_json, validate_scene_payload

def test_validate_scene_json_valid():
    """Validate that the schema validator accepts a valid scene JSON."""
    
    # Minimal valid structure according to SCENE_SCHEMA.
    valid_data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "description": "Initial state"
            }
        }
    }
    
    # Function should return True for valid data.
    assert validate_scene_json(valid_data) is True

def test_validate_scene_json_missing_required_fields():
    """Validate that missing required fields are rejected."""
    
    # Missing required fields: "states" and "initialState".
    invalid_data = {
        "sceneId": "room1_intro"
    }
    
    # Function should return False because schema requirements are not met.
    assert validate_scene_json(invalid_data) is False

def test_validate_scene_json_invalid_action_type():
    """Validate that invalid action type is rejected."""
    
    invalid_data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "onEnter": [
                    {
                        "action": "laser",  # ACTION_SCHEMA allows only: mqtt, audio, video.
                        "topic": "test/topic"
                    }
                ]
            }
        }
    }
    
    # Function should return False due to invalid action type.
    assert validate_scene_json(invalid_data) is False


def test_validate_scene_payload_rejects_unknown_initial_state():
    data = {
        "sceneId": "room1_intro",
        "initialState": "INTRO",
        "states": {
            "START": {}
        }
    }

    result = validate_scene_payload(data)

    assert result["valid"] is False
    assert result["errors"][0]["path"] == "initialState"
    assert "INTRO" in result["errors"][0]["message"]


def test_validate_scene_payload_rejects_unknown_transition_target():
    data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "transitions": [
                    {"type": "always", "goto": "MISSING"}
                ]
            }
        }
    }

    result = validate_scene_payload(data)

    assert result["valid"] is False
    assert result["errors"][0]["path"] == "states.START.transitions.0.goto"
    assert "MISSING" in result["errors"][0]["message"]


def test_validate_scene_payload_allows_terminal_end_target():
    data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "transitions": [
                    {"type": "always", "goto": "END"}
                ]
            }
        }
    }

    assert validate_scene_payload(data)["valid"] is True


def test_validate_scene_payload_rejects_incomplete_mqtt_action():
    data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "onEnter": [
                    {"action": "mqtt", "topic": "room1/light/1"}
                ]
            }
        }
    }

    result = validate_scene_payload(data)

    assert result["valid"] is False
    assert result["errors"][0]["path"] == "states.START.onEnter.0.message"


def test_validate_scene_payload_rejects_incomplete_mqtt_transition():
    data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "transitions": [
                    {"type": "mqttMessage", "topic": "room1/button", "goto": "END"}
                ]
            }
        }
    }

    result = validate_scene_payload(data)

    assert result["valid"] is False
    assert result["errors"][0]["path"] == "states.START.transitions.0.message"


def test_validate_scene_payload_rejects_empty_timeline_item():
    data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "timeline": [
                    {"at": 1.0}
                ]
            }
        }
    }

    result = validate_scene_payload(data)

    assert result["valid"] is False
    assert result["errors"][0]["path"] == "states.START.timeline.0"
