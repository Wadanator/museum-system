#!/usr/bin/env python3
"""
Bootstrap logging setup for early-stage startup error capture.

Provides a minimal logging configuration that is available before the full
logging system is initialized, writing critical startup errors to a rotating
log file in addition to stderr.
"""

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
    """
    Resolve the log directory from config.ini with a safe fallback.

    Reads the log directory path from the [Logging] section of config.ini.
    Falls back silently to the default 'logs' directory if the config file
    is missing, unreadable, or does not specify a path.

    Returns:
        Path: Resolved log directory path.
    """
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
        # Keep startup logging resilient: fall back silently to default path
        pass

    return default_dir


def setup_bootstrap_logging():
    """
    Enable early logging before the full logging configuration is available.

    Configures a basic stderr handler for INFO-level output and attaches a
    rotating file handler to the bootstrap logger for ERROR-level messages.
    File handler failures are reported to stderr but do not raise exceptions.
    """
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
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        )
        bootstrap_logger.addHandler(file_handler)
        bootstrap_logger.setLevel(logging.INFO)
        bootstrap_logger.propagate = True
    except Exception as exc:
        sys.stderr.write(
            f"[BOOTSTRAP] WARNING Failed to initialize bootstrap file logging: {exc}\n"
        )


def log_bootstrap_exception(exc):
    """
    Log a critical startup failure occurring before the full logger is ready.

    Writes the exception to the bootstrap logger at CRITICAL level and
    prints the full traceback to stderr.

    Args:
        exc: The exception instance to log.
    """
    logging.getLogger(BOOTSTRAP_LOGGER_NAME).critical(
        'Critical startup error before logging initialization: %s', exc
    )
    traceback.print_exc(file=sys.stderr)