#!/usr/bin/env python3
"""API routes for Scene Management and Execution."""

import json
import threading
from pathlib import Path
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from ..auth import requires_auth
from ..utils.helpers import get_scenes_path, get_scene_path, get_commands_path

from .status import _get_current_status_data 

scenes_bp = Blueprint('scenes', __name__)

def setup_scenes_routes(dashboard):
    controller = dashboard.controller

    @scenes_bp.route('/scenes')
    @requires_auth
    def list_scenes():
        """List all available scene files with their metadata."""
        try:
            scenes_path = get_scenes_path(controller)
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
            return jsonify({'error': f"Error listing scenes: {e}"}), 500

    @scenes_bp.route('/scene/<scene_name>')
    @requires_auth
    def get_scene(scene_name):
        """Retrieve the contents of a specific scene file."""
        try:
            scene_path = get_scene_path(controller, scene_name)
            if not scene_path.exists():
                return jsonify({'error': 'Scene not found'}), 404
            with open(scene_path, 'r') as f:
                return jsonify(json.load(f))
        except Exception as e:
            return jsonify({'error': f"Error loading scene {scene_name}: {e}"}), 500

    @scenes_bp.route('/scene/<scene_name>', methods=['POST'])
    @requires_auth
    def save_scene(scene_name):
        """Save a new or updated scene file with validation."""
        try:
            scene_data = request.json
            
            if not scene_data:
                return jsonify({'error': 'No scene data provided'}), 400
                
            scenes_path = get_scenes_path(controller)
            scenes_path.mkdir(parents=True, exist_ok=True)
            
            if not scene_name.endswith('.json'):
                scene_name = scene_name + '.json'
                
            scene_path = scenes_path / secure_filename(scene_name)
            
            with open(scene_path, 'w') as f:
                json.dump(scene_data, f, indent=2)
                
            dashboard.log.info(f"Scene '{scene_name}' saved successfully to {scene_path}")
            return jsonify({'success': True, 'message': f'Scene {scene_name} saved successfully', 'path': str(scene_path)})
            
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON data: {str(e)}'}), 400
        except Exception as e:
            dashboard.log.error(f"Error saving scene {scene_name}: {e}")
            return jsonify({'error': f'Error saving scene {scene_name}: {str(e)}'}), 500

    @scenes_bp.route('/run_scene/<scene_name>', methods=['POST'])
    @requires_auth
    def run_scene(scene_name):
        """Start a scene in a separate thread if none is currently running."""
        try:
            with controller.scene_lock:
                if controller.scene_running:
                    return jsonify({'error': 'Scene already running'}), 400
                
                scene_path = get_scene_path(controller, scene_name)
                if not scene_path.exists():
                    return jsonify({'error': 'Scene not found'}), 404
                
                controller.scene_running = True
                dashboard.log.info(f"Web dashboard starting scene: {scene_name}")

            dashboard.socketio.emit('status_update', _get_current_status_data(controller))

            def run_scene_thread():
                """Thread function to execute a scene."""
                
                def scene_progress_emitter(progress_data):
                    progress_data['scene_running'] = getattr(controller, 'scene_running', False) 
                    dashboard.socketio.emit('scene_progress_update', progress_data)
                    
                try:
                    if hasattr(controller, 'scene_parser') and controller.scene_parser:
                        
                        if hasattr(controller.scene_parser, 'set_progress_emitter'):
                            controller.scene_parser.set_progress_emitter(scene_progress_emitter)

                        if controller.scene_parser.load_scene(str(scene_path)):
                            controller.current_scene_name = scene_path.name

                            controller.scene_parser.start_scene()
                            if hasattr(controller, 'run_scene'):
                                controller.run_scene()

                            dashboard.socketio.emit('stats_update', dashboard.stats)
                        else:
                            dashboard.log.error("Scene parser failed to load scene")
                    else:
                        dashboard.log.error("Scene parser not available on controller")
                except Exception as e:
                    dashboard.log.error(f"Error running scene {scene_name}: {e}")
                finally:
                    controller.scene_running = False
                    dashboard.socketio.emit('status_update', _get_current_status_data(controller))
                    
                    if hasattr(controller.scene_parser, 'set_progress_emitter'):
                        controller.scene_parser.set_progress_emitter(None)

            thread = threading.Thread(target=run_scene_thread, daemon=True)
            thread.start()
            return jsonify({'success': True, 'message': f'Scene {scene_name} started'})
        except Exception as e:
            controller.scene_running = False
            dashboard.socketio.emit('status_update', _get_current_status_data(controller))
            return jsonify({'error': f"Error starting scene {scene_name}: {e}"}), 500

    @scenes_bp.route('/stop_scene', methods=['POST'])
    @requires_auth
    def stop_scene():
        """Zastaví prebiehajúcu scénu a vyčistí stav systému."""
        try:
            # FIX: Odstránená prísna kontrola, aby STOP fungoval vždy ako "panic button"
            dashboard.log.info("Web dashboard requested GLOBAL STOP")

            # Voláme centrálnu stop metódu v MuseumController (v main.py)
            controller.stop_scene()

        except Exception as e:
            dashboard.log.error(f"Critical error during stop_scene route: {e}")
            return jsonify({'error': str(e)}), 500
            
        finally:
            # Vyčistenie emittera
            if hasattr(controller, 'scene_parser') and hasattr(controller.scene_parser, 'set_progress_emitter'):
                controller.scene_parser.set_progress_emitter(None)
            
            # Odoslanie statusu klientom
            dashboard.socketio.emit('status_update', _get_current_status_data(controller))
            dashboard.log.info("Scene stop sequence finished.")
            
            return jsonify({'success': True, 'message': 'Stop signal broadcasted to all devices'})

    @scenes_bp.route('/config/main_scene')
    @requires_auth
    def get_main_scene():
        """Get the configured main scene filename."""
        return jsonify({'json_file_name': controller.json_file_name})

    return scenes_bp