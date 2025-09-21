#!/usr/bin/env python3
"""Configuration settings for the Web Dashboard."""

from pathlib import Path

class Config:
    """Centralized configuration settings for the WebDashboard."""
    SECRET_KEY = 'museum_controller_secret'  # Secret key for Flask session security
    MAX_LOG_ENTRIES = 1000  # Maximum number of log entries to store in memory
    DEFAULT_PORT = 5000  # Default port for the web server
    
    # Define base paths relative to the script's location
    _BASE_DIR = Path(__file__).resolve().parent.parent
    LOG_DIR = _BASE_DIR / "logs"  # Directory for log files
    STATS_FILE = _BASE_DIR / "Web" / "stats.json"  # File for storing dashboard stats
    SCENES_DIR = _BASE_DIR / "scenes"  # Directory for scene configuration files
    COMMANDS_DIR = _BASE_DIR / "scenes" / "commands"  # Directory for command configuration files

    # Authentication credentials (must be changed in production)
    USERNAME = 'admin'
    PASSWORD = 'admin'