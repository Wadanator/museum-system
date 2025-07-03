#!/usr/bin/env python3

import os
import configparser
import logging
from pathlib import Path

class ConfigManager:
    def __init__(self, config_file=None, logger=None):
        self.log = logger or logging.getLogger(__name__)
        
        # Set default config file path
        if config_file is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(script_dir, "config", "config.ini")
        
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # Create config if it doesn't exist
        if not os.path.exists(config_file):
            self.log.error(f"Config missing: {config_file}")
            self.create_default_config()
        
        # Load configuration
        self.config.read(config_file)
        self.log.info(f"Config loaded from: {config_file}")
    
    def create_default_config(self):
        """Create a default configuration file"""
        config = configparser.ConfigParser()
        
        config['MQTT'] = {
            'BrokerIP': '192.168.0.127',
            'Port': '1883'
        }
        
        config['GPIO'] = {
            'ButtonPin': '27'
        }
        
        config['Room'] = {
            'ID': 'room1'
        }
        
        config['Scenes'] = {
            'Directory': 'scenes'
        }
        
        config['Audio'] = {
            'Directory': 'audio'
        }
        
        config['System'] = {
            'health_check_interval': '30',
            'main_loop_sleep': '0.5',
            'mqtt_check_interval': '60',
            'scene_processing_sleep': '0.20'
        }
        
        config['Json'] = {
            'json_file_name': 'intro.json'
        }
        
        config['Logging'] = {
            'log_level': 'INFO',
            'log_directory': '',
            'max_file_size_mb': '10',
            'backup_count': '5',
            'daily_backup_days': '30',
            'console_colors': 'true',
            'file_logging': 'true',
            'console_logging': 'true',
            'log_format': 'detailed',
            'component_log_levels': 'mqtt:WARNING,audio:INFO,button:DEBUG'
        }
        
        # Create directory and write config file
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            config.write(f)
        
        self.log.info(f"Default config created: {self.config_file}")
    
    def get_logging_config(self):
        """Get logging configuration values"""
        if not self.config.has_section('Logging'):
            self.log.warning("Logging section not found in config, using defaults")
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
                'component_log_levels': {}
            }
        
        logging_section = self.config['Logging']
        
        # Convert log level string to logging constant
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        log_level = log_level_map.get(logging_section.get('log_level', 'INFO').upper(), logging.INFO)
        
        # Handle log directory
        log_dir = logging_section.get('log_directory', '').strip()
        log_dir = Path(log_dir) if log_dir else None
        
        # Convert file size from MB to bytes
        max_file_size = int(logging_section.get('max_file_size_mb', '10')) * 1024 * 1024
        
        # Parse component log levels
        component_levels = {}
        component_str = logging_section.get('component_log_levels', '')
        if component_str:
            for item in component_str.split(','):
                if ':' in item:
                    component, level = item.strip().split(':', 1)
                    level_upper = level.upper()
                    if level_upper in log_level_map:
                        component_levels[component.strip()] = log_level_map[level_upper]
        
        return {
            'log_level': log_level,
            'log_directory': log_dir,
            'max_file_size': max_file_size,
            'backup_count': int(logging_section.get('backup_count', '5')),
            'daily_backup_days': int(logging_section.get('daily_backup_days', '30')),
            'console_colors': logging_section.get('console_colors', 'true').lower() == 'true',
            'file_logging': logging_section.get('file_logging', 'true').lower() == 'true',
            'console_logging': logging_section.get('console_logging', 'true').lower() == 'true',
            'log_format': logging_section.get('log_format', 'detailed'),
            'component_log_levels': component_levels
        }
    
    def get_all_config(self):
        """Get all configuration as a single dictionary"""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        return {
            # MQTT
            'broker_ip': self.config['MQTT']['BrokerIP'],
            'port': int(self.config['MQTT']['Port']),
            
            # GPIO
            'button_pin': int(self.config['GPIO']['ButtonPin']),
            
            # Room
            'room_id': self.config['Room']['ID'],
            
            # System
            'health_check_interval': int(self.config['System'].get('health_check_interval', '30')),
            'main_loop_sleep': float(self.config['System'].get('main_loop_sleep', '0.5')),
            'mqtt_check_interval': int(self.config['System'].get('mqtt_check_interval', '60')),
            'scene_processing_sleep': float(self.config['System'].get('scene_processing_sleep', '0.20')),
            
            # JSON
            'json_file_name': self.config['Json']['json_file_name'],
            
            # Directories - now using config values properly
            'scenes_dir': os.path.join(script_dir, self.config['Scenes']['Directory']),
            'audio_dir': os.path.join(script_dir, self.config['Audio']['Directory']),
            'video_dir': os.path.join(script_dir, self.config['Video']['Directory']),
            
            # Logging (merged)
            **self.get_logging_config()
        }