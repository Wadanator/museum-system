#!/usr/bin/env python3
"""API routes for System Operations (Restart, Shutdown)."""

import threading
from flask import Blueprint, jsonify
from ..auth import requires_auth

system_bp = Blueprint('system', __name__, url_prefix='/api')

def setup_system_routes(dashboard):
    controller = dashboard.controller

    @system_bp.route('/system/restart', methods=['POST'])
    @requires_auth
    def restart_system():
        """Endpoint to restart the entire Raspberry Pi system."""
        dashboard.log.warning("System restart requested via API.")
        if hasattr(controller, 'system_restart'):
            # Spustenie v novom vlákne, aby API volanie hneď vrátilo odpoveď
            threading.Thread(target=controller.system_restart, daemon=True).start()
            return jsonify({'success': True, 'message': 'System restart initiated'}), 200
        return jsonify({'error': 'System restart functionality not available'}), 500

    @system_bp.route('/system/service/restart', methods=['POST'])
    @requires_auth
    def restart_service():
        """Endpoint to restart the museum service only."""
        dashboard.log.warning("Museum service restart requested via API.")
        if hasattr(controller, 'service_restart'):
            threading.Thread(target=controller.service_restart, daemon=True).start()
            return jsonify({'success': True, 'message': 'Museum service restart initiated'}), 200
        return jsonify({'error': 'Service restart functionality not available'}), 500

    return system_bp