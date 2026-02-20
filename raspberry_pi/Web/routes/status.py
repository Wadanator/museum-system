#!/usr/bin/env python3
"""API routes for Status, Logs, and Monitoring."""

import json
import tempfile
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

    @status_bp.route('/scene/progress')
    @requires_auth
    def get_scene_progress():
        """[DEPRECATED/FALLBACK] Vráti aktuálny stav progresu scény. Nahradené SocketIO."""
        try:
            scene_running = getattr(controller, 'scene_running', False)
            if not scene_running or not hasattr(controller, 'scene_parser') or not controller.scene_parser:
                return jsonify({'scene_running': False, 'mode': 'none', 'progress': 0.0, 'remaining_time': 0, 'total_duration': 0})
            
            progress_info = controller.scene_parser.get_progress_info()
            
            return jsonify({
                **progress_info,
                'progress': min(1.0, progress_info.get('states_completed', 0) / max(progress_info.get('total_states', 1), 1)),
                'remaining_time': 0  
            })
            
        except Exception as e:
            dashboard.log.error(f"Error getting scene progress: {e}")
            return jsonify({'scene_running': False, 'mode': 'error', 'progress': 0.0, 'remaining_time': 0, 'total_duration': 0, 'error': str(e)}), 500

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
        limit = int(request.args.get('limit', 500))
        filtered_logs = dashboard.filter_logs(level_filter, limit)
        return jsonify(filtered_logs)

    @status_bp.route('/logs/clear', methods=['POST'])
    @requires_auth
    def clear_logs():
        """Clear the in-memory log buffer and notify connected clients."""
        dashboard.log_buffer.clear()
        dashboard.socketio.emit('logs_cleared')
        return jsonify({'success': True, 'message': 'Logs cleared'})

    @status_bp.route('/logs/export')
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

    return status_bp