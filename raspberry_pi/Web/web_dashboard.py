#!/usr/bin/env python3
import os
import sys
import json
import threading
import time
from datetime import datetime
import logging
import subprocess
from werkzeug.utils import secure_filename
import tempfile
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_socketio import SocketIO, emit

class WebDashboard:
    def __init__(self, controller_instance):
        self.controller = controller_instance
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'museum_controller_secret'
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
            ping_timeout=60,
            ping_interval=25
        )
        
        self.setup_routes()
        self.log_buffer = []
        self.max_log_entries = 1000
        self.setup_log_handler()
        
    def setup_log_handler(self):
        """Setup custom log handler to capture logs from museum system"""
        class WebLogHandler(logging.Handler):
            def __init__(self, dashboard):
                super().__init__()
                self.dashboard = dashboard
                
            def emit(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'level': record.levelname,
                    'module': record.name.split('.')[-1] if '.' in record.name else record.name,
                    'message': record.getMessage(),
                    'level_color': self.get_level_color(record.levelname)
                }
                
                if record.exc_info:
                    log_entry['exception'] = self.format(record).split('\n')[1:]
                
                self.dashboard.add_log_entry(log_entry)
            
            def get_level_color(self, level):
                colors = {
                    'DEBUG': 'text-secondary',
                    'INFO': 'text-success', 
                    'WARNING': 'text-warning',
                    'ERROR': 'text-danger',
                    'CRITICAL': 'text-danger fw-bold'
                }
                return colors.get(level, 'text-dark')
        
        web_handler = WebLogHandler(self)
        web_handler.setLevel(logging.DEBUG)
        web_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        
        museum_logger = logging.getLogger('museum')
        museum_logger.addHandler(web_handler)
        root_logger = logging.getLogger()
        root_logger.addHandler(web_handler)
    
    def add_log_entry(self, log_entry):
        """Add log entry and broadcast to connected clients"""
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > self.max_log_entries:
            self.log_buffer = self.log_buffer[-self.max_log_entries:]
        self.socketio.emit('new_log', log_entry)
    
    def load_existing_logs(self):
        """Load recent logs from log files if they exist"""
        try:
            from pathlib import Path
            log_dir = Path.home() / "Documents" / "GitHub" / "museum-system" / "logs"
            
            if not log_dir.exists():
                return
            
            main_log = log_dir / 'museum.log'
            if main_log.exists():
                with open(main_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    recent_lines = lines[-100:] if len(lines) > 100 else lines
                    
                    for line in recent_lines:
                        try:
                            if line.strip() and line.startswith('['):
                                parts = line.strip().split('] ', 1)
                                if len(parts) >= 2:
                                    timestamp = parts[0][1:]
                                    rest = parts[1]
                                    rest_parts = rest.split(' ', 2)
                                    if len(rest_parts) >= 3:
                                        level = rest_parts[0].strip()
                                        module = rest_parts[1].strip()
                                        message = rest_parts[2]
                                        log_entry = {
                                            'timestamp': timestamp,
                                            'level': level,
                                            'module': module,
                                            'message': message,
                                            'level_color': self.get_level_color(level),
                                            'from_file': True
                                        }
                                        self.log_buffer.append(log_entry)
                        except Exception:
                            continue
        except Exception as e:
            logging.getLogger('museum').error(f"Error loading existing logs: {e}")
    
    def get_level_color(self, level):
        """Get Bootstrap color class for log level"""
        colors = {
            'DEBUG': 'text-secondary',
            'INFO': 'text-success', 
            'WARNING': 'text-warning',
            'ERROR': 'text-danger',
            'CRITICAL': 'text-danger fw-bold'
        }
        return colors.get(level, 'text-dark')
    
    def setup_routes(self):
        @self.app.route('/')
        def dashboard():
            return send_from_directory('.', 'dashboard.html')
        
        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                'room_id': getattr(self.controller, 'room_id', 'Unknown'),
                'scene_running': getattr(self.controller, 'scene_running', False),
                'mqtt_connected': getattr(self.controller, 'connected_to_broker', False),
                'uptime': time.time() - getattr(self.controller, 'start_time', time.time()),
                'log_count': len(self.log_buffer)
            })
        
        @self.app.route('/api/logs')
        def get_logs():
            level_filter = request.args.get('level', '').upper()
            limit = int(request.args.get('limit', 500))
            filtered_logs = self.log_buffer
            if level_filter and level_filter in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
            filtered_logs = filtered_logs[-limit:] if len(filtered_logs) > limit else filtered_logs
            return jsonify(filtered_logs)
        
        @self.app.route('/api/logs/clear', methods=['POST'])
        def clear_logs():
            self.log_buffer.clear()
            self.socketio.emit('logs_cleared')
            return jsonify({'success': True, 'message': 'Logs cleared'})
        
        @self.app.route('/api/logs/export')
        def export_logs():
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(self.log_buffer, f, indent=2)
                    temp_file = f.name
                return send_file(
                    temp_file,
                    as_attachment=True,
                    download_name=f'museum_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                    mimetype='application/json'
                )
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/scenes')
        def list_scenes():
            scenes_dir = getattr(self.controller, 'scenes_dir', './scenes')
            room_id = getattr(self.controller, 'room_id', 'default')
            scenes_path = os.path.join(scenes_dir, room_id)
            scenes = []
            if os.path.exists(scenes_path):
                for file in os.listdir(scenes_path):
                    if file.endswith('.json'):
                        scenes.append({
                            'name': file,
                            'path': os.path.join(scenes_path, file),
                            'modified': os.path.getmtime(os.path.join(scenes_path, file))
                        })
            return jsonify(scenes)
        
        @self.app.route('/api/scene/<scene_name>')
        def get_scene(scene_name):
            scenes_dir = getattr(self.controller, 'scenes_dir', './scenes')
            room_id = getattr(self.controller, 'room_id', 'default')
            scene_path = os.path.join(scenes_dir, room_id, secure_filename(scene_name))
            if not os.path.exists(scene_path):
                return jsonify({'error': 'Scene not found'}), 404
            try:
                with open(scene_path, 'r') as f:
                    scene_data = json.load(f)
                return jsonify(scene_data)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/scene/<scene_name>', methods=['POST'])
        def save_scene(scene_name):
            try:
                scene_data = request.json
                scenes_dir = getattr(self.controller, 'scenes_dir', './scenes')
                room_id = getattr(self.controller, 'room_id', 'default')
                scene_path = os.path.join(scenes_dir, room_id, secure_filename(scene_name))
                os.makedirs(os.path.dirname(scene_path), exist_ok=True)
                if not isinstance(scene_data, list):
                    return jsonify({'error': 'Scene must be a list of actions'}), 400
                for action in scene_data:
                    if not all(key in action for key in ['timestamp', 'topic', 'message']):
                        return jsonify({'error': 'Invalid action format'}), 400
                with open(scene_path, 'w') as f:
                    json.dump(scene_data, f, indent=2)
                return jsonify({'success': True, 'message': f'Scene {scene_name} saved successfully'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/run_scene/<scene_name>', methods=['POST'])
        def run_scene(scene_name):
            if getattr(self.controller, 'scene_running', False):
                return jsonify({'error': 'Scene already running'}), 400
            scenes_dir = getattr(self.controller, 'scenes_dir', './scenes')
            room_id = getattr(self.controller, 'room_id', 'default')
            scene_path = os.path.join(scenes_dir, room_id, secure_filename(scene_name))
            if not os.path.exists(scene_path):
                return jsonify({'error': 'Scene not found'}), 404
            try:
                def run_scene_thread():
                    if hasattr(self.controller, 'scene_parser') and self.controller.scene_parser:
                        if self.controller.scene_parser.load_scene(scene_path):
                            self.controller.scene_running = True
                            self.controller.scene_parser.start_scene()
                            if hasattr(self.controller, 'run_scene'):
                                self.controller.run_scene()
                thread = threading.Thread(target=run_scene_thread)
                thread.daemon = True
                thread.start()
                return jsonify({'success': True, 'message': f'Scene {scene_name} started'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stop_scene', methods=['POST'])
        def stop_scene():
            if hasattr(self.controller, 'scene_running'):
                self.controller.scene_running = False
            return jsonify({'success': True, 'message': 'Scene stopped'})
        
        @self.app.route('/api/system/restart', methods=['POST'])
        def restart_system():
            try:
                logging.getLogger('museum').info("Initiating system restart")
                # Run the reboot command
                result = subprocess.run(['sudo', 'reboot'], check=True, capture_output=True, text=True)
                return jsonify({'success': True, 'message': 'System restart initiated'})
            except subprocess.CalledProcessError as e:
                logging.getLogger('museum').error(f"Failed to restart system: {e.stderr}")
                return jsonify({'error': f"Failed to restart system: {e.stderr}"}), 500
            except Exception as e:
                logging.getLogger('museum').error(f"Unexpected error during system restart: {str(e)}")
                return jsonify({'error': f"Unexpected error: {str(e)}"}), 500
        
        @self.app.route('/api/system/shutdown', methods=['POST'])
        def shutdown_system():
            if hasattr(self.controller, 'shutdown_requested'):
                self.controller.shutdown_requested = True
            return jsonify({'success': True, 'message': 'System shutdown initiated'})
        
        @self.socketio.on('connect')
        def handle_connect():
            emit('log_history', self.log_buffer[-100:])
            emit('status_update', {
                'room_id': getattr(self.controller, 'room_id', 'Unknown'),
                'scene_running': getattr(self.controller, 'scene_running', False),
                'mqtt_connected': getattr(self.controller, 'connected_to_broker', False),
                'uptime': time.time() - getattr(self.controller, 'start_time', time.time())
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            pass
        
        @self.socketio.on('request_logs')
        def handle_log_request(data):
            level_filter = data.get('level', '').upper()
            limit = int(data.get('limit', 100))
            filtered_logs = self.log_buffer
            if level_filter and level_filter in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
            filtered_logs = filtered_logs[-limit:] if len(filtered_logs) > limit else filtered_logs
            emit('log_history', filtered_logs)
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the web dashboard"""
        self.load_existing_logs()
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.WARNING)
        flask_logger = logging.getLogger('flask')
        flask_logger.setLevel(logging.WARNING)
        self.socketio.run(
            self.app, 
            host=host, 
            port=port, 
            debug=debug,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )

def start_web_dashboard(controller, port=5000):
    """Start web dashboard in a separate thread"""
    dashboard = WebDashboard(controller)
    def run_dashboard():
        dashboard.run(host='0.0.0.0', port=port, debug=False)
    dashboard_thread = threading.Thread(target=run_dashboard)
    dashboard_thread.daemon = True
    dashboard_thread.start()
    return dashboard