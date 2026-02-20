import os
import configparser
import logging
import shutil
from pathlib import Path
from utils.logging_setup import get_logger

class ConfigManager:
    def __init__(self, config_file=None, logger=None):
        self.logger = logger or get_logger('config')
        
        # Získame cestu k priečinku raspberry_pi
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Nastavenie cesty ku config súboru
        if config_file is None:
            config_file = os.path.join(script_dir, "config", "config.ini")
        
        # --- AUTO-CREATE LOGIC ---
        # Ak config.ini neexistuje, ale existuje example, vytvoríme ho
        example_file = os.path.join(script_dir, "config", "config.ini.example")
        if not os.path.exists(config_file) and os.path.exists(example_file):
            try:
                shutil.copy2(example_file, config_file)
                # Použijeme print, lebo logger ešte nemusí byť plne inicializovaný
                print(f"🔧 Config file created from default template: {config_file}")
            except Exception as e:
                print(f"❌ Failed to create config file from template: {e}")
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
        if 'Logging' not in self.config:
            # Fallback ak sekcia chýba
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
        
        # Get component-specific log levels
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
            'component_levels': component_levels
        }
    
    def get_all_config(self):
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Získame názvy priečinkov a ID miestnosti
            scenes_dir_name = self.config.get('Scenes', 'directory', fallback='scenes')
            room_id = self.config.get('Room', 'room_id', fallback='room1')
            audio_dir_name = self.config.get('Audio', 'directory', fallback='audio')
            video_dir_name = self.config.get('Video', 'directory', fallback='videos')

            # Základná cesta k scenes
            scenes_base_path = os.path.join(script_dir, scenes_dir_name)
            
            # Cesta ku konkrétnej miestnosti
            room_path = os.path.join(scenes_base_path, room_id)

            result = {
                # MQTT
                'broker_ip': self.config.get('MQTT', 'broker_ip', fallback='localhost'),
                'port': self.config.getint('MQTT', 'port', fallback=1883),
                'device_timeout': self.config.getint('MQTT', 'device_timeout', fallback=180),
                'feedback_timeout': self.config.getfloat('MQTT', 'feedback_timeout', fallback=1.0),
                
                # GPIO
                'button_pin': self.config.getint('GPIO', 'button_pin', fallback=27),
                'debounce_time': self.config.getint('GPIO', 'debounce_time', fallback=300),
                
                # Room/Json
                'room_id': room_id,
                'json_file_name': self.config.get('Json', 'json_file_name', fallback='default.json'),
                
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
                'device_cleanup_interval': self.config.getint('System', 'device_cleanup_interval', fallback=60),
                
                # Video
                'ipc_socket': self.config.get('Video', 'ipc_socket', fallback='/tmp/mpv_socket'),
                'iddle_image': self.config.get('Video', 'iddle_image', fallback='black.png'),
                'video_health_check_interval': self.config.getint('Video', 'health_check_interval', fallback=60),
                'video_max_restart_attempts': self.config.getint('Video', 'max_restart_attempts', fallback=3),
                'video_restart_cooldown': self.config.getint('Video', 'restart_cooldown', fallback=60),
                
                # Audio
                'audio_max_init_attempts': self.config.getint('Audio', 'max_init_attempts', fallback=3),
                'audio_init_retry_delay': self.config.getint('Audio', 'init_retry_delay', fallback=5),
                
                'scenes_dir': scenes_base_path,
                'audio_dir': os.path.join(room_path, audio_dir_name),
                'video_dir': os.path.join(room_path, video_dir_name),
            }
            result.update(self.get_logging_config())
            return result