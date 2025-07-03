import os
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

# Global variable to track logger initialization
_logger_initialized = False

def setup_logging(log_level=logging.INFO, log_dir=None, max_file_size=10*1024*1024, 
                  backup_count=5, daily_backup_days=30, console_colors=True,
                  file_logging=True, console_logging=True, log_format='detailed',
                  component_log_levels=None):
    """
    Setup comprehensive logging with console and file handlers.
    
    Creates 4 separate log files:
    - museum.log (all levels)
    - museum-warnings.log (warnings only)
    - museum-errors.log (errors and critical only)
    - museum-daily.log (daily rotating, info and above)
    
    Args:
        log_level: Default logging level (default: INFO)
        log_dir: Custom log directory path (default: ~/Documents/GitHub/museum-system/logs)
        max_file_size: Max file size before rotation in bytes (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        daily_backup_days: Days to keep daily logs (default: 30)
        console_colors: Enable console colors (default: True)
        file_logging: Enable file logging (default: True)
        console_logging: Enable console logging (default: True)
        log_format: Log format style - 'simple', 'detailed', 'json' (default: 'detailed')
        component_log_levels: Dict of component-specific log levels (default: None)
    """
    
    class CleanFormatter(logging.Formatter):
        """Custom formatter with color support and multiple format options."""
        
        # ANSI color codes
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'      # Reset
        }
        
        def __init__(self, use_colors=False, format_style='detailed'):
            super().__init__()
            self.use_colors = use_colors
            self.format_style = format_style
        
        def format(self, record):
            if self.format_style == 'simple':
                message = f"{record.levelname}: {record.getMessage()}"
            elif self.format_style == 'json':
                import json
                log_obj = {
                    'timestamp': datetime.now().isoformat(),
                    'level': record.levelname,
                    'module': record.name,
                    'message': record.getMessage()
                }
                if record.exc_info:
                    log_obj['exception'] = self.formatException(record.exc_info)
                return json.dumps(log_obj)
            else:  # detailed
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                level = record.levelname.ljust(8)
                module = record.name.split('.')[-1][:12].ljust(12)
                message = f"[{timestamp}] {level} {module} {record.getMessage()}"
            
            # Add colors for console (not for JSON format)
            if self.use_colors and self.format_style != 'json' and record.levelname in self.COLORS:
                color = self.COLORS[record.levelname]
                reset = self.COLORS['RESET']
                message = f"{color}{message}{reset}"
            
            # Add exception info if present (not for JSON format)
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
    
    # Get or create logger
    logger = logging.getLogger('museum')
    
    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(log_level)
    logger.propagate = False  # Prevent duplicate logs
    
    # Console handler
    if console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(CleanFormatter(use_colors=console_colors, format_style=log_format))
        logger.addHandler(console_handler)
    
    # File logging
    if file_logging:
        # Setup log directory
        if log_dir is None:
            log_dir = Path.home() / "Documents" / "GitHub" / "museum-system" / "logs"
        else:
            log_dir = Path(log_dir)
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main rotating log file (all levels)
        main_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'museum.log',
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(main_handler)
        
        # Warning-only log file with rotation
        warning_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'museum-warnings.log',
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        warning_handler.setLevel(logging.WARNING)
        warning_handler.addFilter(LevelFilter(logging.WARNING))
        warning_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(warning_handler)
        
        # Error-only log file with rotation
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'museum-errors.log',
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(error_handler)
        
        # Daily rotating log file
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            log_dir / 'museum-daily.log',
            when='midnight',
            interval=1,
            backupCount=daily_backup_days,
            encoding='utf-8'
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(CleanFormatter(use_colors=False, format_style=log_format))
        logger.addHandler(daily_handler)
    
    # Set component-specific log levels
    if component_log_levels:
        for component, level in component_log_levels.items():
            component_logger = logging.getLogger(f'museum.{component}')
            component_logger.setLevel(level)
            logger.info(f"Set {component} log level to {logging.getLevelName(level)}")
    
    # Log startup message
    logger.info(f"Logging initialized - Level: {logging.getLevelName(log_level)}")
    if file_logging:
        logger.info(f"Log directory: {log_dir}")
        logger.info(f"Log files: museum.log (all), museum-warnings.log (warnings), museum-errors.log (errors), museum-daily.log (daily)")
    
    # Setup exception handler for uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    return logger

def setup_logging_from_config(config_dict):
    """Setup logging using configuration dictionary"""
    return setup_logging(
        log_level=config_dict.get('log_level', logging.INFO),
        log_dir=config_dict.get('log_directory'),
        max_file_size=config_dict.get('max_file_size', 10*1024*1024),
        backup_count=config_dict.get('backup_count', 5),
        daily_backup_days=config_dict.get('daily_backup_days', 30),
        console_colors=config_dict.get('console_colors', True),
        file_logging=config_dict.get('file_logging', True),
        console_logging=config_dict.get('console_logging', True),
        log_format=config_dict.get('log_format', 'detailed'),
        component_log_levels=config_dict.get('component_log_levels', {})
    )

def get_logger(name=None):
    """Get a child logger with the specified name."""
    if name:
        return logging.getLogger(f'museum.{name}')
    return logging.getLogger('museum')

# Convenience function for testing
def test_logging():
    """Test function to demonstrate logging capabilities."""
    logger = setup_logging(log_level=logging.DEBUG)
    
    logger.debug("Debug message - detailed diagnostic info")
    logger.info("Info message - general information")
    logger.warning("Warning message - something unusual happened")
    logger.error("Error message - something went wrong")
    logger.critical("Critical message - serious error occurred")
    
    # Test child logger
    child_logger = get_logger('test_module')
    child_logger.info("Message from child logger")
    child_logger.warning("Warning from child logger")
    child_logger.error("Error from child logger")
    
    # Test exception logging
    try:
        1 / 0
    except Exception:
        logger.exception("Exception occurred during division")
    
    print("\nLog files created:")
    print("- museum.log (all levels)")
    print("- museum-warnings.log (warnings only)")
    print("- museum-errors.log (errors and critical)")
    print("- museum-daily.log (daily rotation, info+)")

if __name__ == "__main__":
    test_logging()