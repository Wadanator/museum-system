#!/usr/bin/env python3
"""API routes for the Web Dashboard - Updated with scene progress tracking."""

import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from ..auth import requires_auth
from ..utils.helpers import (
    get_scenes_path, get_scene_path, get_commands_path, get_command_path
)

api_bp = Blueprint('api', __name__, url_prefix='/api')

def setup_api_routes(dashboard):
    """Setup API routes with dashboard context."""
    controller = dashboard.controller
    
    @api_bp.route('/status')
    @requires_auth
    def get_status():
        """Return current system status including room ID, scene state, and uptime."""
        return jsonify({
            'room_id': getattr(controller, 'room_id', 'Unknown'),
            'scene_running': getattr(controller, 'scene_running', False),
            'mqtt_connected': controller.mqtt_client.is_connected() if controller.mqtt_client else False,
            'uptime': dashboard.get_uptime(),
            'log_count': len(dashboard.log_buffer)
        })

    @api_bp.route('/scene/progress')
    @requires_auth
    def get_scene_progress():
        """Get current scene progress - supports state machine format."""
        try:
            scene_running = getattr(controller, 'scene_running', False)
            
            if not scene_running or not hasattr(controller, 'scene_parser') or not controller.scene_parser:
                return jsonify({
                    'scene_running': False,
                    'mode': 'none',
                    'progress': 0.0,
                    'remaining_time': 0,
                    'total_duration': 0
                })
            
            scene_parser = controller.scene_parser
            if not scene_parser.scene_data:
                return jsonify({
                    'scene_running': scene_running,
                    'mode': 'none',
                    'progress': 0.0,
                    'remaining_time': 0,
                    'total_duration': 0
                })
            
            # Get progress info from state machine
            progress_info = scene_parser.get_progress_info()
            
            # State machine response
            return jsonify({
                'scene_running': scene_running,
                'mode': progress_info.get('mode', 'state_machine'),
                'scene_id': progress_info.get('scene_id', 'unknown'),
                'current_state': progress_info.get('current_state', 'unknown'),
                'state_description': progress_info.get('state_description', ''),
                'states_completed': progress_info.get('states_completed', 0),
                'total_states': progress_info.get('total_states', 0),
                'state_elapsed': progress_info.get('state_elapsed', 0),
                'scene_elapsed': progress_info.get('scene_elapsed', 0),
                # For compatibility with frontend progress bar
                'progress': min(1.0, progress_info.get('states_completed', 0) / max(progress_info.get('total_states', 1), 1)),
                'remaining_time': 0  # State machine nemá fixed duration
            })
            
        except Exception as e:
            dashboard.log.error(f"Error getting scene progress: {e}")
            return jsonify({
                'scene_running': False,
                'mode': 'error',
                'progress': 0.0,
                'remaining_time': 0,
                'total_duration': 0,
                'error': str(e)
            }), 500

    @api_bp.route('/stats')
    @requires_auth
    def get_stats():
        """Retrieve and return dashboard statistics."""
        dashboard.update_stats()
        return jsonify(dashboard.stats)

    @api_bp.route('/logs')
    @requires_auth
    def get_logs():
        """Fetch logs with optional level filtering and limit."""
        level_filter = request.args.get('level', '').upper()
        limit = int(request.args.get('limit', 500))
        filtered_logs = dashboard.filter_logs(level_filter, limit)
        return jsonify(filtered_logs)

    @api_bp.route('/logs/clear', methods=['POST'])
    @requires_auth
    def clear_logs():
        """Clear the in-memory log buffer and notify connected clients."""
        dashboard.log_buffer.clear()
        dashboard.socketio.emit('logs_cleared')
        return jsonify({'success': True, 'message': 'Logs cleared'})

    @api_bp.route('/logs/export')
    @requires_auth
    def export_logs():
        """Export logs as a JSON file for download."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(dashboard.log_buffer, f, indent=2)
                temp_file = f.name
            return send_file(
                temp_file,
                as_attachment=True,
                download_name=f'museum_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                mimetype='application/json'
            )
        except Exception as e:
            return jsonify({'error': f"Error exporting logs: {e}"}), 500

    @api_bp.route('/scenes')
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

    @api_bp.route('/scene/<scene_name>')
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

    @api_bp.route('/scene/<scene_name>', methods=['POST'])
    @requires_auth
    def save_scene(scene_name):
        """Save a new or updated scene file with validation (now supports State Machine format)."""
        try:
            scene_data = request.json
            
            if not scene_data:
                return jsonify({'error': 'No scene data provided'}), 400
                
            scenes_path = get_scenes_path(controller)
            scenes_path.mkdir(parents=True, exist_ok=True)
            
            # Ensure .json extension
            if not scene_name.endswith('.json'):
                scene_name = scene_name + '.json'
                
            scene_path = scenes_path / secure_filename(scene_name)

            # --- NEW VALIDATION FOR STATE MACHINE FORMAT ---
            
            # 1. Root structure check
            if not isinstance(scene_data, dict):
                return jsonify({'error': 'Scene must be a JSON object (State Machine format)'}), 400

            required_root_fields = ['sceneId', 'version', 'initialState', 'states']
            missing_root_fields = [field for field in required_root_fields if field not in scene_data]
            if missing_root_fields:
                return jsonify({'error': f'Missing required scene fields: {", ".join(missing_root_fields)}'}), 400

            if not isinstance(scene_data['states'], dict) or not scene_data['states']:
                return jsonify({'error': 'The "states" field must be a non-empty object'}), 400
            
            initial_state = scene_data['initialState']
            states = scene_data['states']
            if initial_state not in states:
                return jsonify({'error': f'initialState "{initial_state}" is not defined in "states"'}), 400
                
            # 2. Validate each state and its transitions
            for state_name, state_data in states.items():
                if state_name == 'END':
                    continue # Special terminal state
                
                if not isinstance(state_data, dict):
                    return jsonify({'error': f'State "{state_name}" must be an object'}), 400

                # Validate onEnter actions
                if 'onEnter' not in state_data or not isinstance(state_data.get('onEnter'), list):
                    return jsonify({'error': f'State "{state_name}" missing or invalid "onEnter" list of actions'}), 400

                for i, action in enumerate(state_data['onEnter']):
                    if not isinstance(action, dict):
                        return jsonify({'error': f'State "{state_name}", action {i+1}: must be an object'}), 400
                        
                    if action.get('action') != 'mqtt': # Only 'mqtt' is supported for now
                        return jsonify({'error': f'State "{state_name}", action {i+1}: "action" must be "mqtt"'}), 400
                    
                    required_action_fields = ['topic', 'message']
                    missing_action_fields = [field for field in required_action_fields if field not in action]
                    if missing_action_fields:
                        return jsonify({'error': f'State "{state_name}", action {i+1}: missing required fields: {", ".join(missing_action_fields)}'}), 400
                    
                    if not isinstance(action.get('topic'), str) or not action['topic'].strip():
                        return jsonify({'error': f'State "{state_name}", action {i+1}: topic must be a non-empty string'}), 400
                    if not isinstance(action.get('message'), str):
                        return jsonify({'error': f'State "{state_name}", action {i+1}: message must be a string'}), 400


                # Validate transitions
                if 'transitions' not in state_data or not isinstance(state_data.get('transitions'), list):
                    return jsonify({'error': f'State "{state_name}" missing or invalid "transitions" list'}), 400
                
                for i, transition in enumerate(state_data['transitions']):
                    if not isinstance(transition, dict):
                        return jsonify({'error': f'State "{state_name}", transition {i+1}: must be an object'}), 400

                    required_transition_fields = ['type', 'goto']
                    missing_transition_fields = [field for field in required_transition_fields if field not in transition]
                    if missing_transition_fields:
                        return jsonify({'error': f'State "{state_name}", transition {i+1}: missing required fields: {", ".join(missing_transition_fields)}'}), 400
                        
                    # Check if goto state exists
                    goto_state = transition['goto']
                    if goto_state != 'END' and goto_state not in states:
                        return jsonify({'error': f'State "{state_name}", transition {i+1}: "goto" state "{goto_state}" not found in "states" or is not "END"'}), 400

                    # Check type-specific fields
                    if transition['type'] == 'timeout':
                        if 'delay' not in transition or not isinstance(transition['delay'], (int, float)) or transition['delay'] <= 0:
                            return jsonify({'error': f'State "{state_name}", transition {i+1}: "timeout" transition requires a positive "delay" number'}), 400
                    elif transition['type'] == 'feedback':
                        required_feedback_fields = ['device_topic', 'expected_message']
                        missing_feedback_fields = [field for field in required_feedback_fields if field not in transition]
                        if missing_feedback_fields:
                            return jsonify({'error': f'State "{state_name}", transition {i+1}: "feedback" transition missing required fields: {", ".join(missing_feedback_fields)}'}), 400
                    else:
                         return jsonify({'error': f'State "{state_name}", transition {i+1}: Unknown transition type "{transition["type"]}"'}), 400

            # --- END NEW VALIDATION ---
            
            # Save the scene file
            with open(scene_path, 'w') as f:
                json.dump(scene_data, f, indent=2)
                
            dashboard.log.info(f"Scene '{scene_name}' saved successfully to {scene_path}")
            return jsonify({
                'success': True, 
                'message': f'Scene {scene_name} saved successfully',
                'path': str(scene_path)
            })
            
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON data: {str(e)}'}), 400
        except Exception as e:
            dashboard.log.error(f"Error saving scene {scene_name}: {e}")
            return jsonify({'error': f'Error saving scene {scene_name}: {str(e)}'}), 500

    @api_bp.route('/run_scene/<scene_name>', methods=['POST'])
    @requires_auth
    def run_scene(scene_name):
        """Start a scene in a separate thread if none is currently running."""
        try:
            # ✅ Thread-safe check and set (same as button handler)
            with controller.scene_lock:
                if controller.scene_running:
                    return jsonify({'error': 'Scene already running'}), 400
                
                scene_path = get_scene_path(controller, scene_name)
                if not scene_path.exists():
                    return jsonify({'error': 'Scene not found'}), 404
                
                # Set scene_running while locked
                controller.scene_running = True
                dashboard.log.info(f"Web dashboard starting scene: {scene_name}")

            def run_scene_thread():
                """Thread function to execute a scene."""
                try:
                    if hasattr(controller, 'scene_parser') and controller.scene_parser:
                        if controller.scene_parser.load_scene(str(scene_path)):
                            controller.scene_parser.start_scene()
                            if hasattr(controller, 'run_scene'):
                                controller.run_scene()
                            dashboard.update_scene_stats(scene_name)
                            dashboard.socketio.emit('stats_update', dashboard.stats)
                        else:
                            dashboard.log.error("Scene parser not available")
                except Exception as e:
                    dashboard.log.error(f"Error running scene {scene_name}: {e}")
                finally:
                    # ✅ Always clear scene_running when done
                    controller.scene_running = False

            thread = threading.Thread(target=run_scene_thread, daemon=True)
            thread.start()
            return jsonify({'success': True, 'message': f'Scene {scene_name} started'})
        except Exception as e:
            # ✅ Clear scene_running on error
            controller.scene_running = False
            return jsonify({'error': f"Error starting scene {scene_name}: {e}"}), 500

    @api_bp.route('/stop_scene', methods=['POST'])
    @requires_auth
    def stop_scene():
        """Stop the currently running scene and execute STOPALL command."""
        try:
            if not getattr(controller, 'scene_running', False):
                return jsonify({'error': 'No scene is currently running'}), 400

            # Stop the scene
            if hasattr(controller, 'scene_parser'):
                controller.scene_parser.stop_scene()
            controller.scene_running = False
            dashboard.log.info("Scene stopped")

            # Stop audio and video directly through handlers
            audio_stopped = False
            video_stopped = False
            
            try:
                if hasattr(controller, 'audio_handler') and controller.audio_handler:
                    controller.audio_handler.stop_audio()
                    audio_stopped = True
                    dashboard.log.info("Audio stopped directly")
            except Exception as e:
                dashboard.log.warning(f"Error stopping audio: {e}")

            try:
                if hasattr(controller, 'video_handler') and controller.video_handler:
                    controller.video_handler.stop_video()
                    video_stopped = True
                    dashboard.log.info("Video stopped directly")
            except Exception as e:
                dashboard.log.warning(f"Error stopping video: {e}")

            # Execute STOPALL command for external devices (ESP32)
            try:
                stopall_command_path = get_commands_path() / 'STOPALL.json'
                
                if stopall_command_path.exists():
                    with open(stopall_command_path, 'r') as f:
                        stopall_data = json.load(f)
                    
                    dashboard.log.info("Executing STOPALL command for external devices")
                    
                    # Execute each action in STOPALL command
                    for action in stopall_data:
                        topic = action['topic']
                        message = action['message']
                        
                        if hasattr(controller, 'mqtt_client') and controller.mqtt_client:
                            success = controller.mqtt_client.publish(topic, message)
                            if success:
                                dashboard.log.info(f"STOPALL action executed: {topic} = {message}")
                            else:
                                dashboard.log.warning(f"Failed to send STOPALL action: {topic} = {message}")
                        else:
                            dashboard.log.warning("MQTT client not available for STOPALL command")
                    
                    return jsonify({
                        'success': True, 
                        'message': 'Scene stopped, audio/video stopped, and STOPALL command executed',
                        'stopall_executed': True,
                        'audio_stopped': audio_stopped,
                        'video_stopped': video_stopped
                    })
                    
                else:
                    dashboard.log.warning(f"STOPALL command file not found: {stopall_command_path}")
                    return jsonify({
                        'success': True, 
                        'message': 'Scene and audio/video stopped (STOPALL command not found)',
                        'stopall_executed': False,
                        'audio_stopped': audio_stopped,
                        'video_stopped': video_stopped
                    })
                    
            except Exception as stopall_error:
                dashboard.log.error(f"Error executing STOPALL command: {stopall_error}")
                return jsonify({
                    'success': True, 
                    'message': 'Scene and audio/video stopped but STOPALL command failed',
                    'stopall_executed': False,
                    'stopall_error': str(stopall_error),
                    'audio_stopped': audio_stopped,
                    'video_stopped': video_stopped
                })
                
        except Exception as e:
            dashboard.log.error(f"Error stopping scene: {e}")
            return jsonify({'error': f"Error stopping scene: {e}"}), 500

    @api_bp.route('/commands')
    @requires_auth
    def list_commands():
        """List all available command files with their metadata."""
        try:
            commands_path = get_commands_path()
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
            return jsonify({'error': f"Error listing commands: {e}"}), 500

    @api_bp.route('/config/main_scene')
    @requires_auth
    def get_main_scene():
        """Get the configured main scene filename."""
        return jsonify({
            'json_file_name': controller.json_file_name
        })

    @api_bp.route('/command/<command_name>')
    @requires_auth
    def get_command(command_name):
        """Retrieve the contents of a specific command file."""
        try:
            command_path = get_command_path(command_name)
            if not command_path.exists():
                return jsonify({'error': 'Command not found'}), 404
            with open(command_path, 'r') as f:
                return jsonify(json.load(f))
        except Exception as e:
            return jsonify({'error': f"Error loading command {command_name}: {e}"}), 500

    @api_bp.route('/command/<command_name>', methods=['POST'])
    @requires_auth
    def save_command(command_name):
        """Save a new or updated command file with validation."""
        try:
            command_data = request.json
            commands_path = get_commands_path()
            commands_path.mkdir(parents=True, exist_ok=True)
            command_path = commands_path / secure_filename(command_name + '.json')  # Ensure .json extension

            if not isinstance(command_data, list):
                return jsonify({'error': 'Command must be a list of actions'}), 400
            if not all('timestamp' in a and 'topic' in a and 'message' in a for a in command_data):
                return jsonify({'error': 'Invalid action format'}), 400

            with open(command_path, 'w') as f:
                json.dump(command_data, f, indent=2)
            dashboard.log.info(f"Command '{command_name}' saved successfully")
            return jsonify({'success': True, 'message': f'Command {command_name} saved successfully'})
        except Exception as e:
            return jsonify({'error': f"Error saving command {command_name}: {e}"}), 500

    @api_bp.route('/run_command/<command_name>', methods=['POST'])
    @requires_auth
    def run_command(command_name):
        """Execute a command immediately via MQTT."""
        try:
            command_path = get_command_path(command_name)
            if not command_path.exists():
                return jsonify({'error': 'Command not found'}), 404

            # Load and execute command actions
            with open(command_path, 'r') as f:
                command_data = json.load(f)

            for action in command_data:
                topic = action['topic']
                message = action['message']
                if hasattr(controller, 'mqtt_client') and controller.mqtt_client:
                    controller.mqtt_client.publish(topic, message)
                dashboard.log.info(f"Executed command action: {topic} = {message}")

            return jsonify({'success': True, 'message': f'Command {command_name} executed'})
        except Exception as e:
            return jsonify({'error': f"Error executing command {command_name}: {e}"}), 500

    return api_bp