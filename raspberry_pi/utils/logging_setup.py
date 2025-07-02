import os
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

def setup_logging(log_level=logging.INFO, log_dir=None, max_file_size=10*1024*1024, backup_count=5):
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
    """
    
    class CleanFormatter(logging.Formatter):
        """Custom formatter with color support for console output."""
        
        # ANSI color codes
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'      # Reset
        }
        
        def __init__(self, use_colors=False):
            super().__init__()
            self.use_colors = use_colors
        
        def format(self, record):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Include milliseconds
            level = record.levelname.ljust(8)
            module = record.name.split('.')[-1][:12].ljust(12)  # Show module name
            
            # Base format
            message = f"[{timestamp}] {level} {module} {record.getMessage()}"
            
            # Add colors for console
            if self.use_colors and record.levelname in self.COLORS:
                color = self.COLORS[record.levelname]
                reset = self.COLORS['RESET']
                message = f"{color}{message}{reset}"
            
            # Add exception info if present
            if record.exc_info:
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
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(CleanFormatter(use_colors=True))
    logger.addHandler(console_handler)
    
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
    main_handler.setFormatter(CleanFormatter(use_colors=False))
    logger.addHandler(main_handler)
    
    # Warning-only log file with rotation
    warning_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'museum-warnings.log',
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    warning_handler.setLevel(logging.WARNING)
    warning_handler.addFilter(LevelFilter(logging.WARNING))  # Only warnings
    warning_handler.setFormatter(CleanFormatter(use_colors=False))
    logger.addHandler(warning_handler)
    
    # Error-only log file with rotation (errors and critical)
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'museum-errors.log',
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(CleanFormatter(use_colors=False))
    logger.addHandler(error_handler)
    
    # Daily rotating log file (info and above)
    daily_handler = logging.handlers.TimedRotatingFileHandler(
        log_dir / 'museum-daily.log',
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days
        encoding='utf-8'
    )
    daily_handler.setLevel(logging.INFO)
    daily_handler.setFormatter(CleanFormatter(use_colors=False))
    logger.addHandler(daily_handler)
    
    # Log startup message
    logger.info(f"Logging initialized - Level: {logging.getLevelName(log_level)}, Dir: {log_dir}")
    logger.info(f"Log files: museum.log (all), museum-warnings.log (warnings), museum-errors.log (errors), museum-daily.log (daily)")
    
    # Setup exception handler for uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    return logger

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