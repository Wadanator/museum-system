#!/usr/bin/env python3
"""
Configuration manager for the museum controller system.

Loads and parses config.ini, auto-creates it from a template if missing,
and provides structured access to all configuration sections.
"""

import os
import configparser
import logging
import shutil
import shlex
from pathlib import Path
from utils.logging_setup import get_logger


class ConfigManager:
    """
    Centralized configuration loader and accessor.

    Reads settings from config.ini and exposes them as structured
    dictionaries for logging, MQTT, GPIO, audio, video, and system
    components. Auto-creates config.ini from a template if absent.
    """

    def __init__(self, config_file=None, logger=None):
        """
        Initialize the configuration manager and load config.ini.

        If config.ini does not exist but config.ini.example does, the
        example file is copied automatically. Raises FileNotFoundError
        if the config file is still missing after the auto-create attempt.

        Args:
            config_file: Path to the config file. Defaults to
                <project_root>/config/config.ini.
            logger: Logger instance for configuration events.

        Raises:
            FileNotFoundError: If the configuration file cannot be found
                or created.
        """
        self.logger = logger or get_logger('config')

        # Resolve the raspberry_pi project root directory
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Default config file path
        if config_file is None:
            config_file = os.path.join(script_dir, "config", "config.ini")

        # --- Auto-create logic ---
        # If config.ini is missing but an example exists, copy it
        example_file = os.path.join(script_dir, "config", "config.ini.example")
        if not os.path.exists(config_file) and os.path.exists(example_file):
            try:
                shutil.copy2(example_file, config_file)
                # Use print because the logger may not be fully initialized yet
                print(f"Config file created from default template: {config_file}")
            except Exception as e:
                print(f"Failed to create config file from template: {e}")
        # -------------------------

        self.config_file = config_file
        self.config = configparser.ConfigParser()

        # Load config file
        if not os.path.exists(config_file):
            self.logger.critical(f"Config file not found: {config_file}")
            raise FileNotFoundError(f"Configuration file missing: {config_file}")

        self.config.read(config_file)
        self.logger.debug(f"Config loaded from: {self.config_file}")

    def get_logging_config(self):
        """
        Return logging configuration as a dictionary.

        Falls back to safe defaults if the [Logging] section is absent.
        Reads component-specific log levels from the [LogLevels] section
        if present.

        Returns:
            dict: Logging settings including log level, directory, file size
                limits, rotation settings, output toggles, format, and
                per-component log levels.
        """
        if 'Logging' not in self.config:
            # Fallback if the section is missing
            return {
                'log_level': logging.INFO,
                'log_directory': None,
                'max_file_size': 10 * 1024 * 1024,
                'backup_count': 5,
                'daily_backup_days': 30,
                'console_colors': True,
                'file_logging': True,
                'console_logging': True,
                'log_format': 'detailed',
                'component_levels': {}
            }

        section = self.config['Logging']
        log_level_str = section.get('log_level', 'INFO').upper()
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        log_level = log_level_map.get(log_level_str, logging.INFO)

        # Read component-specific log levels from [LogLevels] section
        component_levels = {}
        if self.config.has_section('LogLevels'):
            component_levels = dict(self.config['LogLevels'].items())

        return {
            'log_level': log_level,
            'log_directory': (
                Path(section.get('log_directory', '').strip())
                if section.get('log_directory')
                else None
            ),
            'max_file_size': section.getint('max_file_size_mb', 10) * 1024 * 1024,
            'backup_count': section.getint('backup_count', 5),
            'daily_backup_days': section.getint('daily_backup_days', 30),
            'console_colors': section.getboolean('console_colors', True),
            'file_logging': section.getboolean('file_logging', True),
            'console_logging': section.getboolean('console_logging', True),
            'log_format': section.get('log_format', 'detailed'),
            'component_levels': component_levels
        }

    def _get_choice(self, section, option, *, allowed, fallback):
        value = self.config.get(section, option, fallback=fallback).strip().lower()
        if value in allowed:
            return value

        self.logger.warning(
            "Invalid [%s] %s=%r; using %r",
            section,
            option,
            value,
            fallback,
        )
        return fallback

    def _get_nonnegative_float(self, section, option, *, fallback):
        value = self.config.getfloat(section, option, fallback=fallback)
        if value >= 0:
            return value

        self.logger.warning(
            "Invalid negative [%s] %s=%s; clamping to 0",
            section,
            option,
            value,
        )
        return 0.0

    def get_all_config(self):
        """
        Return the complete application configuration as a single dictionary.

        Resolves all directory paths relative to the project root and merges
        logging configuration from get_logging_config(). Covers MQTT, GPIO,
        room, system timing, video, and audio settings.

        Returns:
            dict: Flat dictionary of all configuration values with defaults
                applied for any missing keys.
        """
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        def resolve_runtime_path(path_value):
            raw_value = str(path_value or '').strip()
            if not raw_value:
                return ''
            if os.path.isabs(raw_value):
                return os.path.normpath(raw_value)
            return os.path.normpath(os.path.join(script_dir, raw_value))

        # Resolve directory names and room ID
        scenes_dir_name = self.config.get('Scenes', 'directory', fallback='scenes')
        room_id = self.config.get('Room', 'room_id', fallback='room1')
        audio_dir_name = self.config.get('Audio', 'directory', fallback='audio')
        video_dir_name = self.config.get('Video', 'directory', fallback='videos')
        json_file_name = self.config.get(
            'Json', 'json_file_name', fallback='default.json'
        )

        # Base path for all scenes
        scenes_base_path = os.path.join(script_dir, scenes_dir_name)

        # Path to the specific room's asset directory
        room_path = os.path.join(scenes_base_path, room_id)
        devices_config_path = os.path.join(
            script_dir, 'config', 'rooms', room_id, 'devices.json'
        )

        mpv_extra_args_raw = self.config.get(
            'Video', 'mpv_extra_args', fallback=''
        ).strip()

        scene_wait_poll_interval = max(1, self.config.getint(
            'System', 'scene_wait_poll_interval', fallback=30
        ))
        scene_wait_max_seconds = max(1, self.config.getint(
            'System', 'scene_wait_max_seconds', fallback=7200
        ))

        startup_mode = self._get_choice(
            'Startup',
            'mode',
            allowed={'classic', 'ambient'},
            fallback='classic',
        )
        ambient_scene = self.config.get(
            'Startup', 'ambient_scene', fallback=''
        ).strip() or json_file_name
        ambient_start_policy = self._get_choice(
            'Startup',
            'ambient_start_policy',
            allowed={'after_initial_connection_attempt', 'wait_for_mqtt'},
            fallback='after_initial_connection_attempt',
        )
        ambient_restart_delay_seconds = self._get_nonnegative_float(
            'Startup', 'ambient_restart_delay_seconds', fallback=2.0
        )
        ambient_error_retry_seconds = self._get_nonnegative_float(
            'Startup', 'ambient_error_retry_seconds', fallback=30.0
        )
        ambient_cycle_cleanup = self._get_choice(
            'Startup',
            'ambient_cycle_cleanup',
            allowed={'scene_only', 'full_stop'},
            fallback='scene_only',
        )
        ambient_stop_behavior = self._get_choice(
            'Startup',
            'ambient_stop_behavior',
            allowed={'suspend_until_restart', 'resume_after_delay'},
            fallback='suspend_until_restart',
        )
        display_backend = self._get_choice(
            'Display',
            'backend',
            allowed={'script', 'cec', 'noop'},
            fallback='noop',
        )
        display_startup_power_state = self._get_choice(
            'Display',
            'startup_power_state',
            allowed={'unchanged', 'standby', 'on'},
            fallback='unchanged',
        )

        if ambient_restart_delay_seconds > scene_wait_max_seconds:
            self.logger.warning(
                "ambient_restart_delay_seconds (%s) exceeds "
                "scene_wait_max_seconds (%s); watchdog may force restart "
                "during ambient cycle gap",
                ambient_restart_delay_seconds,
                scene_wait_max_seconds,
            )

        result = {
            # MQTT
            'broker_ip': self.config.get('MQTT', 'broker_ip', fallback='localhost'),
            'port': self.config.getint('MQTT', 'port', fallback=1883),
            'device_timeout': self.config.getint('MQTT', 'device_timeout', fallback=180),
            'feedback_timeout': self.config.getfloat('MQTT', 'feedback_timeout', fallback=1.0),
            # MQTT timeouts (split from legacy feedback_timeout)
            'command_ack_timeout_ms': self.config.getint(
                'MQTT', 'command_ack_timeout_ms', fallback=200),
            'node_offline_timeout_s': self.config.getint(
                'MQTT', 'node_offline_timeout_s', fallback=5),

            # GPIO
            'button_pin': self.config.getint('GPIO', 'button_pin', fallback=27),
            'debounce_time': self.config.getint('GPIO', 'debounce_time', fallback=300),

            # Room / JSON
            'room_id': room_id,
            'json_file_name': json_file_name,
            'devices_config_path': devices_config_path,

            # System
            'health_check_interval': self.config.getint(
                'System', 'health_check_interval', fallback=60),
            'main_loop_sleep': self.config.getfloat(
                'System', 'main_loop_sleep', fallback=1.0),
            'mqtt_check_interval': self.config.getint(
                'System', 'mqtt_check_interval', fallback=60),
            'scene_processing_sleep': self.config.getfloat(
                'System', 'scene_processing_sleep', fallback=0.20),
            'web_dashboard_port': self.config.getint(
                'System', 'web_dashboard_port', fallback=5000),
            'scene_buffer_time': self.config.getfloat(
                'System', 'scene_buffer_time', fallback=1.0),
            'mqtt_retry_attempts': self.config.getint(
                'System', 'mqtt_retry_attempts', fallback=5),
            'mqtt_retry_sleep': self.config.getfloat(
                'System', 'mqtt_retry_sleep', fallback=2.0),
            'mqtt_connect_timeout': self.config.getint(
                'System', 'mqtt_connect_timeout', fallback=10),
            'mqtt_reconnect_timeout': self.config.getint(
                'System', 'mqtt_reconnect_timeout', fallback=5),
            'mqtt_reconnect_sleep': self.config.getfloat(
                'System', 'mqtt_reconnect_sleep', fallback=0.5),
            'device_cleanup_interval': self.config.getint(
                'System', 'device_cleanup_interval', fallback=60),
            'scene_heartbeat_interval': self.config.getfloat(
                'System', 'scene_heartbeat_interval', fallback=60.0),
            'scene_wait_poll_interval': scene_wait_poll_interval,
            'scene_wait_max_seconds': scene_wait_max_seconds,

            # Startup / ambient mode
            'startup_mode': startup_mode,
            'ambient_scene': ambient_scene,
            'ambient_start_policy': ambient_start_policy,
            'ambient_restart_delay_seconds': ambient_restart_delay_seconds,
            'ambient_error_retry_seconds': ambient_error_retry_seconds,
            'ambient_cycle_cleanup': ambient_cycle_cleanup,
            'ambient_ignore_default_start': self.config.getboolean(
                'Startup', 'ambient_ignore_default_start', fallback=True),
            'ambient_allow_named_scene_start': self.config.getboolean(
                'Startup', 'ambient_allow_named_scene_start', fallback=True),
            'ambient_stop_behavior': ambient_stop_behavior,

            # Video
            'ipc_socket': self.config.get(
                'Video', 'ipc_socket', fallback='/tmp/mpv_socket'),
            'iddle_image': self.config.get(
                'Video', 'iddle_image', fallback='black.png'),
            'video_health_check_interval': self.config.getint(
                'Video', 'health_check_interval', fallback=60),
            'video_max_restart_attempts': self.config.getint(
                'Video', 'max_restart_attempts', fallback=3),
            'video_restart_cooldown': self.config.getint(
                'Video', 'restart_cooldown', fallback=60),
            'video_hwdec': self.config.get(
                'Video', 'hwdec', fallback='auto-safe'),
            'video_output': self.config.get(
                'Video', 'video_output', fallback='gpu'),
            'video_gpu_context': self.config.get(
                'Video', 'gpu_context', fallback='drm'),
            'video_hwdec_codecs': self.config.get(
                'Video', 'hwdec_codecs', fallback='h264,hevc'),
            'video_framedrop': self.config.get(
                'Video', 'framedrop', fallback='vo'),
            'video_mpv_extra_args': (
                shlex.split(mpv_extra_args_raw) if mpv_extra_args_raw else []
            ),

            # Display / HDMI-CEC
            'display_enabled': self.config.getboolean(
                'Display', 'enabled', fallback=False),
            'display_backend': display_backend,
            'display_on_script': resolve_runtime_path(
                self.config.get(
                    'Display',
                    'on_script',
                    fallback='tools/CEC/display_on.sh',
                )
            ),
            'display_off_script': resolve_runtime_path(
                self.config.get(
                    'Display',
                    'off_script',
                    fallback='tools/CEC/display_off.sh',
                )
            ),
            'display_cec_target': self.config.get(
                'Display', 'cec_target', fallback='0').strip(),
            'display_idle_timeout_seconds': self._get_nonnegative_float(
                'Display', 'idle_timeout_seconds', fallback=300.0),
            'display_command_timeout_seconds': self._get_nonnegative_float(
                'Display', 'command_timeout_seconds', fallback=5.0),
            'display_min_seconds_between_power_commands': self._get_nonnegative_float(
                'Display', 'min_seconds_between_power_commands', fallback=15.0),
            'display_standby_on_service_stop': self.config.getboolean(
                'Display', 'standby_on_service_stop', fallback=False),
            'display_startup_power_state': display_startup_power_state,

            # Audio
            'audio_max_init_attempts': self.config.getint(
                'Audio', 'max_init_attempts', fallback=3),
            'audio_init_retry_delay': self.config.getint(
                'Audio', 'init_retry_delay', fallback=5),

            'scenes_dir': scenes_base_path,
            'audio_dir': os.path.join(room_path, audio_dir_name),
            'video_dir': os.path.join(room_path, video_dir_name),
        }
        result.update(self.get_logging_config())
        return result
