#!/usr/bin/env python3
"""API routes for Command Management and Manual Control."""

import json
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from ..auth import requires_auth
from ..utils.helpers import (
    get_commands_path,
    get_command_path,
    get_scenes_path,
    get_devices_config_path,
)

commands_bp = Blueprint('commands', __name__)

def setup_commands_routes(dashboard):
    controller = dashboard.controller

    def _get_display_power_manager():
        manager = getattr(controller, 'display_power_manager', None)
        if manager and hasattr(manager, 'get_status'):
            return manager
        return None

    def _get_display_status_data(manager=None):
        manager = manager or _get_display_power_manager()
        room_id = getattr(controller, 'room_id', None)
        topic = f'{room_id}/display' if room_id else None

        if manager:
            status = dict(manager.get_status() or {})
            status.setdefault('enabled', False)
            status.setdefault('backend', 'unknown')
            status.setdefault('active_reasons', [])
            status.setdefault('requested_state', 'unknown')
            status.setdefault('pending_standby_at', None)
            status.setdefault('last_command', None)
            status.setdefault('last_result', None)
            status.setdefault('last_error', None)
            status['available'] = True
            status['topic'] = topic
            return status

        return {
            'available': False,
            'enabled': False,
            'backend': 'none',
            'active_reasons': [],
            'requested_state': 'unknown',
            'pending_standby_at': None,
            'last_command': None,
            'last_result': None,
            'last_error': None,
            'topic': topic,
        }

    def _broadcast_status_if_possible():
        broadcaster = getattr(dashboard, 'broadcast_status', None)
        if callable(broadcaster):
            broadcaster()

    def _is_room_stop_command(topic, payload):
        room_id = getattr(controller, 'room_id', None)
        return (
            bool(room_id)
            and topic == f'{room_id}/STOP'
            and str(payload).strip().upper() == 'STOP'
        )

    # --- 1. DEVICES CONFIG (config/rooms/<room_id>/devices.json) ---
    @commands_bp.route('/devices')
    @requires_auth
    def get_devices():
        """Return room devices config. Uses room config path with legacy fallback."""
        try:
            devices_config_path = get_devices_config_path(controller)

            # Legacy fallback for older deployments (scenes/<room>/devices.json)
            if not devices_config_path.exists():
                legacy_path = get_scenes_path(controller) / 'devices.json'
                if legacy_path.exists():
                    with open(legacy_path, 'r', encoding='utf-8') as f:
                        legacy_data = json.load(f)
                    # Auto-migrate legacy file to new room-config location
                    with open(devices_config_path, 'w', encoding='utf-8') as f:
                        json.dump(legacy_data, f, indent=2)
                    dashboard.log.info(
                        f"Migrated devices config from {legacy_path} to {devices_config_path}"
                    )
                    return jsonify(legacy_data)
                return jsonify({'relays': [], 'motors': [], 'windows': []})

            with open(devices_config_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except Exception as e:
            dashboard.log.error(f"Error loading devices config: {e}")
            return jsonify({'error': f"Config error: {e}"}), 500

    @commands_bp.route('/devices', methods=['POST'])
    @requires_auth
    def save_devices():
        """Save room devices config JSON to room-specific config path."""
        try:
            devices_data = request.json
            if not isinstance(devices_data, dict):
                return jsonify({'error': 'Devices config must be an object'}), 400

            # Keep compatibility with current UI expectations
            if all(key not in devices_data for key in ('motors', 'relays', 'lights', 'windows')):
                return jsonify({'error': 'Devices config must include motors/relays/lights/windows keys'}), 400

            devices_config_path = get_devices_config_path(controller)
            with open(devices_config_path, 'w', encoding='utf-8') as f:
                json.dump(devices_data, f, indent=2)

            store = getattr(controller, 'actuator_state_store', None)
            if store:
                store.initialize_from_devices_config(devices_data)

            dashboard.log.info(f"Devices config saved: {devices_config_path}")
            return jsonify({'success': True, 'path': str(devices_config_path)})
        except Exception as e:
            dashboard.log.error(f"Error saving devices config: {e}")
            return jsonify({'error': str(e)}), 500

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
                success = controller.mqtt_client.publish(
                    topic,
                    payload,
                    force_feedback=True,
                )
                if not success:
                    return jsonify({'error': 'MQTT publish failed - broker may be disconnected'}), 503
                if _is_room_stop_command(topic, payload):
                    store = getattr(controller, 'actuator_state_store', None)
                    if store:
                        store.force_all_off(source='manual_mqtt_stop')
                dashboard.log.info(f"[MANUAL] MQTT: {topic} = {payload}")
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'MQTT client not available'}), 503
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # --- 3. PRIAME OVLÁDANIE HDMI/CEC DISPLEJA ---
    @commands_bp.route('/display/status')
    @requires_auth
    def get_display_status():
        """Return local display power manager status for manual dashboard control."""
        return jsonify({
            'success': True,
            'status': _get_display_status_data(),
        })

    @commands_bp.route('/display/on', methods=['POST'])
    @requires_auth
    def display_on():
        """Queue an immediate local display ON request."""
        manager = _get_display_power_manager()
        if not manager or not hasattr(manager, 'force_on'):
            return jsonify({
                'success': False,
                'error': 'Display power manager not available',
                'status': _get_display_status_data(manager),
            }), 503

        if not getattr(manager, 'enabled', False):
            return jsonify({
                'success': False,
                'error': 'Display power control is disabled',
                'status': _get_display_status_data(manager),
            }), 409

        try:
            queued = bool(manager.force_on('dashboard_manual'))
            dashboard.log.info("[MANUAL] Display ON requested from dashboard")
            _broadcast_status_if_possible()
            return jsonify({
                'success': queued,
                'queued': queued,
                'status': _get_display_status_data(manager),
            })
        except Exception as e:
            dashboard.log.error(f"Error requesting display ON: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'status': _get_display_status_data(manager),
            }), 500

    @commands_bp.route('/display/off', methods=['POST'])
    @requires_auth
    def display_off():
        """Queue an immediate local display standby request."""
        manager = _get_display_power_manager()
        if not manager or not hasattr(manager, 'force_standby'):
            return jsonify({
                'success': False,
                'error': 'Display power manager not available',
                'status': _get_display_status_data(manager),
            }), 503

        if not getattr(manager, 'enabled', False):
            return jsonify({
                'success': False,
                'error': 'Display power control is disabled',
                'status': _get_display_status_data(manager),
            }), 409

        try:
            queued = bool(manager.force_standby('dashboard_manual'))
            dashboard.log.info("[MANUAL] Display STANDBY requested from dashboard")
            _broadcast_status_if_possible()
            return jsonify({
                'success': queued,
                'queued': queued,
                'status': _get_display_status_data(manager),
            })
        except Exception as e:
            dashboard.log.error(f"Error requesting display STANDBY: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'status': _get_display_status_data(manager),
            }), 500

    # --- 4. JSON COMMAND SÚBORY (scenes/room1/commands/*.json) ---
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

            dashboard.log.info(f"[MANUAL] Command '{command_name}' executed ({len(command_data)} actions)")
            for action in command_data:
                topic = action['topic']
                message = action['message']
                if hasattr(controller, 'mqtt_client') and controller.mqtt_client:
                    success = controller.mqtt_client.publish(
                        topic,
                        message,
                        force_feedback=True,
                    )
                    if not success:
                        return jsonify({'error': f'MQTT publish failed on action: {topic} - broker may be disconnected'}), 503
                    if _is_room_stop_command(topic, message):
                        store = getattr(controller, 'actuator_state_store', None)
                        if store:
                            store.force_all_off(source='manual_command_stop')
                else:
                    return jsonify({'error': 'MQTT client not available'}), 503
                dashboard.log.debug(f"  -> {topic} = {message}")

            return jsonify({'success': True, 'message': f'Command {command_name} executed'})
        except Exception as e:
            return jsonify({'error': f"Error executing command {command_name}: {e}"}), 500

    return commands_bp

