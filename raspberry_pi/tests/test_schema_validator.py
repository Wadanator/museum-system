import pytest
# Import function under test.
from utils.schema_validator import validate_scene_json

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