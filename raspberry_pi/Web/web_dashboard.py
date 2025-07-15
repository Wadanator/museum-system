#!/usr/bin/env python3
import json
import logging
import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from utils.logging_setup import get_logger

class Config:
    """Centralized configuration for the WebDashboard."""
    SECRET_KEY = 'museum_controller_secret'
    MAX_LOG_ENTRIES = 1000
    DEFAULT_PORT = 5000
    
    # Use paths relative to the script's location
    _BASE_DIR = Path(__file__).resolve().parent.parent
    LOG_DIR = _BASE_DIR / "logs"
    STATS_FILE = _BASE_DIR / "Web" / "stats.json"
    SCENES_DIR = _BASE_DIR / "scenes"


class WebLogHandler(logging.Handler):
    """Custom logging handler for web dashboard."""
    def __init__(self, dashboard: 'WebDashboard'):
        super().__init__()
        self.dashboard = dashboard
        self.setLevel(logging.DEBUG)
        self.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        # Extract the last meaningful part of the logger name
        module = record.name.split('.')[-1] if '.' in record.name else record.name
        if module.startswith('utils.'):
            module = module.split('.')[-1]  # Handle utils.<module> case
        module = module.strip()  # No padding for web display
        
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'level': record.levelname,
            'module': module,
            'message': record.getMessage()
        }
        if record.exc_info:
            log_entry['exception'] = self.format(record).split('\n')[1:]
        self.dashboard.add_log_entry(log_entry)


