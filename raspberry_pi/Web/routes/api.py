#!/usr/bin/env python3
"""
Hlavný API modul pre Web Dashboard.
Registruje a kombinuje všetky ostatné API sub-moduly.
"""

from flask import Blueprint
from .status import setup_status_routes
from .scenes import setup_scenes_routes
from .commands import setup_commands_routes

api_bp = Blueprint('api', __name__, url_prefix='/api') 

def setup_api_routes(dashboard):
    """Setup a single Blueprint by aggregating all sub-blueprints."""

    api_bp.register_blueprint(setup_status_routes(dashboard))
    
    api_bp.register_blueprint(setup_scenes_routes(dashboard))

    api_bp.register_blueprint(setup_commands_routes(dashboard))
    
    return api_bp