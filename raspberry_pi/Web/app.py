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

_WEB_FAST_RETRY_DELAYS_SECONDS = (2, 4, 8)
_WEB_SLOW_RETRY_SECONDS = 300
_WEB_SLOW_LOG_INTERVAL_SECONDS = 900
_WEB_STABLE_RUN_SECONDS = 60


def create_app(controller):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['ENV'] = 'production'
    app.config['CONTROLLER'] = controller
    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=False,
        engineio_logger=False,
        ping_timeout=60,
        ping_interval=25,
        # Keep Socket.IO on the standard polling handshake with optional
        # websocket upgrade. Forcing websocket-only under Werkzeug can produce
        # noisy "write() before start_response" request errors during reconnects.
        transports=['polling', 'websocket']
    )
    
    # Create dashboard instance
    dashboard = WebDashboard(controller, app, socketio)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(setup_api_routes(dashboard))
    app.register_blueprint(setup_system_routes(dashboard))
    
    return app, socketio, dashboard


def _set_web_server_status(dashboard, state, **kwargs) -> None:
    setter = getattr(dashboard, 'set_web_server_status', None)
    if callable(setter):
        setter(state, **kwargs)


def _wait_for_retry(delay_seconds, sleep_func, stop_event=None) -> bool:
    if stop_event is not None and stop_event.is_set():
        return False
    sleep_func(delay_seconds)
    return stop_event is None or not stop_event.is_set()


def _web_retry_should_stop(dashboard, stop_event=None) -> bool:
    if stop_event is not None and stop_event.is_set():
        return True
    controller = getattr(dashboard, 'controller', None)
    return bool(
        getattr(controller, 'shutdown_requested', False)
        or getattr(controller, '_cleaned_up', False)
    )


def _run_dashboard_with_retries(
    app,
    socketio,
    dashboard,
    port,
    logger,
    *,
    sleep_func=time.sleep,
    stop_event=None,
):
    """Run SocketIO with bounded fast retries and slow degraded retries."""
    failed_starts = 0
    degraded_logged = False
    last_degraded_log_at = 0.0

    while not _web_retry_should_stop(dashboard, stop_event):
        _set_web_server_status(
            dashboard,
            'running',
            failed_starts=0,
            next_retry_seconds=None,
        )
        run_started_at = time.monotonic()

        try:
            socketio.run(
                app,
                host='0.0.0.0',
                port=port,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
            error = RuntimeError("Web dashboard server stopped unexpectedly")
        except Exception as exc:
            error = exc

        if _web_retry_should_stop(dashboard, stop_event):
            break

        if time.monotonic() - run_started_at >= _WEB_STABLE_RUN_SECONDS:
            failed_starts = 0
            degraded_logged = False

        failed_starts += 1
        fast_retry_index = failed_starts - 1

        if fast_retry_index < len(_WEB_FAST_RETRY_DELAYS_SECONDS):
            retry_delay = _WEB_FAST_RETRY_DELAYS_SECONDS[fast_retry_index]
            _set_web_server_status(
                dashboard,
                'retrying',
                last_error=error,
                failed_starts=failed_starts,
                next_retry_seconds=retry_delay,
            )
            logger.error(
                "WEB crashed: %s. Restarting in %.0fs "
                "(attempt %d/%d)...",
                error,
                retry_delay,
                failed_starts,
                len(_WEB_FAST_RETRY_DELAYS_SECONDS),
            )
        else:
            retry_delay = _WEB_SLOW_RETRY_SECONDS
            _set_web_server_status(
                dashboard,
                'degraded',
                last_error=error,
                failed_starts=failed_starts,
                next_retry_seconds=retry_delay,
            )

            now = time.monotonic()
            if not degraded_logged:
                logger.error(
                    "Web dashboard degraded after %d failed starts; "
                    "retrying every %.0fs. Last error: %s",
                    failed_starts,
                    retry_delay,
                    error,
                )
                degraded_logged = True
                last_degraded_log_at = now
            elif now - last_degraded_log_at >= _WEB_SLOW_LOG_INTERVAL_SECONDS:
                logger.warning(
                    "Web dashboard still degraded; retrying every %.0fs. "
                    "Last error: %s",
                    retry_delay,
                    error,
                )
                last_degraded_log_at = now
            else:
                logger.debug(
                    "Web dashboard retry failed while degraded: %s",
                    error,
                )

        if not _wait_for_retry(retry_delay, sleep_func, stop_event):
            break


def start_web_dashboard(controller, port: int = Config.DEFAULT_PORT):
    """Start the web dashboard in a separate thread."""
    app, socketio, dashboard = create_app(controller)
    
    def run_dashboard():
        """Thread function to run the dashboard."""
        logger = logging.getLogger('museum.web')
        logger.debug(f"Starting web dashboard on 0.0.0.0:{port}")
        _run_dashboard_with_retries(app, socketio, dashboard, port, logger)
    
    thread = threading.Thread(target=run_dashboard, daemon=True)
    thread.start()
    
    logger = logging.getLogger('museum.web')
    logger.debug(f"Web dashboard started on port {port}")
    return dashboard