class RouteHandler:
    """Handles all Flask routes and SocketIO events."""
    def __init__(self, dashboard: 'WebDashboard'):
        self.dashboard = dashboard
        self.app = dashboard.app
        self.socketio = dashboard.socketio
        self.controller = dashboard.controller

    def register_routes(self):
        """Register all Flask routes and SocketIO handlers."""
        self.app.route('/')(self.dashboard_route)
        self.app.route('/static/<path:filename>')(self.static_files)
        self.app.route('/api/status')(self.get_status)
        self.app.route('/api/stats')(self.get_stats)
        self.app.route('/api/logs')(self.get_logs)
        self.app.route('/api/logs/clear', methods=['POST'])(self.clear_logs)
        self.app.route('/api/logs/export')(self.export_logs)
        self.app.route('/api/scenes')(self.list_scenes)
        self.app.route('/api/scene/<scene_name>')(self.get_scene)
        self.app.route('/api/scene/<scene_name>', methods=['POST'])(self.save_scene)
        self.app.route('/api/run_scene/<scene_name>', methods=['POST'])(self.run_scene)
        self.app.route('/api/stop_scene', methods=['POST'])(self.stop_scene)
        self.app.route('/api/system/restart', methods=['POST'])(self.restart_system)
        self.app.route('/api/system/shutdown', methods=['POST'])(self.shutdown_system)
        self.app.route('/api/system/service/restart', methods=['POST'])(self.restart_service)

        self.socketio.on('connect')(self.handle_connect)
        self.socketio.on('disconnect')(self.handle_disconnect)
        self.socketio.on('request_logs')(self.handle_log_request)
        self.socketio.on('request_status')(self.handle_status_request)
        self.socketio.on('request_stats')(self.handle_stats_request)

    def dashboard_route(self):
        return send_from_directory('.', 'dashboard.html')

    def static_files(self, filename: str):
        return send_from_directory('static', filename)

    def get_status(self):
        return jsonify({
            'room_id': getattr(self.controller, 'room_id', 'Unknown'),
            'scene_running': getattr(self.controller, 'scene_running', False),
            'mqtt_connected': getattr(self.controller, 'connected_to_broker', False),
            'uptime': time.time() - getattr(self.controller, 'start_time', time.time()),
            'log_count': len(self.dashboard.log_buffer)
        })

    def get_stats(self):
        self.dashboard.update_stats()
        return jsonify(self.dashboard.stats)

    def get_logs(self):
        level_filter = request.args.get('level', '').upper()
        limit = int(request.args.get('limit', 500))
        filtered_logs = self.dashboard.filter_logs(level_filter, limit)
        return jsonify(filtered_logs)

    def clear_logs(self):
        self.dashboard.log_buffer.clear()
        self.socketio.emit('logs_cleared')
        return jsonify({'success': True, 'message': 'Logs cleared'})

    def export_logs(self):
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(self.dashboard.log_buffer, f, indent=2)
                temp_file = f.name
            return send_file(
                temp_file,
                as_attachment=True,
                download_name=f'museum_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                mimetype='application/json'
            )
        except Exception as e:
            return self._error_response(f"Error exporting logs: {e}")

    def list_scenes(self):
        try:
            scenes_path = self._get_scenes_path()
            scenes = []
            if scenes_path.exists():
                scenes = [{
                    'name': file.name,
                    'path': str(file),
                    'modified': file.stat().st_mtime
                } for file in scenes_path.glob('*.json')]
                scenes.sort(key=lambda x: x['modified'], reverse=True)
            return jsonify(scenes)
        except Exception as e:
            return self._error_response(f"Error listing scenes: {e}", [])

    def get_scene(self, scene_name: str):
        try:
            scene_path = self._get_scene_path(scene_name)
            if not scene_path.exists():
                return jsonify({'error': 'Scene not found'}), 404
            with open(scene_path, 'r') as f:
                return jsonify(json.load(f))
        except Exception as e:
            return self._error_response(f"Error loading scene {scene_name}: {e}")

    def save_scene(self, scene_name: str):
        try:
            scene_data = request.json
            scenes_path = self._get_scenes_path()
            scenes_path.mkdir(parents=True, exist_ok=True)
            scene_path = scenes_path / secure_filename(scene_name)

            if not isinstance(scene_data, list):
                return jsonify({'error': 'Scene must be a list of actions'}), 400
            if not all('timestamp' in a and 'topic' in a and 'message' in a for a in scene_data):
                return jsonify({'error': 'Invalid action format'}), 400

            with open(scene_path, 'w') as f:
                json.dump(scene_data, f, indent=2)
            logging.getLogger('WEB').info(f"Scene '{scene_name}' saved successfully")
            return jsonify({'success': True, 'message': f'Scene {scene_name} saved successfully'})
        except Exception as e:
            return self._error_response(f"Error saving scene {scene_name}: {e}")

    def run_scene(self, scene_name: str):
        try:
            if getattr(self.controller, 'scene_running', False):
                return jsonify({'error': 'Scene already running'}), 400

            scene_path = self._get_scene_path(scene_name)
            if not scene_path.exists():
                return jsonify({'error': 'Scene not found'}), 404

            def run_scene_thread():
                try:
                    logging.getLogger('WEB').info(f"Starting scene: {scene_name}")
                    if hasattr(self.controller, 'scene_parser') and self.controller.scene_parser:
                        if self.controller.scene_parser.load_scene(str(scene_path)):
                            self.controller.scene_running = True
                            self.controller.scene_parser.start_scene()
                            if hasattr(self.controller, 'run_scene'):
                                self.controller.run_scene()
                            self.dashboard.update_scene_stats(scene_name)
                            self.socketio.emit('stats_update', self.dashboard.stats)
                        else:
                            logging.getLogger('museum').error("Scene parser not available")
                except Exception as e:
                    logging.getLogger('museum').error(f"Error running scene {scene_name}: {e}")
                finally:
                    self.controller.scene_running = False

            thread = threading.Thread(target=run_scene_thread, daemon=True)
            thread.start()
            return jsonify({'success': True, 'message': f'Scene {scene_name} started'})
        except Exception as e:
            return self._error_response(f"Error starting scene {scene_name}: {e}")

    def stop_scene(self):
        try:
            if hasattr(self.controller, 'scene_running'):
                self.controller.scene_running = False
                logging.getLogger('WEB').info("Scene stopped by user")
            if hasattr(self.controller, 'scene_parser') and self.controller.scene_parser:
                if hasattr(self.controller.scene_parser, 'stop_scene'):
                    self.controller.scene_parser.stop_scene()
            return jsonify({'success': True, 'message': 'Scene stopped'})
        except Exception as e:
            return self._error_response(f"Error stopping scene: {e}")

    def restart_system(self):
        return self._system_command(['sudo', 'reboot'], "System restart")

    def shutdown_system(self):
        try:
            logging.getLogger('WEB').info("System shutdown requested")
            self.dashboard.save_stats()
            if hasattr(self.controller, 'shutdown_requested'):
                self.controller.shutdown_requested = True
            return self._system_command(['sudo', 'shutdown', '-h', 'now'], "System shutdown")
        except Exception as e:
            return self._error_response(f"Error during shutdown: {e}")

    def restart_service(self):
        return self._system_command(['sudo', 'systemctl', 'restart', 'museum-system'], "Museum system service restart")

    def handle_connect(self):
        logging.getLogger('museum').debug("Client connected to dashboard")
        emit('log_history', self.dashboard.log_buffer[-100:])
        emit('status_update', self.get_status().get_json())
        emit('stats_update', self.dashboard.stats)

    def handle_disconnect(self):
        logging.getLogger('museum').debug("Client disconnected from dashboard")

    def handle_log_request(self, data: Dict):
        try:
            level_filter = data.get('level', '').upper()
            limit = int(data.get('limit', 100))
            filtered_logs = self.dashboard.filter_logs(level_filter, limit)
            emit('log_history', filtered_logs)
        except Exception as e:
            logging.getLogger('museum').error(f"Error handling log request: {e}")

    def handle_status_request(self):
        try:
            emit('status_update', self.get_status().get_json())
        except Exception as e:
            logging.getLogger('museum').error(f"Error handling status request: {e}")

    def handle_stats_request(self):
        try:
            self.dashboard.update_stats()
            emit('stats_update', self.dashboard.stats)
        except Exception as e:
            logging.getLogger('museum').error(f"Error handling stats request: {e}")

    def _get_scenes_path(self) -> Path:
        return Path(getattr(self.controller, 'scenes_dir', Config.SCENES_DIR)) / getattr(self.controller, 'room_id', 'default')

    def _get_scene_path(self, scene_name: str) -> Path:
        return self._get_scenes_path() / secure_filename(scene_name)

    def _system_command(self, command: List[str], operation: str):
        try:
            logging.getLogger('WEB').info(f"{operation} requested via web dashboard")
            self.dashboard.save_stats()
            subprocess.run(command, check=True, capture_output=True, text=True)
            return jsonify({'success': True, 'message': f'{operation} initiated'})
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to {operation.lower()}: {e.stderr if e.stderr else 'Permission denied'}"
            logging.getLogger('museum').error(error_msg)
            return jsonify({'error': error_msg}), 500
        except FileNotFoundError:
            error_msg = f"Command not found. Are you running on a Linux system?"
            logging.getLogger('museum').error(error_msg)
            return jsonify({'error': error_msg}), 500
        except Exception as e:
            error_msg = f"Unexpected error during {operation.lower()}: {str(e)}"
            logging.getLogger('museum').error(error_msg)
            return jsonify({'error': error_msg}), 500

    def _error_response(self, message: str, default_response: Optional[any] = None):
        logging.getLogger('museum').error(message)
        return jsonify({'error': message}), 500 if default_response is None else (default_response, 500)


