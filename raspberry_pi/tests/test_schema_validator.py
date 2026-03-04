import pytest
# Importujeme funkciu, ktorú chceme testovať
from utils.schema_validator import validate_scene_json

def test_validate_scene_json_valid():
    """Testuje, či validátor správne prijme korektný JSON scény."""
    
    # Toto je minimálna platná štruktúra podľa SCENE_SCHEMA
    valid_data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "description": "Počiatočný stav"
            }
        }
    }
    
    # Očakávame, že funkcia vráti True
    assert validate_scene_json(valid_data) is True

def test_validate_scene_json_missing_required_fields():
    """Testuje, či validátor správne odmietne JSON, ktorému chýbajú povinné polia."""
    
    # V tomto JSONe chýba povinné pole "states" a "initialState"
    invalid_data = {
        "sceneId": "room1_intro"
    }
    
    # Očakávame, že funkcia vráti False, pretože schéma nebola dodržaná
    assert validate_scene_json(invalid_data) is False

def test_validate_scene_json_invalid_action_type():
    """Testuje, či validátor odhalí zlý typ akcie."""
    
    invalid_data = {
        "sceneId": "room1_intro",
        "initialState": "START",
        "states": {
            "START": {
                "onEnter": [
                    {
                        "action": "laser", # Podľa ACTION_SCHEMA sú povolené len "mqtt", "audio", "video"
                        "topic": "test/topic"
                    }
                ]
            }
        }
    }
    
    # Očakávame, že vráti False kvôli neplatnému typu akcie
    assert validate_scene_json(invalid_data) is False