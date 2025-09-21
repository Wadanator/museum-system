#!/usr/bin/env python3
"""System control routes for the Web Dashboard."""

from flask import Blueprint, jsonify
from ..auth import requires_auth
from ..utils.helpers import execute_system_command

system_bp = Blueprint('system', __name__, url_prefix='/api/system')

def setup_system_routes(dashboard):
    """Setup system routes with dashboard context."""
    
    @system_bp.route('/restart', methods=['POST'])
    @requires_auth
    def restart_system():
        """Initiate a system reboot."""
        result = execute_system_command(
            ['sudo', 'reboot'], 'System Restart', dashboard.log
        )
        dashboard.save_stats()
        
        if 'error' in result:
            return jsonify(result), 500
        return jsonify(result)

    @system_bp.route('/shutdown', methods=['POST'])
    @requires_auth
    def shutdown_system():
        """Initiate a system shutdown."""
        result = execute_system_command(
            ['sudo', 'shutdown', '-h', 'now'], 'System Shutdown', dashboard.log
        )
        dashboard.save_stats()
        
        if 'error' in result:
            return jsonify(result), 500
        return jsonify(result)

    @system_bp.route('/service/restart', methods=['POST'])
    @requires_auth
    def restart_service():
        """Restart the museum system service."""
        result = execute_system_command(
            ['sudo', 'systemctl', 'restart', 'museum-system.service'], 
            'Service Restart', dashboard.log
        )
        
        if 'error' in result:
            return jsonify(result), 500
        return jsonify(result)

    return system_bp