class WebDashboard:
    """Web dashboard for museum system control."""
    def __init__(self, controller):
        self.controller = controller
        self.log = get_logger('web')
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = Config.SECRET_KEY
        self.app.config['ENV'] = 'production'
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
            ping_timeout=60,
            ping_interval=25
        )
        self.log_buffer: List[Dict] = []
        self.stats = {
            'total_scenes_played': 0,
            'scene_play_counts': {},
            'total_uptime': 0,
            'last_start_time': time.time(),
            'connected_devices': {}
        }
        self._setup_logging()
        self._load_stats()
        RouteHandler(self).register_routes()

    def _setup_logging(self):
        """Configure logging for the dashboard."""
        web_handler = WebLogHandler(self)
        for logger_name in ('museum', ''):
            logger = logging.getLogger(logger_name)
            logger.addHandler(web_handler)
        for logger_name in ('werkzeug', 'flask'):
            logging.getLogger(logger_name).setLevel(logging.ERROR)
        self.load_existing_logs()

    def load_existing_logs(self):
        """Load recent logs from file."""
        try:
            if not Config.LOG_DIR.exists():
                self.log.info(f"Log directory does not exist: {Config.LOG_DIR}")
                return
            main_log = Config.LOG_DIR / 'museum.log'
            if main_log.exists():
                with open(main_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-100:]
                    for line in lines:
                        if line.strip() and line.startswith('['):
                            try:
                                timestamp, rest = line.strip().split('] ', 1)
                                level, module, message = rest.split(' ', 2)
                                self.log_buffer.append({
                                    'timestamp': timestamp[1:],
                                    'level': level.strip(),
                                    'module': module.strip(),  # Remove padding for web display
                                    'message': message,
                                    'from_file': True
                                })
                            except ValueError:
                                # Handle malformed log lines
                                continue
                    self.log.info(f"Loaded {len([log for log in self.log_buffer if log.get('from_file')])} log entries from file")
            else:
                self.log.info(f"Main log file does not exist: {main_log}")
        except Exception as e:
            self.log.error(f"Error loading existing logs: {e}")

    def _load_stats(self):
        """Load stats from file."""
        try:
            if Config.STATS_FILE.exists():
                with open(Config.STATS_FILE, 'r') as f:
                    loaded_stats = json.load(f)
                    self.stats.update({
                        'total_scenes_played': loaded_stats.get('total_scenes_played', 0),
                        'scene_play_counts': loaded_stats.get('scene_play_counts', {}),
                        'total_uptime': loaded_stats.get('total_uptime', 0),
                        'last_start_time': time.time(),
                        'connected_devices': {}
                    })
                    logging.getLogger('WEB').info(f"Loaded stats from: {Config.STATS_FILE}")
            else:
                logging.getLogger('WEB').info(f"Stats file does not exist, using defaults: {Config.STATS_FILE}")
        except Exception as e:
            logging.getLogger('museum').error(f"Error loading stats: {e}")

    def save_stats(self):
        """Save stats to file."""
        try:
            Config.STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.update_stats()
            with open(Config.STATS_FILE, 'w') as f:
                # Exclude connected_devices from saved stats as it's transient
                save_stats = {k: v for k, v in self.stats.items() if k != 'connected_devices'}
                json.dump(save_stats, f, indent=2)
            logging.getLogger('museum').debug(f"Stats saved to: {Config.STATS_FILE}")
        except Exception as e:
            logging.getLogger('museum').error(f"Error saving stats: {e}")

    def update_stats(self):
        """Update running stats."""
        self.stats['total_uptime'] += time.time() - self.stats['last_start_time']
        self.stats['last_start_time'] = time.time()
        if hasattr(self.controller, 'mqtt_client') and self.controller.mqtt_client:
            self.stats['connected_devices'] = self.controller.mqtt_client.get_connected_devices()

    def update_scene_stats(self, scene_name: str):
        """Update scene-specific stats."""
        self.stats['total_scenes_played'] += 1
        self.stats['scene_play_counts'][scene_name] = self.stats['scene_play_counts'].get(scene_name, 0) + 1
        self.save_stats()

    def add_log_entry(self, log_entry: Dict):
        """Add a new log entry to the buffer."""
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > Config.MAX_LOG_ENTRIES:
            self.log_buffer = self.log_buffer[-Config.MAX_LOG_ENTRIES:]
        self.socketio.emit('new_log', log_entry)

    def filter_logs(self, level_filter: str, limit: int) -> List[Dict]:
        """Filter logs based on level and limit."""
        filtered_logs = self.log_buffer
        if level_filter in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
        return filtered_logs[-limit:] if len(filtered_logs) > limit else filtered_logs

    def run(self, host: str = '0.0.0.0', port: int = Config.DEFAULT_PORT, debug: bool = False):
        """Start the web dashboard."""
        logging.getLogger('WEB').info(f"Starting web dashboard on {host}:{port}")
        logging.getLogger('WEB').info(f"Project root: {Config._BASE_DIR}")
        
        import warnings
        warnings.filterwarnings('ignore', message='.*Werkzeug.*production.*')
        os.environ['FLASK_ENV'] = 'production'
        try:
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=debug,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            logging.getLogger('museum').error(f"Error starting web dashboard: {e}")
            raise


def start_web_dashboard(controller, port: int = Config.DEFAULT_PORT) -> WebDashboard:
    """Start the web dashboard in a separate thread."""
    dashboard = WebDashboard(controller)
    def run_dashboard():
        try:
            dashboard.run(host='0.0.0.0', port=port, debug=False)
        except Exception as e:
            logging.getLogger('museum').error(f"Dashboard thread error: {e}")
    
    thread = threading.Thread(target=run_dashboard, daemon=True)
    thread.start()
    logging.getLogger('WEB').info(f"Web dashboard started on port {port}")
    return dashboard