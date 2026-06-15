#!/usr/bin/env python3
"""API routes for Status, Logs, and Monitoring."""

import io
import json
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file
from ..auth import requires_auth

# --- KOREKCIA: Odstránený url_prefix='/api' ---
status_bp = Blueprint('status', __name__) 

def _get_ambient_status_data(controller):
    ambient_service = getattr(controller, '_ambient_loop_service', None)
    if callable(ambient_service):
        return ambient_service().get_status()
    return {
        'enabled': False,
        'scene': None,
        'suspended': False,
        'start_policy': 'after_initial_connection_attempt',
        'cycle_cleanup': 'scene_only',
        'next_restart_at': None,
        'last_outcome': 'never_started',
    }

# Pomocná funkcia na získanie dát o stave systému
def _get_current_status_data(controller):
    config = getattr(controller, 'config', {}) or {}
    return {
        'room_id': getattr(controller, 'room_id', 'Unknown'),
        'scene_running': getattr(controller, 'scene_running', False),
        'current_scene_name': getattr(controller, 'current_scene_name', None),
        'active_state': getattr(controller, 'current_scene_state', None),
        'mqtt_connected': controller.mqtt_client.is_connected() if controller.mqtt_client else False,
        'default_scene': config.get(
            'json_file_name',
            getattr(controller, 'json_file_name', None),
        ),
        'startup_mode': config.get('startup_mode', 'classic'),
        'ambient': _get_ambient_status_data(controller),
    }

def setup_status_routes(dashboard):
    controller = dashboard.controller

    @status_bp.route('/status')
    @requires_auth
    def get_status():
        """Return current system status including room ID, scene state, and uptime."""
        status_data = _get_current_status_data(controller)
        status_data['uptime'] = dashboard.get_uptime()
        status_data['log_count'] = dashboard.get_log_count()
        return jsonify(status_data)

    @status_bp.route('/runtime')
    @requires_auth
    def get_runtime():
        """Return a complete runtime snapshot for page load/reconnect recovery."""
        return jsonify(dashboard.get_runtime_snapshot())

    @status_bp.route('/stats')
    @requires_auth
    def get_stats():
        """Retrieve and return dashboard statistics."""
        dashboard.update_stats()
        return jsonify(dashboard.stats)

    @status_bp.route('/logs')
    @requires_auth
    def get_logs():
        """Fetch logs with optional level filtering and limit."""
        level_filter = request.args.get('level', '').upper()
        try:
            limit = min(int(request.args.get('limit', 500)), 1000)
        except ValueError:
            limit = 500
        filtered_logs = dashboard.filter_logs(level_filter, limit)
        return jsonify(filtered_logs)

    @status_bp.route('/logs/clear', methods=['POST'])
    @requires_auth
    def clear_logs():
        """Clear the in-memory log buffer and notify connected clients."""
        dashboard.clear_log_buffer()
        dashboard._broadcast_event('logs_cleared', None)
        return jsonify({'success': True, 'message': 'Logs cleared'})

    @status_bp.route('/logs/export')
    @requires_auth
    def export_logs():
        """Export logs as a JSON file for download."""
        try:
            log_history = dashboard.get_log_history()
            buf = io.BytesIO(json.dumps(log_history, indent=2).encode('utf-8'))
            return send_file(
                buf,
                as_attachment=True,
                download_name=f'museum_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                mimetype='application/json'
            )
        except Exception as e:
            return jsonify({'error': f"Error exporting logs: {e}"}), 500

    return status_bp
