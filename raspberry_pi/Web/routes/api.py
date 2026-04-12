#!/usr/bin/env python3
"""
Main API module for the Web Dashboard.
Registers and combines all API sub-blueprints.
"""

from flask import Blueprint

from .status import setup_status_routes
from .scenes import setup_scenes_routes
from .commands import setup_commands_routes
from .device_states import setup_device_states_routes
from .media import media_bp

api_bp = Blueprint('api', __name__, url_prefix='/api')


def setup_api_routes(dashboard):
    """Aggregate all sub-blueprints into a single API blueprint."""

    api_bp.register_blueprint(setup_status_routes(dashboard))
    api_bp.register_blueprint(setup_scenes_routes(dashboard))
    api_bp.register_blueprint(setup_commands_routes(dashboard))
    api_bp.register_blueprint(setup_device_states_routes(dashboard))
    api_bp.register_blueprint(media_bp, url_prefix='/media')

    return api_bp