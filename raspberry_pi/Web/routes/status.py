#!/usr/bin/env python3
"""API routes for Status, Logs, and Monitoring."""

import io
import json
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file
from ..auth import requires_auth

# --- KOREKCIA: Odstránený url_prefix='/api' ---
status_bp = Blueprint('status', __name__) 

# Pomocná funkcia na získanie dát o stave systému
def _get_current_status_data(controller):
    return {
        'room_id': getattr(controller, 'room_id', 'Unknown'),
        'scene_running': getattr(controller, 'scene_running', False),
        'mqtt_connected': controller.mqtt_client.is_connected() if controller.mqtt_client else False,
    }

def setup_status_routes(dashboard):
    controller = dashboard.controller

    @status_bp.route('/status')
    @requires_auth
    def get_status():
        """Return current system status including room ID, scene state, and uptime."""
        status_data = _get_current_status_data(controller)
        status_data['uptime'] = dashboard.get_uptime()
        status_data['log_count'] = len(dashboard.log_buffer)
        return jsonify(status_data)

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
        dashboard.log_buffer.clear()
        dashboard._broadcast_event('logs_cleared', None)
        return jsonify({'success': True, 'message': 'Logs cleared'})

    @status_bp.route('/logs/export')
    @requires_auth
    def export_logs():
        """Export logs as a JSON file for download."""
        try:
            buf = io.BytesIO(json.dumps(dashboard.log_buffer, indent=2).encode('utf-8'))
            return send_file(
                buf,
                as_attachment=True,
                download_name=f'museum_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                mimetype='application/json'
            )
        except Exception as e:
            return jsonify({'error': f"Error exporting logs: {e}"}), 500

    return status_bp