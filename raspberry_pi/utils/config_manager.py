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
        """Extract and validate logging configuration."""
        if not self.config.has_section('Logging'):
            self.logger.error("Logging section not found in config file!")
            raise ValueError("Missing Logging section in configuration")
        
        logging_section = self.config['Logging']
        
        # Map log levels
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        log_level = log_level_map.get(
            logging_section.get('log_level', 'INFO').upper(), 
            logging.INFO
        )
        
        # Handle log directory
        log_dir = logging_section.get('log_directory', '').strip()
        log_dir = Path(log_dir) if log_dir else None
        
        # Convert file size to bytes
        max_file_size = int(logging_section.get('max_file_size_mb', '10')) * 1024 * 1024
        
        return {
            'log_level': log_level,
            'log_directory': log_dir,
            'max_file_size': max_file_size,
            'backup_count': int(logging_section.get('backup_count', '5')),
            'daily_backup_days': int(logging_section.get('daily_backup_days', '30')),
            'console_colors': logging_section.get('console_colors', 'true').lower() == 'true',
            'file_logging': logging_section.get('file_logging', 'true').lower() == 'true',
            'console_logging': logging_section.get('console_logging', 'true').lower() == 'true',
            'log_format': logging_section.get('log_format', 'detailed')
        }
    
    def get_all_config(self):
        """Get all configuration values with proper type conversion."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Configuration mapping with type conversion
        config_map = {
            # MQTT settings
            'broker_ip': (self.config['MQTT']['broker_ip'], str),
            'port': (self.config['MQTT']['port'], int),
            
            # GPIO settings
            'button_pin': (self.config['GPIO']['button_pin'], int),
            'debounce_time': (self.config['GPIO'].get('debounce_time', '300'), int),
            
            # Room settings
            'room_id': (self.config['Room']['room_id'], str),
            'json_file_name': (self.config['Json']['json_file_name'], str),
            
            # System timing settings
            'health_check_interval': (self.config['System'].get('health_check_interval', '60'), int),
            'main_loop_sleep': (self.config['System'].get('main_loop_sleep', '1'), float),
            'mqtt_check_interval': (self.config['System'].get('mqtt_check_interval', '60'), int),
            'scene_processing_sleep': (self.config['System'].get('scene_processing_sleep', '0.20'), float),
            'web_dashboard_port': (self.config['System'].get('web_dashboard_port', '5000'), int),
            'scene_buffer_time': (self.config['System'].get('scene_buffer_time', '1'), float),
            
            # MQTT connection settings
            'mqtt_retry_attempts': (self.config['System'].get('mqtt_retry_attempts', '5'), int),
            'mqtt_retry_sleep': (self.config['System'].get('mqtt_retry_sleep', '2'), float),
            'mqtt_connect_timeout': (self.config['System'].get('mqtt_connect_timeout', '10'), int),
            'mqtt_reconnect_timeout': (self.config['System'].get('mqtt_reconnect_timeout', '5'), int),
            'mqtt_reconnect_sleep': (self.config['System'].get('mqtt_reconnect_sleep', '0.5'), float),
            
            # Video settings
            'ipc_socket': (self.config['Video']['ipc_socket'], str),
            'black_image': (self.config['Video']['black_image'], str),
        }
        
        # Convert values to proper types
        result = {}
        for key, (value, type_converter) in config_map.items():
            result[key] = type_converter(value)
        
        # Add directory paths
        result.update({
            'scenes_dir': os.path.join(script_dir, self.config['Scenes']['directory']),
            'audio_dir': os.path.join(script_dir, self.config['Audio']['directory']),
            'video_dir': os.path.join(script_dir, self.config['Video']['directory']),
        })
        
        # Add logging configuration
        result.update(self.get_logging_config())
        
        return result