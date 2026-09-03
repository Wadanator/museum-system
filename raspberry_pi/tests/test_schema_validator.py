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


def _scene_with_on_enter_action(action):
    return {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "onEnter": [action]
            }
        }
    }


def test_validate_scene_payload_accepts_image_show_action():
    data = _scene_with_on_enter_action(
        {"action": "image", "message": "SHOW:wallpaper.png"}
    )

    assert validate_scene_payload(data)["valid"] is True


def test_validate_scene_payload_accepts_display_policy():
    data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "displayPolicy": "required",
        "states": {
            "START": {}
        }
    }

    assert validate_scene_payload(data)["valid"] is True


def test_validate_scene_payload_rejects_unknown_display_policy():
    data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "displayPolicy": "always_on",
        "states": {
            "START": {}
        }
    }

    result = validate_scene_payload(data)

    assert result["valid"] is False
    assert result["errors"][0]["path"] == "displayPolicy"


def test_validate_scene_payload_accepts_image_clear_action():
    data = _scene_with_on_enter_action(
        {"action": "image", "message": "CLEAR"}
    )

    assert validate_scene_payload(data)["valid"] is True


def test_validate_scene_payload_accepts_image_default_action():
    data = _scene_with_on_enter_action(
        {"action": "image", "message": "DEFAULT"}
    )

    assert validate_scene_payload(data)["valid"] is True


@pytest.mark.parametrize(
    "message",
    [
        "SHOW:",
        "wallpaper.png",
        "SHOW:intro.mp4",
        "SHOW:music.mp3",
        "SHOW:sfx.wav",
        "SHOW:clip.webm",
        "SHOW:../wallpaper.png",
        "SHOW:/tmp/wallpaper.png",
        "SHOW:subdir/wallpaper.png",
        "BLACK",
        "",
    ],
)
def test_validate_scene_payload_rejects_invalid_image_messages(message):
    data = _scene_with_on_enter_action(
        {"action": "image", "message": message}
    )

    result = validate_scene_payload(data)

    assert result["valid"] is False
    assert result["errors"][0]["path"] == "states.START.onEnter.0.message"


def test_validate_scene_payload_rejects_non_string_image_message():
    data = _scene_with_on_enter_action(
        {"action": "image", "message": True}
    )

    result = validate_scene_payload(data)

    assert result["valid"] is False
    assert result["errors"][0]["path"] == "states.START.onEnter.0.message"


def test_validate_scene_payload_rejects_photo_action_typo():
    data = _scene_with_on_enter_action(
        {"action": "photo", "message": "SHOW:wallpaper.png"}
    )

    assert validate_scene_payload(data)["valid"] is False


def test_validate_scene_payload_accepts_image_timeline_action():
    data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "timeline": [
                    {"at": 1.0, "action": "image", "message": "SHOW:slide.jpg"}
                ]
            }
        }
    }

    assert validate_scene_payload(data)["valid"] is True
