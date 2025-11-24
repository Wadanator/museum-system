#!/usr/bin/env python3
"""API routes for Command Management and Execution."""

import json
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from ..auth import requires_auth
from ..utils.helpers import get_commands_path, get_command_path

# --- KOREKCIA: Odstránený url_prefix='/api' ---
commands_bp = Blueprint('commands', __name__)

def setup_commands_routes(dashboard):
    controller = dashboard.controller

    @commands_bp.route('/commands')
    @requires_auth
    def list_commands():
        """List all available command files with their metadata."""
        try:
            commands_path = get_commands_path()
            commands = []
            if commands_path.exists():
                commands = [{
                    'name': file.stem, 
                    'path': str(file),
                    'modified': file.stat().st_mtime
                } for file in commands_path.glob('*.json')]
                commands.sort(key=lambda x: x['modified'], reverse=True)
            return jsonify(commands)
        except Exception as e:
            return jsonify({'error': f"Error listing commands: {e}"}), 500

    @commands_bp.route('/command/<command_name>')
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

    @commands_bp.route('/command/<command_name>', methods=['POST'])
    @requires_auth
    def save_command(command_name):
        """Save a new or updated command file with validation."""
        try:
            command_data = request.json
            commands_path = get_commands_path()
            commands_path.mkdir(parents=True, exist_ok=True)
            command_path = commands_path / secure_filename(command_name + '.json')

            if not isinstance(command_data, list):
                return jsonify({'error': 'Command must be a list of actions'}), 400
            if not all('topic' in a and 'message' in a for a in command_data):
                return jsonify({'error': 'Invalid action format (missing topic/message)'}), 400

            with open(command_path, 'w') as f:
                json.dump(command_data, f, indent=2)
            dashboard.log.info(f"Command '{command_name}' saved successfully")
            return jsonify({'success': True, 'message': f'Command {command_name} saved successfully'})
        except Exception as e:
            return jsonify({'error': f"Error saving command {command_name}: {e}"}), 500

    @commands_bp.route('/run_command/<command_name>', methods=['POST'])
    @requires_auth
    def run_command(command_name):
        """Execute a command immediately via MQTT."""
        try:
            command_path = get_command_path(command_name)
            if not command_path.exists():
                return jsonify({'error': 'Command not found'}), 404

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

    return commands_bp