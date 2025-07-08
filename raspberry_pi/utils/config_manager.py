#!/usr/bin/env python3

import os
import configparser
import logging
from pathlib import Path

class ConfigManager:
    def __init__(self, config_file=None, logger=None):
        self.log = logger or logging.getLogger(__name__)
        
        if config_file is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(script_dir, "config", "config.ini")
        
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        if not os.path.exists(config_file):
            self.log.error(f"Config missing: {config_file}")
            self.create_default_config()
        
        self.config.read(config_file)
        self.log.info(f"Config loaded from: {self.config_file}")
    
    def create_default_config(self):
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
            'directory': 'scenes'
        }
        
        config['Audio'] = {
            'directory': 'audio'
        }
        
        config['Video'] = {
            'directory': 'videos',
            'ipc_socket': '/tmp/mpv_socket',
            'black_image': 'black.png'
        }
        
        config['System'] = {
            'health_check_interval': '30',
            'main_loop_sleep': '0.5',
            'mqtt_check_interval': '60',
            'scene_processing_sleep': '0.20',
            'web_dashboard_port': '5000',
            'mqtt_retry_attempts': '5',
            'mqtt_retry_sleep': '2',
            'mqtt_connect_timeout': '10',
            'mqtt_reconnect_timeout': '5',
            'mqtt_reconnect_sleep': '0.5',
            'scene_buffer_time': '1'
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
            'log_format': 'detailed'
        }
        
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            config.write(f)
        
        self.log.info(f"Default config created: {self.config_file}")
    
    def get_logging_config(self):
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
                'log_format': 'detailed'
            }
        
        logging_section = self.config['Logging']
        
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        log_level = log_level_map.get(logging_section.get('log_level', 'INFO').upper(), logging.INFO)
        
        log_dir = logging_section.get('log_directory', '').strip()
        log_dir = Path(log_dir) if log_dir else None
        
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
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        return {
            'broker_ip': self.config['MQTT']['BrokerIP'],
            'port': int(self.config['MQTT']['Port']),
            'button_pin': int(self.config['GPIO']['ButtonPin']),
            'room_id': self.config['Room']['ID'],
            'health_check_interval': int(self.config['System'].get('health_check_interval', '30')),
            'main_loop_sleep': float(self.config['System'].get('main_loop_sleep', '0.5')),
            'mqtt_check_interval': int(self.config['System'].get('mqtt_check_interval', '60')),
            'scene_processing_sleep': float(self.config['System'].get('scene_processing_sleep', '0.20')),
            'web_dashboard_port': int(self.config['System'].get('web_dashboard_port', '5000')),
            'mqtt_retry_attempts': int(self.config['System'].get('mqtt_retry_attempts', '5')),
            'mqtt_retry_sleep': float(self.config['System'].get('mqtt_retry_sleep', '2')),
            'mqtt_connect_timeout': int(self.config['System'].get('mqtt_connect_timeout', '10')),
            'mqtt_reconnect_timeout': int(self.config['System'].get('mqtt_reconnect_timeout', '5')),
            'mqtt_reconnect_sleep': float(self.config['System'].get('mqtt_reconnect_sleep', '0.5')),
            'scene_buffer_time': float(self.config['System'].get('scene_buffer_time', '1')),
            'json_file_name': self.config['Json']['json_file_name'],
            'scenes_dir': os.path.join(script_dir, self.config['Scenes']['directory']),
            'audio_dir': os.path.join(script_dir, self.config['Audio']['directory']),
            'video_dir': os.path.join(script_dir, self.config['Video']['directory']),
            'ipc_socket': self.config['Video']['ipc_socket'],
            'black_image': self.config['Video']['black_image'],
            **self.get_logging_config()
        }