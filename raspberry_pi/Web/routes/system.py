#!/usr/bin/env python3
"""API routes for System Operations (Restart, Shutdown)."""

import threading
from flask import Blueprint, jsonify
from ..auth import requires_auth

system_bp = Blueprint('system', __name__, url_prefix='/api')

def setup_system_routes(dashboard):
    controller = dashboard.controller

    # 1. Reštart služby (Python)
    @system_bp.route('/system/restart_service', methods=['POST'])
    @requires_auth
    def restart_service():
        """Restart the Python service only."""
        dashboard.log.warning("Service restart requested via API.")
        if hasattr(controller, 'service_restart'):
            threading.Thread(target=controller.service_restart, daemon=True).start()
            return jsonify({'success': True, 'message': 'Service restarting...'}), 200
        return jsonify({'error': 'Not supported'}), 500

    # 2. Reštart systému (RPi Reboot)
    @system_bp.route('/system/reboot', methods=['POST'])
    @requires_auth
    def reboot_system():
        """Reboot the whole OS."""
        dashboard.log.warning("System reboot requested via API.")
        if hasattr(controller, 'system_restart'): # V main.py sa to volá system_restart
            threading.Thread(target=controller.system_restart, daemon=True).start()
            return jsonify({'success': True, 'message': 'System reboot initiated'}), 200
        return jsonify({'error': 'Not supported'}), 500

    # 3. Vypnutie systému (RPi Shutdown)
    @system_bp.route('/system/shutdown', methods=['POST'])
    @requires_auth
    def shutdown_system():
        """Shutdown the whole OS."""
        dashboard.log.warning("System shutdown requested via API.")
        if hasattr(controller, 'system_shutdown'):
            threading.Thread(target=controller.system_shutdown, daemon=True).start()
            return jsonify({'success': True, 'message': 'System shutdown initiated'}), 200
        return jsonify({'error': 'Not supported'}), 500

    return system_bp