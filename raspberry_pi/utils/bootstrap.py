import configparser
import logging
import logging.handlers
import os
import sys
import traceback
from pathlib import Path


BOOTSTRAP_LOGGER_NAME = 'museum.bootstrap'
BOOTSTRAP_LOG_FILE = 'museum-errors.log'


def _resolve_bootstrap_log_dir():
    """Resolve log directory from config.ini Logging.log_directory with a safe default."""
    raspberry_dir = Path(__file__).resolve().parent.parent
    default_dir = raspberry_dir / 'logs'
    config_path = raspberry_dir / 'config' / 'config.ini'

    parser = configparser.ConfigParser()
    if not config_path.exists():
        return default_dir

    try:
        parser.read(config_path)
        configured = parser.get('Logging', 'log_directory', fallback='').strip()
        if configured:
            return Path(configured).expanduser()
    except Exception:
        # Keep startup logging resilient: fallback silently to default path.
        pass

    return default_dir


def setup_bootstrap_logging():
    """Enable early logging before the full logging config is available."""
    logging.basicConfig(
        level=logging.INFO,
        format='[BOOTSTRAP] %(levelname)s %(message)s',
        stream=sys.stderr,
        force=True,
    )

    bootstrap_logger = logging.getLogger(BOOTSTRAP_LOGGER_NAME)
    log_dir = _resolve_bootstrap_log_dir()

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / BOOTSTRAP_LOG_FILE,
            maxBytes=1024 * 1024,
            backupCount=1,
            encoding='utf-8',
        )
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        bootstrap_logger.addHandler(file_handler)
        bootstrap_logger.setLevel(logging.INFO)
        bootstrap_logger.propagate = True
    except Exception as exc:
        sys.stderr.write(f"[BOOTSTRAP] WARNING Failed to initialize bootstrap file logging: {exc}\n")


def log_bootstrap_exception(exc):
    """Log startup failures when full logger is not initialized yet."""
    logging.getLogger(BOOTSTRAP_LOGGER_NAME).critical(
        'Critical startup error before logging initialization: %s', exc
    )
    traceback.print_exc(file=sys.stderr)
