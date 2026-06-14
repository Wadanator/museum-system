import configparser
import shutil
import sys
import threading
import time
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from utils.config_manager import ConfigManager
from utils.runtime.ambient_loop_service import AmbientLoopService


class _ListLogger:
    def __init__(self):
        self.warnings = []
        self.errors = []

    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

    def critical(self, *args, **kwargs):
        pass

    def error(self, message, *args, **kwargs):
        if args:
            message = message % args
        self.errors.append(message)

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


class _FakeOwner:
    def __init__(self, config):
        self.config = config
        self.shutdown_requested = False
        self.start_calls = []

    def _initiate_scene_start(self, scene_filename, log_message):
        self.start_calls.append((scene_filename, log_message))
        return True


class _FailingStartOwner(_FakeOwner):
    def _initiate_scene_start(self, scene_filename, log_message):
        self.start_calls.append((scene_filename, log_message))
        return False


def _ambient_config(**overrides):
    config = {
        "startup_mode": "ambient",
        "json_file_name": "SceneV01.json",
        "ambient_scene": "AmbientLoop.json",
        "ambient_start_policy": "after_initial_connection_attempt",
        "ambient_restart_delay_seconds": 2.0,
        "ambient_error_retry_seconds": 30.0,
        "ambient_cycle_cleanup": "scene_only",
        "ambient_ignore_default_start": True,
        "ambient_allow_named_scene_start": True,
        "ambient_stop_behavior": "suspend_until_restart",
    }
    config.update(overrides)
    return config


def _service(config=None, owner_cls=_FakeOwner):
    logger = _ListLogger()
    owner = owner_cls(config or _ambient_config())
    return AmbientLoopService(owner, logger), owner, logger


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


def test_ambient_service_reports_classic_disabled_status():
    service, _owner, _logger = _service(
        {
            "startup_mode": "classic",
            "json_file_name": "SceneV01.json",
        }
    )

    status = service.get_status()
    assert status["enabled"] is False
    assert status["scene"] == "SceneV01.json"
    assert status["suspended"] is False
    assert status["next_restart_at"] is None
    assert status["last_outcome"] == "never_started"
    assert service.should_ignore_default_start() is False
    assert service.should_allow_named_scene_start() is True


def test_ambient_service_status_and_start_decisions_use_config():
    service, _owner, _logger = _service(
        _ambient_config(
            ambient_ignore_default_start=False,
            ambient_allow_named_scene_start=False,
        )
    )

    assert service.is_enabled() is True
    assert service.startup_mode() == "ambient"
    assert service.scene_name() == "AmbientLoop.json"
    assert service.should_ignore_default_start() is False
    assert service.should_allow_named_scene_start() is False

    status = service.get_status()
    assert status["enabled"] is True
    assert status["scene"] == "AmbientLoop.json"
    assert status["start_policy"] == "after_initial_connection_attempt"
    assert status["cycle_cleanup"] == "scene_only"


def test_operator_stop_suspend_policy_uses_mode_and_config():
    service, _owner, _logger = _service(
        _ambient_config(ambient_stop_behavior="suspend_until_restart")
    )
    assert service.should_suspend_on_operator_stop() is True

    service, _owner, _logger = _service(
        _ambient_config(ambient_stop_behavior="resume_after_delay")
    )
    assert service.should_suspend_on_operator_stop() is False

    service, _owner, _logger = _service({"startup_mode": "classic"})
    assert service.should_suspend_on_operator_stop() is False


def test_cycle_cleanup_reports_configured_mode():
    service, _owner, _logger = _service(
        _ambient_config(ambient_cycle_cleanup="full_stop")
    )

    assert service.cycle_cleanup() == "full_stop"


def test_start_after_boot_is_idempotent_for_default_policy():
    service, owner, _logger = _service()

    assert service.start_after_boot_if_needed() is True
    assert service.start_after_boot_if_needed() is False
    assert owner.start_calls == [
        ("AmbientLoop.json", "Ambient mode: auto-start on boot")
    ]


