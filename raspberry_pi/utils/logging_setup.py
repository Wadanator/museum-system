import os
import logging
import logging.handlers
import sys
import json
from datetime import datetime
from pathlib import Path

def get_default_log_dir():
    """Get the default log directory relative to the project root."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "logs"

def setup_logging_from_config(config_dict):
    """Setup logging using configuration dictionary with component-specific levels."""
    component_levels = config_dict.get('component_levels', {})
    
    logger = setup_logging(
        log_level=config_dict.get('log_level', logging.INFO),
        log_dir=config_dict.get('log_directory'),
        max_file_size=config_dict.get('max_file_size', 10*1024*1024),
        backup_count=config_dict.get('backup_count', 5),
        daily_backup_days=config_dict.get('daily_backup_days', 30),
        console_colors=config_dict.get('console_colors', True),
        file_logging=config_dict.get('file_logging', True),
        console_logging=config_dict.get('console_logging', True),
        log_format=config_dict.get('log_format', 'detailed')
    )
    
    _apply_component_log_levels(component_levels)
    return logger

def _apply_component_log_levels(component_levels):
    """Apply specific log levels to different components."""
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO, 
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    # Default levels - keys must be lowercase to match get_logger normalization
    default_levels = {
        'museum.main': 'INFO',
        'museum.scene_parser': 'INFO',
        'museum.mqtt': 'INFO',
        'museum.audio': 'INFO', 
        'museum.video': 'INFO',
        'museum.web': 'INFO',
        'museum.btn_handler': 'INFO',
        
        # Suppressions (Defaults)
        'museum.sys_monitor': 'ERROR',
        'museum.config': 'ERROR',
        'museum.setup': 'ERROR',
        'museum.mqtt_handler': 'WARNING',
        'museum.mqtt_feedback': 'WARNING',
        'museum.mqtt_devices': 'WARNING',
        
        # Libraries
        'werkzeug': 'ERROR',
        'flask.app': 'ERROR',
        'urllib3': 'ERROR',
        'paho': 'ERROR',
        'socketio': 'ERROR',
        'engineio': 'ERROR',
    }
    
    # Merge user config (which ConfigParser lowercases) with defaults
    # We force lowercase on keys just to be safe
    all_levels = default_levels.copy()
    for k, v in component_levels.items():
        all_levels[k.lower()] = v
    
    for logger_name, level_str in all_levels.items():
        level = level_map.get(level_str.upper(), logging.INFO)
        logging.getLogger(logger_name).setLevel(level)

def setup_logging(log_level=logging.INFO, log_dir=None, max_file_size=10*1024*1024, 
                 backup_count=5, daily_backup_days=30, console_colors=True,
                 file_logging=True, console_logging=False, log_format='detailed'):
    
    class CleanFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m',
            'ERROR': '\033[31m', 'CRITICAL': '\033[35m', 'RESET': '\033[0m'
        }
        
        def __init__(self, use_colors=False, format_style='detailed'):
            super().__init__()
            self.use_colors = use_colors
            self.format_style = format_style
        
        def format(self, record):
            # Extract module name
            module = record.name.split('.')[-1] if '.' in record.name else record.name
            if module.startswith('utils.'):
                module = module.split('.')[-1]
            
            # Aliases for cleaner logs
            # Keys here must match the lowercase module name
            module_aliases = {
                'mqtt_client': 'mqtt',
                'mqtt_handler': 'mqtt_msg', 
                'mqtt_feedback_tracker': 'mqtt_fb',
                'mqtt_device_registry': 'mqtt_dev',
                'scene_parser': 'scene',   # Opravené pre zhodu s lowercase
                'audio_handler': 'audio',
                'video_handler': 'video',
                'button_handler': 'button',
                'system_monitor': 'monitor',
                'web_dashboard': 'web'
            }
            
            # Normalize to lower for lookup
            module_key = module.lower()
            if module_key in module_aliases:
                 module = module_aliases[module_key]
            
            module = module[:10].ljust(10)
            
            if self.format_style == 'simple':
                message = f"{record.levelname}: {record.getMessage()}"
            elif self.format_style == 'json':
                log_obj = {
                    'timestamp': datetime.now().isoformat(),
                    'level': record.levelname,
                    'module': module.strip(),
                    'message': record.getMessage()
                }
                if record.exc_info:
                    log_obj['exception'] = self.formatException(record.exc_info)
                return json.dumps(log_obj)
            else:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                level = record.levelname.ljust(7)
                message = f"[{timestamp}] {level} {module} {record.getMessage()}"
            
            if self.use_colors and self.format_style != 'json' and record.levelname in self.COLORS:
                color = self.COLORS[record.levelname]
                reset = self.COLORS['RESET']
                message = f"{color}{message}{reset}"
            
            if record.exc_info and self.format_style != 'json':
                message += '\n' + self.formatException(record.exc_info)
            
            return message
    
    class LevelFilter(logging.Filter):
        def __init__(self, level):
            super().__init__()
            self.level = level
        def filter(self, record):
            return record.levelno == self.level
    
    logger = logging.getLogger('museum')
    if logger.handlers:
        return logger
    
    logger.setLevel(log_level)
    logger.propagate = False
    
    if console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(CleanFormatter(use_colors=console_colors, format_style=log_format))
        logger.addHandler(console_handler)
    
    if file_logging:
        log_dir = Path(log_dir) if log_dir else get_default_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        daily_log_dir = log_dir / "daily"
        daily_log_dir.mkdir(parents=True, exist_ok=True)
        
        main_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'museum.log', maxBytes=max_file_size, backupCount=backup_count, encoding='utf-8'
        )
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(main_handler)
        
        warning_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'museum-warnings.log', maxBytes=max_file_size//2, backupCount=backup_count, encoding='utf-8'
        )
        warning_handler.setLevel(logging.WARNING)
        warning_handler.addFilter(LevelFilter(logging.WARNING))
        warning_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(warning_handler)
        
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'museum-errors.log', maxBytes=max_file_size//4, backupCount=backup_count, encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(error_handler)
        
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            daily_log_dir / 'museum-daily.log', when='midnight', interval=1, backupCount=daily_backup_days, encoding='utf-8'
        )
        daily_handler.setLevel(logging.DEBUG)
        daily_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(daily_handler)
    
    logger.info(f"Logging initialized - Level: {logging.getLevelName(log_level)}")
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    return logger

def get_logger(name=None):
    """Get a child logger with the specified name (normalized to lowercase)."""
    if name:
        # TOTO je kľúčová oprava: vynútenie malých písmen
        return logging.getLogger(f'museum.{name.lower()}')
    return logging.getLogger('museum')