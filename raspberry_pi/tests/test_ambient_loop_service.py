import configparser
import shutil
import sys
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from utils.config_manager import ConfigManager


class _ListLogger:
    def __init__(self):
        self.warnings = []

    def debug(self, *args, **kwargs):
        pass

    def critical(self, *args, **kwargs):
        pass

    def warning(self, message, *args, **kwargs):
        if args:
            message = message % args
        self.warnings.append(message)


def _config_file(tmp_path, updates=None, remove_startup=False):
    cfg_file = tmp_path / "config.ini"
    shutil.copy(str(RPI_DIR / "config" / "config.ini.example"), str(cfg_file))

    cfg = configparser.ConfigParser()
    cfg.read(str(cfg_file))

    if remove_startup:
        cfg.remove_section("Startup")

    for section, values in (updates or {}).items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        for key, value in values.items():
            cfg.set(section, key, str(value))

    with cfg_file.open("w", encoding="utf-8") as fh:
        cfg.write(fh)

    return cfg_file


def _load_config(tmp_path, updates=None, remove_startup=False):
    logger = _ListLogger()
    manager = ConfigManager(
        config_file=str(_config_file(tmp_path, updates, remove_startup)),
        logger=logger,
    )
    return manager.get_all_config(), logger


def test_startup_config_defaults_to_classic_when_section_missing(tmp_path):
    config, logger = _load_config(tmp_path, remove_startup=True)

    assert config["startup_mode"] == "classic"
    assert config["ambient_scene"] == "SceneV01.json"
    assert config["ambient_start_policy"] == "after_initial_connection_attempt"
    assert config["ambient_restart_delay_seconds"] == 2.0
    assert config["ambient_error_retry_seconds"] == 30.0
    assert config["ambient_cycle_cleanup"] == "scene_only"
    assert config["ambient_ignore_default_start"] is True
    assert config["ambient_allow_named_scene_start"] is True
    assert config["ambient_stop_behavior"] == "suspend_until_restart"
    assert logger.warnings == []


def test_startup_config_accepts_valid_ambient_overrides(tmp_path):
    config, logger = _load_config(
        tmp_path,
        {
            "Startup": {
                "mode": "ambient",
                "ambient_scene": "AmbientLoop.json",
                "ambient_start_policy": "wait_for_mqtt",
                "ambient_restart_delay_seconds": "3.5",
                "ambient_error_retry_seconds": "12.25",
                "ambient_cycle_cleanup": "full_stop",
                "ambient_ignore_default_start": "false",
                "ambient_allow_named_scene_start": "false",
                "ambient_stop_behavior": "resume_after_delay",
            }
        },
    )

    assert config["startup_mode"] == "ambient"
    assert config["ambient_scene"] == "AmbientLoop.json"
    assert config["ambient_start_policy"] == "wait_for_mqtt"
    assert config["ambient_restart_delay_seconds"] == 3.5
    assert config["ambient_error_retry_seconds"] == 12.25
    assert config["ambient_cycle_cleanup"] == "full_stop"
    assert config["ambient_ignore_default_start"] is False
    assert config["ambient_allow_named_scene_start"] is False
    assert config["ambient_stop_behavior"] == "resume_after_delay"
    assert logger.warnings == []


def test_empty_ambient_scene_resolves_to_default_json_scene(tmp_path):
    config, _logger = _load_config(
        tmp_path,
        {
            "Json": {"json_file_name": "DefaultScene.json"},
            "Startup": {"mode": "ambient", "ambient_scene": ""},
        },
    )

    assert config["ambient_scene"] == "DefaultScene.json"


def test_invalid_startup_enums_fall_back_to_documented_defaults(tmp_path):
    config, logger = _load_config(
        tmp_path,
        {
            "Startup": {
                "mode": "always",
                "ambient_start_policy": "immediate",
                "ambient_cycle_cleanup": "unsafe",
                "ambient_stop_behavior": "forever",
            }
        },
    )

    assert config["startup_mode"] == "classic"
    assert config["ambient_start_policy"] == "after_initial_connection_attempt"
    assert config["ambient_cycle_cleanup"] == "scene_only"
    assert config["ambient_stop_behavior"] == "suspend_until_restart"
    assert len(logger.warnings) == 4


def test_negative_ambient_delays_are_clamped_to_zero(tmp_path):
    config, logger = _load_config(
        tmp_path,
        {
            "Startup": {
                "ambient_restart_delay_seconds": "-5",
                "ambient_error_retry_seconds": "-30",
            }
        },
    )

    assert config["ambient_restart_delay_seconds"] == 0.0
    assert config["ambient_error_retry_seconds"] == 0.0
    assert len(logger.warnings) == 2
    assert all("clamping to 0" in warning for warning in logger.warnings)


def test_ambient_restart_delay_warns_when_above_watchdog_wait(tmp_path):
    config, logger = _load_config(
        tmp_path,
        {
            "System": {"scene_wait_max_seconds": "10"},
            "Startup": {"ambient_restart_delay_seconds": "60"},
        },
    )

    assert config["scene_wait_max_seconds"] == 10
    assert config["ambient_restart_delay_seconds"] == 60.0
    assert any("watchdog may force restart" in warning for warning in logger.warnings)
