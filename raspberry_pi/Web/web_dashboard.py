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
        self.app.config['ENV'] = 'production'
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
        self.stats = {
            'total_scenes_played': 0,
            'scene_play_counts': {},
            'connection_events': 0,
            'total_uptime': 0,
            'last_start_time': time.time()
        }
        self.setup_log_handler()
        self.load_stats()
        
    def setup_log_handler(self):
        class WebLogHandler(logging.Handler):
            def __init__(self, dashboard):
                super().__init__()
                self.dashboard = dashboard
                
            def emit(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'level': record.levelname,
                    'module': record.name.split('.')[-1] if '.' in record.name else record.name,
                    'message': record.getMessage()
                }
                
                if record.exc_info:
                    log_entry['exception'] = self.format(record).split('\n')[1:]
                
                self.dashboard.add_log_entry(log_entry)
        
        web_handler = WebLogHandler(self)
        web_handler.setLevel(logging.DEBUG)
        web_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        
        museum_logger = logging.getLogger('museum')
        museum_logger.addHandler(web_handler)
        root_logger = logging.getLogger()
        root_logger.addHandler(web_handler)
    
    def add_log_entry(self, log_entry):
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > self.max_log_entries:
            self.log_buffer = self.log_buffer[-self.max_log_entries:]
        self.socketio.emit('new_log', log_entry)
    
    def load_existing_logs(self):
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
                                            'from_file': True
                                        }
                                        self.log_buffer.append(log_entry)
                        except Exception:
                            continue
        except Exception as e:
            logging.getLogger('museum').error(f"Error loading existing logs: {e}")
    
    def load_stats(self):
        try:
            from pathlib import Path
            stats_file = Path.home() / "Documents" / "GitHub" / "museum-system" / "raspberry_pi" / "Web" / "stats.json"
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    loaded_stats = json.load(f)
                    self.stats.update(loaded_stats)
                    self.stats['last_start_time'] = time.time()
        except Exception as e:
            logging.getLogger('museum').error(f"Error loading stats: {e}")

    def save_stats(self):
        try:
            from pathlib import Path
            stats_file = Path.home() / "Documents" / "GitHub" / "museum-system" / "raspberry_pi" / "Web" / "stats.json"
            stats_file.parent.mkdir(parents=True, exist_ok=True)
            self.stats['total_uptime'] += time.time() - self.stats['last_start_time']
            self.stats['last_start_time'] = time.time()
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logging.getLogger('museum').error(f"Error saving stats: {e}")
    
    def setup_routes(self):
        @self.app.route('/')
        def dashboard():
            return send_from_directory('.', 'dashboard.html')
        
        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            return send_from_directory('static', filename)
        
        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                'room_id': getattr(self.controller, 'room_id', 'Unknown'),
                'scene_running': getattr(self.controller, 'scene_running', False),
                'mqtt_connected': getattr(self.controller, 'connected_to_broker', False),
                'uptime': time.time() - getattr(self.controller, 'start_time', time.time()),
                'log_count': len(self.log_buffer)
            })
        
        @self.app.route('/api/stats')
        def get_stats():
            self.stats['total_uptime'] += time.time() - self.stats['last_start_time']
            self.stats['last_start_time'] = time.time()
            return jsonify(self.stats)
        
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
            try:
                scenes_dir = getattr(self.controller, 'scenes_dir', './scenes')
                room_id = getattr(self.controller, 'room_id', 'default')
                scenes_path = os.path.join(scenes_dir, room_id)
                scenes = []
                
                if os.path.exists(scenes_path):
                    for file in os.listdir(scenes_path):
                        if file.endswith('.json'):
                            file_path = os.path.join(scenes_path, file)
                            scenes.append({
                                'name': file,
                                'path': file_path,
                                'modified': os.path.getmtime(file_path)
                            })
                
                scenes.sort(key=lambda x: x['modified'], reverse=True)
                return jsonify(scenes)
            except Exception as e:
                logging.getLogger('museum').error(f"Error listing scenes: {e}")
                return jsonify([])
        
        @self.app.route('/api/scene/<scene_name>')
        def get_scene(scene_name):
            try:
                scenes_dir = getattr(self.controller, 'scenes_dir', './scenes')
                room_id = getattr(self.controller, 'room_id', 'default')
                scene_path = os.path.join(scenes_dir, room_id, secure_filename(scene_name))
                
                if not os.path.exists(scene_path):
                    return jsonify({'error': 'Scene not found'}), 404
                
                with open(scene_path, 'r') as f:
                    scene_data = json.load(f)
                return jsonify(scene_data)
            except Exception as e:
                logging.getLogger('museum').error(f"Error loading scene {scene_name}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/scene/<scene_name>', methods=['POST'])
        def save_scene(scene_name):
            try:
                scene_data = request.json
                scenes_dir = getattr(self.controller, 'scenes_dir', './scenes')
                room_id = getattr(self.controller, 'room_id', 'default')
                scenes_path = os.path.join(scenes_dir, room_id)
                scene_path = os.path.join(scenes_path, secure_filename(scene_name))
                
                os.makedirs(scenes_path, exist_ok=True)
                
                if not isinstance(scene_data, list):
                    return jsonify({'error': 'Scene must be a list of actions'}), 400
                
                for action in scene_data:
                    if not all(key in action for key in ['timestamp', 'topic', 'message']):
                        return jsonify({'error': 'Invalid action format. Each action must have timestamp, topic, and message'}), 400
                
                with open(scene_path, 'w') as f:
                    json.dump(scene_data, f, indent=2)
                
                logging.getLogger('museum').info(f"Scene '{scene_name}' saved successfully")
                return jsonify({'success': True, 'message': f'Scene {scene_name} saved successfully'})
            except Exception as e:
                logging.getLogger('museum').error(f"Error saving scene {scene_name}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/run_scene/<scene_name>', methods=['POST'])
        def run_scene(scene_name):
            try:
                if getattr(self.controller, 'scene_running', False):
                    return jsonify({'error': 'Scene already running'}), 400
                
                scenes_dir = getattr(self.controller, 'scenes_dir', './scenes')
                room_id = getattr(self.controller, 'room_id', 'default')
                scene_path = os.path.join(scenes_dir, room_id, secure_filename(scene_name))
                
                if not os.path.exists(scene_path):
                    return jsonify({'error': 'Scene not found'}), 404
                
                def run_scene_thread():
                    try:
                        logging.getLogger('museum').info(f"Starting scene: {scene_name}")
                        
                        if hasattr(self.controller, 'scene_parser') and self.controller.scene_parser:
                            if self.controller.scene_parser.load_scene(scene_path):
                                self.controller.scene_running = True
                                self.controller.scene_parser.start_scene()
                                
                                if hasattr(self.controller, 'run_scene'):
                                    self.controller.run_scene()
                                
                                # Update stats after scene completion
                                self.stats['total_scenes_played'] += 1
                                self.stats['scene_play_counts'][scene_name] = self.stats['scene_play_counts'].get(scene_name, 0) + 1
                                self.save_stats()
                                self.socketio.emit('stats_update', self.stats)
                            else:
                                logging.getLogger('museum').error("Scene parser not available")
                    except Exception as e:
                        logging.getLogger('museum').error(f"Error running scene {scene_name}: {e}")
                    finally:
                        self.controller.scene_running = False
                
                thread = threading.Thread(target=run_scene_thread)
                thread.daemon = True
                thread.start()
                
                return jsonify({'success': True, 'message': f'Scene {scene_name} started'})
            except Exception as e:
                logging.getLogger('museum').error(f"Error starting scene {scene_name}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stop_scene', methods=['POST'])
        def stop_scene():
            try:
                if hasattr(self.controller, 'scene_running'):
                    self.controller.scene_running = False
                    logging.getLogger('museum').info("Scene stopped by user")
                
                if hasattr(self.controller, 'scene_parser') and self.controller.scene_parser:
                    if hasattr(self.controller.scene_parser, 'stop_scene'):
                        self.controller.scene_parser.stop_scene()
                
                return jsonify({'success': True, 'message': 'Scene stopped'})
            except Exception as e:
                logging.getLogger('museum').error(f"Error stopping scene: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/system/restart', methods=['POST'])
        def restart_system():
            try:
                logging.getLogger('museum').info("System restart requested via web dashboard")
                self.save_stats()
                result = subprocess.run(['sudo', 'reboot'], check=True, capture_output=True, text=True)
                return jsonify({'success': True, 'message': 'System restart initiated'})
            except subprocess.CalledProcessError as e:
                error_msg = f"Failed to restart system: {e.stderr if e.stderr else 'Permission denied'}"
                logging.getLogger('museum').error(error_msg)
                return jsonify({'error': error_msg}), 500
            except FileNotFoundError:
                error_msg = "Reboot command not found. Are you running on a Linux system?"
                logging.getLogger('museum').error(error_msg)
                return jsonify({'error': error_msg}), 500
            except Exception as e:
                error_msg = f"Unexpected error during system restart: {str(e)}"
                logging.getLogger('museum').error(error_msg)
                return jsonify({'error': error_msg}), 500
        
        @self.app.route('/api/system/shutdown', methods=['POST'])
        def shutdown_system():
            try:
                logging.getLogger('museum').info("System shutdown requested via web dashboard")
                self.save_stats()
                if hasattr(self.controller, 'shutdown_requested'):
                    self.controller.shutdown_requested = True
                result = subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True, capture_output=True, text=True)
                return jsonify({'success': True, 'message': 'System shutdown initiated'})
            except Exception as e:
                logging.getLogger('museum').error(f"Error during shutdown: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.socketio.on('connect')
        def handle_connect():
            self.stats['connection_events'] += 1
            self.save_stats()
            logging.getLogger('museum').debug("Client connected to dashboard")
            emit('log_history', self.log_buffer[-100:])
            emit('status_update', {
                'room_id': getattr(self.controller, 'room_id', 'Unknown'),
                'scene_running': getattr(self.controller, 'scene_running', False),
                'mqtt_connected': getattr(self.controller, 'connected_to_broker', False),
                'uptime': time.time() - getattr(self.controller, 'start_time', time.time())
            })
            emit('stats_update', self.stats)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            logging.getLogger('museum').debug("Client disconnected from dashboard")
        
        @self.socketio.on('request_logs')
        def handle_log_request(data):
            try:
                level_filter = data.get('level', '').upper()
                limit = int(data.get('limit', 100))
                filtered_logs = self.log_buffer
                
                if level_filter and level_filter in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                    filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
                
                filtered_logs = filtered_logs[-limit:] if len(filtered_logs) > limit else filtered_logs
                emit('log_history', filtered_logs)
            except Exception as e:
                logging.getLogger('museum').error(f"Error handling log request: {e}")
        
        @self.socketio.on('request_status')
        def handle_status_request():
            try:
                emit('status_update', {
                    'room_id': getattr(self.controller, 'room_id', 'Unknown'),
                    'scene_running': getattr(self.controller, 'scene_running', False),
                    'mqtt_connected': getattr(self.controller, 'connected_to_broker', False),
                    'uptime': time.time() - getattr(self.controller, 'start_time', time.time())
                })
            except Exception as e:
                logging.getLogger('museum').error(f"Error handling status request: {e}")
        
        @self.socketio.on('request_stats')
        def handle_stats_request():
            try:
                self.stats['total_uptime'] += time.time() - self.stats['last_start_time']
                self.stats['last_start_time'] = time.time()
                emit('stats_update', self.stats)
            except Exception as e:
                logging.getLogger('museum').error(f"Error handling stats request: {e}")
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        logging.getLogger('museum').info(f"Starting web dashboard on {host}:{port}")
        self.load_existing_logs()
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.ERROR)
        flask_logger = logging.getLogger('flask')
        flask_logger.setLevel(logging.ERROR)
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

def start_web_dashboard(controller, port=5000):
    dashboard = WebDashboard(controller)
    def run_dashboard():
        try:
            dashboard.run(host='0.0.0.0', port=port, debug=False)
        except Exception as e:
            logging.getLogger('museum').error(f"Dashboard thread error: {e}")
    
    dashboard_thread = threading.Thread(target=run_dashboard)
    dashboard_thread.daemon = True
    dashboard_thread.start()
    
    logging.getLogger('museum').info(f"Web dashboard started on port {port}")
    return dashboard