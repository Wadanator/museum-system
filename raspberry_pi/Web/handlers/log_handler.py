#!/usr/bin/env python3
"""Web logging handler for capturing logs for the dashboard."""

import logging
from datetime import datetime
from ..config import Config

class WebLogHandler(logging.Handler):
    """Custom logging handler to capture logs for the web dashboard."""
    
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.setLevel(logging.DEBUG)  # Capture all log levels
        self.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        """Format and store log entries for web display."""
        # Extract the last part of the logger name for cleaner display
        module = record.name.split('.')[-1] if '.' in record.name else record.name
        if module.startswith('utils.'):
            module = module.split('.')[-1]  # Handle utils.<module> case
        module = module.strip()  # Remove padding for web display
        
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'level': record.levelname,
            'module': module,
            'message': record.getMessage()
        }
        if record.exc_info:
            log_entry['exception'] = self.format(record).split('\n')[1:]  # Include stack trace if available
        self.dashboard.add_log_entry(log_entry)