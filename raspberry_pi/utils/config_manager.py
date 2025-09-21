# raspberry_pi/utils/config_manager.py - Updated with component log levels

#!/usr/bin/env python3

import os
import configparser
import logging
from pathlib import Path
from utils.logging_setup import get_logger

class ConfigManager:
    def __init__(self, config_file=None, logger=None):
        self.logger = logger or get_logger('config')
        
        # Set config file path
        if config_file is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(script_dir, "config", "config.ini")
        
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # Load config file
        if not os.path.exists(config_file):
            self.logger.critical(f"Config file not found: {config_file}")
            raise FileNotFoundError(f"Configuration file missing: {config_file}")
        
        self.config.read(config_file)
        self.logger.info(f"Config loaded from: {self.config_file}")
    
    def get_logging_config(self):
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
        
        # Get component-specific log levels if LogLevels section exists
        component_levels = {}
        if self.config.has_section('LogLevels'):
            component_levels = dict(self.config['LogLevels'].items())
        
        return {
            'log_level': log_level,
            'log_directory': Path(section.get('log_directory', '').strip()) if section.get('log_directory') else None,
            'max_file_size': section.getint('max_file_size_mb', 10) * 1024 * 1024,
            'backup_count': section.getint('backup_count', 5),
            'daily_backup_days': section.getint('daily_backup_days', 30),
            'console_colors': section.getboolean('console_colors', True),
            'file_logging': section.getboolean('file_logging', True),
            'console_logging': section.getboolean('console_logging', True),
            'log_format': section.get('log_format', 'detailed'),
            'component_levels': component_levels  # NEW: component-specific levels
        }
    
    def get_all_config(self):
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            result = {
                # MQTT
                'broker_ip': self.config.get('MQTT', 'broker_ip'),
                'port': self.config.getint('MQTT', 'port'),
                'device_timeout': self.config.getint('MQTT', 'device_timeout', fallback=180),  # ADD THIS LINE
                'feedback_timeout': self.config.getfloat('MQTT', 'feedback_timeout', fallback=1.0),  # ADD THIS LINE
                
                # GPIO
                'button_pin': self.config.getint('GPIO', 'button_pin'),
                'debounce_time': self.config.getint('GPIO', 'debounce_time', fallback=300),
                
                # Room/Json
                'room_id': self.config.get('Room', 'room_id'),
                'json_file_name': self.config.get('Json', 'json_file_name'),
                
                # System
                'health_check_interval': self.config.getint('System', 'health_check_interval', fallback=60),
                'main_loop_sleep': self.config.getfloat('System', 'main_loop_sleep', fallback=1.0),
                'mqtt_check_interval': self.config.getint('System', 'mqtt_check_interval', fallback=60),
                'scene_processing_sleep': self.config.getfloat('System', 'scene_processing_sleep', fallback=0.20),
                'web_dashboard_port': self.config.getint('System', 'web_dashboard_port', fallback=5000),
                'scene_buffer_time': self.config.getfloat('System', 'scene_buffer_time', fallback=1.0),
                'mqtt_retry_attempts': self.config.getint('System', 'mqtt_retry_attempts', fallback=5),
                'mqtt_retry_sleep': self.config.getfloat('System', 'mqtt_retry_sleep', fallback=2.0),
                'mqtt_connect_timeout': self.config.getint('System', 'mqtt_connect_timeout', fallback=10),
                'mqtt_reconnect_timeout': self.config.getint('System', 'mqtt_reconnect_timeout', fallback=5),
                'mqtt_reconnect_sleep': self.config.getfloat('System', 'mqtt_reconnect_sleep', fallback=0.5),
                'device_cleanup_interval': self.config.getint('System', 'device_cleanup_interval', fallback=60),  # ADD THIS LINE
                
                # Video
                'ipc_socket': self.config.get('Video', 'ipc_socket'),
                'black_image': self.config.get('Video', 'black_image'),
                'video_health_check_interval': self.config.getint('Video', 'health_check_interval', fallback=60),  # ADD THIS LINE
                'video_max_restart_attempts': self.config.getint('Video', 'max_restart_attempts', fallback=3),  # ADD THIS LINE
                'video_restart_cooldown': self.config.getint('Video', 'restart_cooldown', fallback=60),  # ADD THIS LINE
                
                # Audio - ADD THESE 2 LINES
                'audio_max_init_attempts': self.config.getint('Audio', 'max_init_attempts', fallback=3),
                'audio_init_retry_delay': self.config.getint('Audio', 'init_retry_delay', fallback=5),
                
                # Paths
                'scenes_dir': os.path.join(script_dir, self.config.get('Scenes', 'directory')),
                'audio_dir': os.path.join(script_dir, self.config.get('Audio', 'directory')),
                'video_dir': os.path.join(script_dir, self.config.get('Video', 'directory')),
            }
            result.update(self.get_logging_config())
            return result