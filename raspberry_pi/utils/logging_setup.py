import os
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

def get_default_log_dir():
    """Get the default log directory relative to the project root."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "logs"

def setup_logging(log_level=logging.INFO, log_dir=None, max_file_size=10*1024*1024, 
                 backup_count=5, daily_backup_days=30, console_colors=True,
                 file_logging=True, console_logging=False, log_format='detailed'):
    """
    Setup comprehensive logging with console and file handlers.
    Creates 4 log files: main, warnings, errors, and daily rotating logs.
    """
    
    class CleanFormatter(logging.Formatter):
        """Custom formatter with color support and multiple format styles."""
        COLORS = {
            'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m',
            'ERROR': '\033[31m', 'CRITICAL': '\033[35m', 'RESET': '\033[0m'
        }
        
        def __init__(self, use_colors=False, format_style='detailed'):
            super().__init__()
            self.use_colors = use_colors
            self.format_style = format_style
        
        def format(self, record):
            # Extract and format module name
            module = record.name.split('.')[-1] if '.' in record.name else record.name
            if module.startswith('utils.'):
                module = module.split('.')[-1]
            module = module[:12].ljust(12)
            
            # Format based on style
            if self.format_style == 'simple':
                message = f"{record.levelname}: {record.getMessage()}"
            elif self.format_style == 'json':
                import json
                log_obj = {
                    'timestamp': datetime.now().isoformat(),
                    'level': record.levelname,
                    'module': module.strip(),
                    'message': record.getMessage()
                }
                if record.exc_info:
                    log_obj['exception'] = self.formatException(record.exc_info)
                return json.dumps(log_obj)
            else:  # detailed
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                level = record.levelname.ljust(8)
                message = f"[{timestamp}] {level} {module} {record.getMessage()}"
            
            # Apply colors for console output
            if self.use_colors and self.format_style != 'json' and record.levelname in self.COLORS:
                color = self.COLORS[record.levelname]
                reset = self.COLORS['RESET']
                message = f"{color}{message}{reset}"
            
            # Add exception info if present
            if record.exc_info and self.format_style != 'json':
                message += '\n' + self.formatException(record.exc_info)
            
            return message
    
    class LevelFilter(logging.Filter):
        """Filter to only allow specific log levels."""
        def __init__(self, level):
            super().__init__()
            self.level = level
        
        def filter(self, record):
            return record.levelno == self.level
    
    # Initialize logger
    logger = logging.getLogger('museum')
    if logger.handlers:  # Prevent duplicate handlers
        return logger
    
    logger.setLevel(log_level)
    logger.propagate = False
    
    # Setup console handler
    if console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(CleanFormatter(use_colors=console_colors, format_style=log_format))
        logger.addHandler(console_handler)
    
    # Setup file logging
    if file_logging:
        # Create log directories
        log_dir = Path(log_dir) if log_dir else get_default_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        daily_log_dir = log_dir / "daily"
        daily_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log directory info
        logger_temp = logging.getLogger('museum.setup')
        logger_temp.info(f"Main log directory: {log_dir.resolve()}")
        logger_temp.info(f"Daily log directory: {daily_log_dir.resolve()}")
        
        # Main rotating log file (all levels)
        main_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'museum.log', maxBytes=max_file_size, 
            backupCount=backup_count, encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(main_handler)
        
        # Warning-only log file
        warning_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'museum-warnings.log', maxBytes=max_file_size,
            backupCount=backup_count, encoding='utf-8'
        )
        warning_handler.setLevel(logging.WARNING)
        warning_handler.addFilter(LevelFilter(logging.WARNING))
        warning_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(warning_handler)
        
        # Error-only log file
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'museum-errors.log', maxBytes=max_file_size,
            backupCount=backup_count, encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(error_handler)
        
        # Daily rotating log file
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            daily_log_dir / 'museum-daily.log', when='midnight', interval=1,
            backupCount=daily_backup_days, encoding='utf-8'
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(daily_handler)
    
    # Log startup message
    logger.info(f"Logging initialized - Level: {logging.getLevelName(log_level)}")
    
    # Setup global exception handler
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    return logger

def setup_logging_from_config(config_dict):
    """Setup logging using configuration dictionary."""
    return setup_logging(
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

def get_logger(name=None):
    """Get a child logger with the specified name."""
    if name:
        return logging.getLogger(f'museum.{name}')
    return logging.getLogger('museum')