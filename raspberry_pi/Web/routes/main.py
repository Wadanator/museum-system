#!/usr/bin/env python3
"""Main routes for the Web Dashboard."""

from flask import Blueprint, send_from_directory
from ..auth import requires_auth

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@requires_auth
def dashboard():
    """Serve the main dashboard HTML page."""
    return send_from_directory('.', 'dashboard.html')

@main_bp.route('/static/<path:filename>')
@requires_auth  
def static_files(filename):
    """Serve static files from the static directory."""
    return send_from_directory('static', filename)