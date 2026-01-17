#!/usr/bin/env python3
"""Refactored Web Dashboard - Main dashboard class."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from flask import request as flask_request
from flask_socketio import emit

from .config import Config
from .handlers.log_handler import WebLogHandler
from .utils.helpers import format_uptime

class WebDashboard:
    """Web interface for controlling and monitoring the museum system."""
    
    def __init__(self, controller, app, socketio):
        self.controller = controller
        self.app = app
        self.socketio = socketio
        self.log = self._setup_logger()
        
        self.log_buffer: List[Dict] = []  # In-memory log storage
        self.stats = {
            'total_scenes_played': 0,
            'scene_play_counts': {},
            'total_uptime': 0,
            'last_start_time': time.monotonic(),
            'connected_devices': {}
        }
        
        self._setup_logging()
        self._load_stats()
        self._setup_socketio_handlers()

    def _setup_logger(self):
        """Setup logger for dashboard."""
        from utils.logging_setup import get_logger
        return get_logger('web')

    def _setup_logging(self):
        """Configure logging handlers for the dashboard."""
        web_handler = WebLogHandler(self)
        for logger_name in ('museum', ''):
            logger = logging.getLogger(logger_name)
            logger.addHandler(web_handler)
        for logger_name in ('werkzeug', 'flask'):
            logging.getLogger(logger_name).setLevel(logging.ERROR)  # Suppress Flask/Werkzeug logs
        self.load_existing_logs()

    def _setup_socketio_handlers(self):
        """Setup SocketIO event handlers."""
        @self.socketio.on('connect')
        def handle_connect(auth=None):
            """Handle new SocketIO client connections with authentication."""
            # FIX: Kontrola auth z handshake dát (spoľahlivejšie pre WebSockets)
            is_valid = False
            if auth and 'username' in auth and 'password' in auth:
                is_valid = self._check_auth(auth['username'], auth['password'])
            else:
                # Fallback na standardnu Flask basic auth (pre polling)
                flask_auth = flask_request.authorization
                if flask_auth:
                    is_valid = self._check_auth(flask_auth.username, flask_auth.password)

            if not is_valid:
                return False  # Reject unauthorized connections
            
            try:
                # FIX: ODOŠLEME STAV IHNEĎ ABY UI NEUKAZOVALO POMMLČKY
                emit('status_update', self._get_status_data())
                emit('log_history', self.log_buffer)
                emit('stats_update', self.stats)
                self.log.info("New SocketIO client connected and authenticated")
            except Exception as e:
                self.log.error(f"Error on connect: {e}")

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle SocketIO client disconnections."""
            self.log.info("SocketIO client disconnected")

        @self.socketio.on('request_logs')
        def handle_log_request():
            """Send log history to requesting SocketIO client."""
            try:
                emit('log_history', self.log_buffer)
            except Exception as e:
                self.log.error(f"Error handling log request: {e}")

        @self.socketio.on('request_status')
        def handle_status_request():
            """Send current system status to requesting SocketIO client."""
            try:
                emit('status_update', self._get_status_data())
            except Exception as e:
                self.log.error(f"Error handling status request: {e}")

        @self.socketio.on('request_stats')
        def handle_stats_request():
            """Send updated statistics to requesting SocketIO client."""
            try:
                self.update_stats()
                emit('stats_update', self.stats)
            except Exception as e:
                self.log.error(f"Error handling stats request: {e}")

    def _check_auth(self, username, password):
        """Check authentication credentials."""
        return username == Config.USERNAME and password == Config.PASSWORD

    def _get_status_data(self):
        """Get current system status data."""
        return {
            'room_id': getattr(self.controller, 'room_id', 'Unknown'),
            'scene_running': getattr(self.controller, 'scene_running', False),
            'mqtt_connected': self.controller.mqtt_client.is_connected() if self.controller.mqtt_client else False,
            'uptime': self.get_uptime(),
            'log_count': len(self.log_buffer)
        }

    def get_uptime(self):
        """Get system uptime in seconds."""
        return time.monotonic() - getattr(self.controller, 'start_time', time.monotonic())

    def load_existing_logs(self):
        """Load recent log entries from the main log file."""
        try:
            if not Config.LOG_DIR.exists():
                self.log.info(f"Log directory does not exist: {Config.LOG_DIR}")
                return
            main_log = Config.LOG_DIR / 'museum.log'
            if main_log.exists():
                with open(main_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-100:]  # Load last 100 lines
                    for line in lines:
                        if line.strip() and line.startswith('['):
                            try:
                                timestamp, rest = line.strip().split('] ', 1)
                                level, module, message = rest.split(' ', 2)
                                self.log_buffer.append({
                                    'timestamp': timestamp[1:],
                                    'level': level.strip(),
                                    'module': module.strip(),
                                    'message': message,
                                    'from_file': True
                                })
                            except ValueError:
                                continue  # Skip malformed log lines
                    self.log.info(f"Loaded {len([log for log in self.log_buffer if log.get('from_file')])} log entries from file")
            else:
                self.log.info(f"Main log file does not exist: {main_log}")
        except Exception as e:
            self.log.error(f"Error loading existing logs: {e}")

    def _load_stats(self):
        """Load saved statistics from file."""
        try:
            if Config.STATS_FILE.exists():
                with open(Config.STATS_FILE, 'r') as f:
                    loaded_stats = json.load(f)
                    self.stats.update({
                        'total_scenes_played': loaded_stats.get('total_scenes_played', 0),
                        'scene_play_counts': loaded_stats.get('scene_play_counts', {}),
                        'total_uptime': loaded_stats.get('total_uptime', 0),
                        'last_start_time': time.monotonic(),
                        'connected_devices': {}
                    })
                    self.log.info(f"Loaded stats from: {Config.STATS_FILE}")
            else:
                self.log.info(f"Stats file does not exist, using defaults: {Config.STATS_FILE}")
        except Exception as e:
            self.log.error(f"Error loading stats: {e}")

    def save_stats(self):
        """Save current statistics to file."""
        try:
            Config.STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.update_stats()
            with open(Config.STATS_FILE, 'w') as f:
                save_stats = {k: v for k, v in self.stats.items() if k != 'connected_devices'}  # Exclude transient data
                json.dump(save_stats, f, indent=2)
            self.log.debug(f"Stats saved to: {Config.STATS_FILE}")
        except Exception as e:
            self.log.error(f"Error saving stats: {e}")

    def update_stats(self):
        """Update runtime statistics including uptime and connected devices."""
        self.stats['total_uptime'] += time.monotonic() - self.stats['last_start_time']
        self.stats['last_start_time'] = time.monotonic()
        
        # Fix: Access device registry through the MQTT client structure
        if (hasattr(self.controller, 'mqtt_client') and 
            self.controller.mqtt_client and 
            hasattr(self.controller, 'mqtt_device_registry') and
            self.controller.mqtt_device_registry):
            self.stats['connected_devices'] = self.controller.mqtt_device_registry.get_connected_devices()
        else:
            self.stats['connected_devices'] = {}

    def update_scene_stats(self, scene_name: str):
        """Increment scene play count and save stats."""
        self.stats['total_scenes_played'] += 1
        self.stats['scene_play_counts'][scene_name] = self.stats['scene_play_counts'].get(scene_name, 0) + 1
        self.save_stats()

    def add_log_entry(self, log_entry: Dict):
        """Add a log entry to the buffer and notify connected clients."""
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > Config.MAX_LOG_ENTRIES:
            self.log_buffer = self.log_buffer[-Config.MAX_LOG_ENTRIES:]  # Trim to max size
        self.socketio.emit('new_log', log_entry)

    def filter_logs(self, level_filter: str, limit: int) -> List[Dict]:
        """Filter logs by level and limit the number returned."""
        filtered_logs = self.log_buffer
        if level_filter in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
        return filtered_logs[-limit:] if len(filtered_logs) > limit else filtered_logs