def test_start_after_boot_skips_wait_for_mqtt_policy():
    service, owner, _logger = _service(
        _ambient_config(ambient_start_policy="wait_for_mqtt")
    )

    assert service.start_after_boot_if_needed() is False
    assert owner.start_calls == []


def test_start_after_mqtt_restore_is_idempotent_for_wait_policy():
    service, owner, _logger = _service(
        _ambient_config(ambient_start_policy="wait_for_mqtt")
    )

    assert service.start_after_mqtt_restore_if_needed() is True
    assert service.start_after_mqtt_restore_if_needed() is False
    assert owner.start_calls == [
        ("AmbientLoop.json", "Ambient mode: MQTT restored auto-start")
    ]


def test_failed_ambient_start_records_start_failure():
    service, owner, _logger = _service(owner_cls=_FailingStartOwner)

    assert service.start_after_boot_if_needed() is False
    assert owner.start_calls == [
        ("AmbientLoop.json", "Ambient mode: auto-start on boot")
    ]
    assert service.get_status()["last_outcome"] == "start_failure"


def test_suspension_blocks_start_and_restart_until_resume():
    service, owner, _logger = _service()

    service.suspend_by_operator_stop()
    assert service.get_status()["suspended"] is True
    assert service.get_status()["last_outcome"] == "explicit_stop"
    assert service.start_after_boot_if_needed() is False
    assert service.should_restart_after_scene("AmbientLoop.json", normal_end=True) is False

    service.resume()
    assert service.get_status()["suspended"] is False
    assert service.start_after_boot_if_needed() is True
    assert owner.start_calls == [
        ("AmbientLoop.json", "Ambient mode: auto-start on boot")
    ]


def test_restart_decision_only_allows_configured_ambient_normal_end():
    service, _owner, _logger = _service()

    assert service.should_restart_after_scene("AmbientLoop.json", normal_end=True)
    assert not service.should_restart_after_scene("OtherScene.json", normal_end=True)
    assert not service.should_restart_after_scene("AmbientLoop.json", normal_end=False)


def test_restart_delay_selects_normal_or_error_delay():
    service, _owner, _logger = _service(
        _ambient_config(
            ambient_restart_delay_seconds=4.5,
            ambient_error_retry_seconds=12.0,
        )
    )

    assert service.restart_delay_seconds(normal_end=True) == 4.5
    assert service.restart_delay_seconds(normal_end=False) == 12.0


def test_wait_for_restart_delay_sets_iso_status_and_wakes_on_suspend():
    service, _owner, _logger = _service()
    result = []

    thread = threading.Thread(
        target=lambda: result.append(service.wait_for_restart_delay(10)),
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 1.0
    while service.get_status()["next_restart_at"] is None:
        assert time.monotonic() < deadline
        time.sleep(0.01)

    next_restart_at = service.get_status()["next_restart_at"]
    assert "T" in next_restart_at
    assert next_restart_at.endswith("Z")

    service.suspend_by_operator_stop()
    thread.join(timeout=1.0)

    assert result == [False]
    assert service.get_status()["next_restart_at"] is None


def test_request_shutdown_cancels_restart_wait_and_records_shutdown():
    service, _owner, _logger = _service()
    result = []

    thread = threading.Thread(
        target=lambda: result.append(service.wait_for_restart_delay(10)),
        daemon=True,
    )
    thread.start()

    deadline = time.monotonic() + 1.0
    while service.get_status()["next_restart_at"] is None:
        assert time.monotonic() < deadline
        time.sleep(0.01)

    service.request_shutdown()
    thread.join(timeout=1.0)

    assert result == [False]
    assert service.get_status()["last_outcome"] == "shutdown"
    assert service.get_status()["next_restart_at"] is None


def test_record_outcome_validates_status_values():
    service, _owner, logger = _service()

    service.record_outcome("normal_end")
    assert service.get_status()["last_outcome"] == "normal_end"

    service.record_outcome("surprising")
    assert service.get_status()["last_outcome"] == "error"
    assert logger.warnings == ["Unknown ambient outcome 'surprising'; using 'error'"]
