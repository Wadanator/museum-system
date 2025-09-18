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

from flask import Flask, jsonify, request, send_file, send_from_directory, Response
from flask import request as flask_request  # Alias for clarity in SocketIO
from flask_socketio import SocketIO, emit
from utils.logging_setup import get_logger
from functools import wraps

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

# Authentication helper functions
def check_auth(username, password):
    """Validate provided username and password against configured credentials."""
    return username == Config.USERNAME and password == Config.PASSWORD

def authenticate():
    """Return a 401 response to trigger basic authentication prompt."""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    """Decorator to enforce basic authentication on routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = flask_request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

class WebLogHandler(logging.Handler):
    """Custom logging handler to capture logs for the web dashboard."""
    def __init__(self, dashboard: 'WebDashboard'):
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

class RouteHandler:
    """Manages Flask routes and SocketIO event handlers for the dashboard."""
    def __init__(self, dashboard: 'WebDashboard'):
        self.dashboard = dashboard
        self.app = dashboard.app
        self.socketio = dashboard.socketio
        self.controller = dashboard.controller

    def register_routes(self):
        """Register all Flask routes and SocketIO event handlers with authentication."""
        self.app.route('/')(requires_auth(self.dashboard_route))
        self.app.route('/static/<path:filename>')(requires_auth(self.static_files))
        self.app.route('/api/status')(requires_auth(self.get_status))
        self.app.route('/api/stats')(requires_auth(self.get_stats))
        self.app.route('/api/logs')(requires_auth(self.get_logs))
        self.app.route('/api/logs/clear', methods=['POST'])(requires_auth(self.clear_logs))
        self.app.route('/api/logs/export')(requires_auth(self.export_logs))
        self.app.route('/api/scenes')(requires_auth(self.list_scenes))
        self.app.route('/api/scene/<scene_name>')(requires_auth(self.get_scene))
        self.app.route('/api/scene/<scene_name>', methods=['POST'])(requires_auth(self.save_scene))
        self.app.route('/api/run_scene/<scene_name>', methods=['POST'])(requires_auth(self.run_scene))
        self.app.route('/api/stop_scene', methods=['POST'])(requires_auth(self.stop_scene))
        
        # Command-related routes
        self.app.route('/api/commands')(requires_auth(self.list_commands))
        self.app.route('/api/command/<command_name>')(requires_auth(self.get_command))
        self.app.route('/api/command/<command_name>', methods=['POST'])(requires_auth(self.save_command))
        self.app.route('/api/run_command/<command_name>', methods=['POST'])(requires_auth(self.run_command))
        
        # System control routes
        self.app.route('/api/system/restart', methods=['POST'])(requires_auth(self.restart_system))
        self.app.route('/api/system/shutdown', methods=['POST'])(requires_auth(self.shutdown_system))
        self.app.route('/api/system/service/restart', methods=['POST'])(requires_auth(self.restart_service))

        # SocketIO event handlers
        self.socketio.on('connect')(self.handle_connect)
        self.socketio.on('disconnect')(self.handle_disconnect)
        self.socketio.on('request_logs')(self.handle_log_request)
        self.socketio.on('request_status')(self.handle_status_request)
        self.socketio.on('request_stats')(self.handle_stats_request)

    def dashboard_route(self):
        """Serve the main dashboard HTML page."""
        return send_from_directory('.', 'dashboard.html')

    def static_files(self, filename: str):
        """Serve static files from the static directory."""
        return send_from_directory('static', filename)

    def get_status(self):
        """Return current system status including room ID, scene state, and uptime."""
        return jsonify({
            'room_id': getattr(self.controller, 'room_id', 'Unknown'),
            'scene_running': getattr(self.controller, 'scene_running', False),
            'mqtt_connected': self.controller.mqtt_client.is_connected() if self.controller.mqtt_client else False,
            'uptime': time.monotonic() - getattr(self.controller, 'start_time', time.monotonic()),
            'log_count': len(self.dashboard.log_buffer)
        })

    def get_stats(self):
        """Retrieve and return dashboard statistics."""
        self.dashboard.update_stats()
        return jsonify(self.dashboard.stats)

    def get_logs(self):
        """Fetch logs with optional level filtering and limit."""
        level_filter = request.args.get('level', '').upper()
        limit = int(request.args.get('limit', 500))
        filtered_logs = self.dashboard.filter_logs(level_filter, limit)
        return jsonify(filtered_logs)

    def clear_logs(self):
        """Clear the in-memory log buffer and notify connected clients."""
        self.dashboard.log_buffer.clear()
        self.socketio.emit('logs_cleared')
        return jsonify({'success': True, 'message': 'Logs cleared'})

    def export_logs(self):
        """Export logs as a JSON file for download."""
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
        """List all available scene files with their metadata."""
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
        """Retrieve the contents of a specific scene file."""
        try:
            scene_path = self._get_scene_path(scene_name)
            if not scene_path.exists():
                return jsonify({'error': 'Scene not found'}), 404
            with open(scene_path, 'r') as f:
                return jsonify(json.load(f))
        except Exception as e:
            return self._error_response(f"Error loading scene {scene_name}: {e}")

    def save_scene(self, scene_name: str):
        """Save a new or updated scene file with validation."""
        try:
            scene_data = request.json
            
            if not scene_data:
                return jsonify({'error': 'No scene data provided'}), 400
                
            scenes_path = self._get_scenes_path()
            scenes_path.mkdir(parents=True, exist_ok=True)
            
            # Ensure .json extension
            if not scene_name.endswith('.json'):
                scene_name = scene_name + '.json'
                
            scene_path = scenes_path / secure_filename(scene_name)

            # Validate scene data structure
            if not isinstance(scene_data, list):
                return jsonify({'error': 'Scene must be a list of actions'}), 400
                
            if len(scene_data) == 0:
                return jsonify({'error': 'Scene cannot be empty'}), 400

            # Validate each action
            for i, action in enumerate(scene_data):
                if not isinstance(action, dict):
                    return jsonify({'error': f'Action {i+1} must be an object'}), 400
                    
                required_fields = ['timestamp', 'topic', 'message']
                missing_fields = [field for field in required_fields if field not in action]
                if missing_fields:
                    return jsonify({'error': f'Action {i+1} missing required fields: {", ".join(missing_fields)}'}), 400
                    
                # Validate field types
                if not isinstance(action['timestamp'], (int, float)):
                    return jsonify({'error': f'Action {i+1}: timestamp must be a number'}), 400
                if action['timestamp'] < 0:
                    return jsonify({'error': f'Action {i+1}: timestamp cannot be negative'}), 400
                if not isinstance(action['topic'], str) or not action['topic'].strip():
                    return jsonify({'error': f'Action {i+1}: topic must be a non-empty string'}), 400
                if not isinstance(action['message'], str):
                    return jsonify({'error': f'Action {i+1}: message must be a string'}), 400

            # Save the scene file
            with open(scene_path, 'w') as f:
                json.dump(scene_data, f, indent=2)
                
            logging.getLogger('WEB').info(f"Scene '{scene_name}' saved successfully to {scene_path}")
            return jsonify({
                'success': True, 
                'message': f'Scene {scene_name} saved successfully',
                'path': str(scene_path)
            })
            
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON data: {str(e)}'}), 400
        except Exception as e:
            logging.getLogger('museum').error(f"Error saving scene {scene_name}: {e}")
            return jsonify({'error': f'Error saving scene {scene_name}: {str(e)}'}), 500

    def run_scene(self, scene_name: str):
        """Start a scene in a separate thread if none is currently running."""
        try:
            if getattr(self.controller, 'scene_running', False):
                return jsonify({'error': 'Scene already running'}), 400

            scene_path = self._get_scene_path(scene_name)
            if not scene_path.exists():
                return jsonify({'error': 'Scene not found'}), 404

            def run_scene_thread():
                """Thread function to execute a scene."""
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

    def list_commands(self):
        """List all available command files with their metadata."""
        try:
            commands_path = self._get_commands_path()
            commands = []
            if commands_path.exists():
                commands = [{
                    'name': file.stem,  # Strip .json extension
                    'path': str(file),
                    'modified': file.stat().st_mtime
                } for file in commands_path.glob('*.json')]
                commands.sort(key=lambda x: x['modified'], reverse=True)
            return jsonify(commands)
        except Exception as e:
            return self._error_response(f"Error listing commands: {e}", [])

    def get_command(self, command_name: str):
        """Retrieve the contents of a specific command file."""
        try:
            command_path = self._get_command_path(command_name)
            if not command_path.exists():
                return jsonify({'error': 'Command not found'}), 404
            with open(command_path, 'r') as f:
                return jsonify(json.load(f))
        except Exception as e:
            return self._error_response(f"Error loading command {command_name}: {e}")

    def save_command(self, command_name: str):
        """Save a new or updated command file with validation."""
        try:
            command_data = request.json
            commands_path = self._get_commands_path()
            commands_path.mkdir(parents=True, exist_ok=True)
            command_path = commands_path / secure_filename(command_name + '.json')  # Ensure .json extension

            if not isinstance(command_data, list):
                return jsonify({'error': 'Command must be a list of actions'}), 400
            if not all('timestamp' in a and 'topic' in a and 'message' in a for a in command_data):
                return jsonify({'error': 'Invalid action format'}), 400

            with open(command_path, 'w') as f:
                json.dump(command_data, f, indent=2)
            logging.getLogger('WEB').info(f"Command '{command_name}' saved successfully")
            return jsonify({'success': True, 'message': f'Command {command_name} saved successfully'})
        except Exception as e:
            return self._error_response(f"Error saving command {command_name}: {e}")

    def run_command(self, command_name: str):
        """Execute a command immediately via MQTT."""
        try:
            command_path = self._get_command_path(command_name)
            if not command_path.exists():
                return jsonify({'error': 'Command not found'}), 404

            # Load and execute command actions
            with open(command_path, 'r') as f:
                command_data = json.load(f)

            for action in command_data:
                topic = action['topic']
                message = action['message']
                if hasattr(self.controller, 'mqtt_client') and self.controller.mqtt_client:
                    self.controller.mqtt_client.publish(topic, message)
                logging.getLogger('WEB').info(f"Executed command action: {topic} = {message}")

            return jsonify({'success': True, 'message': f'Command {command_name} executed'})
        except Exception as e:
            return self._error_response(f"Error executing command {command_name}: {e}")

    def stop_scene(self):
        """Stop the currently running scene."""
        try:
            if not getattr(self.controller, 'scene_running', False):
                return jsonify({'error': 'No scene is currently running'}), 400

            if hasattr(self.controller, 'scene_parser'):
                self.controller.scene_parser.stop_scene()
            self.controller.scene_running = False
            logging.getLogger('WEB').info("Scene stopped")
            return jsonify({'success': True, 'message': 'Scene stopped'})
        except Exception as e:
            return self._error_response(f"Error stopping scene: {e}")

    def restart_system(self):
        """Initiate a system reboot."""
        return self._system_command(['sudo', 'reboot'], 'System Restart')

    def shutdown_system(self):
        """Initiate a system shutdown."""
        return self._system_command(['sudo', 'shutdown', '-h', 'now'], 'System Shutdown')

    def restart_service(self):
        """Restart the museum system service."""
        return self._system_command(['sudo', 'systemctl', 'restart', 'museum-system.service'], 'Service Restart')

    def handle_connect(self):
        """Handle new SocketIO client connections with authentication."""
        auth = flask_request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return False  # Reject unauthorized connections
        try:
            emit('log_history', self.dashboard.log_buffer)
            emit('stats_update', self.dashboard.stats)
            logging.getLogger('WEB').info("New SocketIO client connected")
        except Exception as e:
            logging.getLogger('museum').error(f"Error on connect: {e}")

    def handle_disconnect(self):
        """Handle SocketIO client disconnections."""
        logging.getLogger('WEB').info("SocketIO client disconnected")

    def handle_log_request(self):
        """Send log history to requesting SocketIO client."""
        try:
            emit('log_history', self.dashboard.log_buffer)
        except Exception as e:
            logging.getLogger('museum').error(f"Error handling log request: {e}")

    def handle_status_request(self):
        """Send current system status to requesting SocketIO client."""
        try:
            emit('status_update', self.get_status().get_json())
        except Exception as e:
            logging.getLogger('museum').error(f"Error handling status request: {e}")

    def handle_stats_request(self):
        """Send updated statistics to requesting SocketIO client."""
        try:
            self.dashboard.update_stats()
            emit('stats_update', self.dashboard.stats)
        except Exception as e:
            logging.getLogger('museum').error(f"Error handling stats request: {e}")

    def _get_scenes_path(self) -> Path:
        """Get the directory path for scene files, ensuring it exists."""
        room_scenes_path = Path(getattr(self.controller, 'scenes_dir', Config.SCENES_DIR)) / getattr(self.controller, 'room_id', 'default')
        
        # Create the directory if it doesn't exist
        try:
            room_scenes_path.mkdir(parents=True, exist_ok=True)
            logging.getLogger('WEB').debug(f"Scene directory ensured: {room_scenes_path}")
        except Exception as e:
            logging.getLogger('museum').error(f"Failed to create scenes directory {room_scenes_path}: {e}")
            
        return room_scenes_path

    def _get_scene_path(self, scene_name: str) -> Path:
        """Get the file path for a specific scene."""
        return self._get_scenes_path() / secure_filename(scene_name)

    def _get_commands_path(self) -> Path:
        """Get the directory path for command files."""
        return Config.COMMANDS_DIR

    def _get_command_path(self, command_name: str) -> Path:
        """Get the file path for a specific command, ensuring .json extension."""
        if not command_name.endswith('.json'):
            command_name += '.json'
        return self._get_commands_path() / secure_filename(command_name)

    def _system_command(self, command: List[str], operation: str):
        """Execute a system command with error handling."""
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
        """Generate an error response with logging."""
        logging.getLogger('museum').error(message)
        return jsonify({'error': message}), 500 if default_response is None else (default_response, 500)

class WebDashboard:
    """Web interface for controlling and monitoring the museum system."""
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
        RouteHandler(self).register_routes()

    def _setup_logging(self):
        """Configure logging handlers for the dashboard."""
        web_handler = WebLogHandler(self)
        for logger_name in ('museum', ''):
            logger = logging.getLogger(logger_name)
            logger.addHandler(web_handler)
        for logger_name in ('werkzeug', 'flask'):
            logging.getLogger(logger_name).setLevel(logging.ERROR)  # Suppress Flask/Werkzeug logs
        self.load_existing_logs()

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
                    logging.getLogger('WEB').info(f"Loaded stats from: {Config.STATS_FILE}")
            else:
                logging.getLogger('WEB').info(f"Stats file does not exist, using defaults: {Config.STATS_FILE}")
        except Exception as e:
            logging.getLogger('museum').error(f"Error loading stats: {e}")

    def save_stats(self):
        """Save current statistics to file."""
        try:
            Config.STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.update_stats()
            with open(Config.STATS_FILE, 'w') as f:
                save_stats = {k: v for k, v in self.stats.items() if k != 'connected_devices'}  # Exclude transient data
                json.dump(save_stats, f, indent=2)
            logging.getLogger('museum').debug(f"Stats saved to: {Config.STATS_FILE}")
        except Exception as e:
            logging.getLogger('museum').error(f"Error saving stats: {e}")

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

    def run(self, host: str = '0.0.0.0', port: int = Config.DEFAULT_PORT, debug: bool = False):
        logging.getLogger('WEB').info(f"Starting web dashboard on {host}:{port}")
        while True: 
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
                logging.getLogger('WEB').error(f"WEB crashed: {e}. Restarting in 10s...")
                time.sleep(10)

def start_web_dashboard(controller, port: int = Config.DEFAULT_PORT) -> WebDashboard:
    """Start the web dashboard in a separate thread."""
    dashboard = WebDashboard(controller)
    def run_dashboard():
        """Thread function to run the dashboard."""
        try:
            dashboard.run(host='0.0.0.0', port=port, debug=False)
        except Exception as e:
            logging.getLogger('museum').error(f"Dashboard thread error: {e}")
    
    thread = threading.Thread(target=run_dashboard, daemon=True)
    thread.start()
    logging.getLogger('WEB').info(f"Web dashboard started on port {port}")
    return dashboard