#!/usr/bin/env python3
"""API routes for Command Management and Manual Control."""

import json
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from ..auth import requires_auth
from ..utils.helpers import get_commands_path, get_command_path, get_scenes_path

commands_bp = Blueprint('commands', __name__)

def setup_commands_routes(dashboard):
    controller = dashboard.controller

    # --- 1. DEVICES CONFIG (scenes/room1/devices.json) ---
    @commands_bp.route('/devices')
    @requires_auth
    def get_devices():
        """Vráti zoznam zariadení zo súboru devices.json v zložke aktuálnej miestnosti."""
        try:
            room_path = get_scenes_path(controller)
            devices_config_path = room_path / 'devices.json'

            if not devices_config_path.exists():
                return jsonify({'relays': [], 'motors': []})
            
            with open(devices_config_path, 'r') as f:
                return jsonify(json.load(f))
        except Exception as e:
            dashboard.log.error(f"Error loading devices config: {e}")
            return jsonify({'error': f"Config error: {e}"}), 500

    # --- 2. PRIAME MQTT (MANUÁLNE OVLÁDANIE) ---
    @commands_bp.route('/mqtt/send', methods=['POST'])
    @requires_auth
    def send_mqtt_direct():
        """Odošle MQTT správu okamžite bez vytvárania súboru."""
        try:
            data = request.json
            topic = data.get('topic')
            message = data.get('message')

            if not topic or message is None:
                return jsonify({'error': 'Missing topic or message'}), 400

            payload = json.dumps(message) if isinstance(message, (dict, list)) else str(message)

            if hasattr(controller, 'mqtt_client') and controller.mqtt_client:
                controller.mqtt_client.publish(topic, payload)
                dashboard.log.info(f"Manual MQTT: {topic} -> {payload}")
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'MQTT client not connected'}), 503
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # --- 3. JSON COMMAND SÚBORY (scenes/room1/commands/*.json) ---
    @commands_bp.route('/commands')
    @requires_auth
    def list_commands():
        """List all available command files in the ROOM directory."""
        try:
            commands_path = get_commands_path(controller)
            
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
            command_path = get_command_path(controller, command_name)
            
            if not command_path.exists():
                return jsonify({'error': 'Command not found'}), 404
            with open(command_path, 'r') as f:
                return jsonify(json.load(f))
        except Exception as e:
            return jsonify({'error': f"Error loading command {command_name}: {e}"}), 500

    @commands_bp.route('/command/<command_name>', methods=['POST'])
    @requires_auth
    def save_command(command_name):
        """Save a new or updated command file."""
        try:
            command_data = request.json
            commands_path = get_commands_path(controller)
            commands_path.mkdir(parents=True, exist_ok=True)
            
            command_path = commands_path / secure_filename(command_name + '.json')

            if not isinstance(command_data, list):
                return jsonify({'error': 'Command must be a list of actions'}), 400

            with open(command_path, 'w') as f:
                json.dump(command_data, f, indent=2)
            dashboard.log.info(f"Command '{command_name}' saved successfully to {command_path}")
            return jsonify({'success': True, 'message': f'Command {command_name} saved successfully'})
        except Exception as e:
            return jsonify({'error': f"Error saving command {command_name}: {e}"}), 500

    @commands_bp.route('/run_command/<command_name>', methods=['POST'])
    @requires_auth
    def run_command(command_name):
        """Execute a command file immediately via MQTT."""
        try:
            command_path = get_command_path(controller, command_name)
            
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