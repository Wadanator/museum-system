#!/usr/bin/env python3
"""Main Flask application for the Web Dashboard."""

import time
import threading
import logging
from flask import Flask
from flask_socketio import SocketIO

from .config import Config
from .dashboard import WebDashboard
from .routes.main import main_bp
from .routes.api import setup_api_routes
from .routes.system import setup_system_routes

def create_app(controller):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['ENV'] = 'production'
    
    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        logger=False,
        engineio_logger=False,
        ping_timeout=60,
        ping_interval=25
    )
    
    # Create dashboard instance
    dashboard = WebDashboard(controller, app, socketio)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(setup_api_routes(dashboard))
    app.register_blueprint(setup_system_routes(dashboard))
    
    return app, socketio, dashboard

def start_web_dashboard(controller, port: int = Config.DEFAULT_PORT):
    """Start the web dashboard in a separate thread."""
    app, socketio, dashboard = create_app(controller)
    
    def run_dashboard():
        """Thread function to run the dashboard."""
        logger = logging.getLogger('WEB')
        logger.info(f"Starting web dashboard on 0.0.0.0:{port}")
        
        while True: 
            try:
                socketio.run(
                    app,
                    host='0.0.0.0',
                    port=port,
                    debug=False,
                    use_reloader=False,
                    allow_unsafe_werkzeug=True
                )
            except Exception as e:
                logger.error(f"WEB crashed: {e}. Restarting in 10s...")
                time.sleep(10)
    
    thread = threading.Thread(target=run_dashboard, daemon=True)
    thread.start()
    
    logger = logging.getLogger('WEB')
    logger.info(f"Web dashboard started on port {port}")
    return dashboard