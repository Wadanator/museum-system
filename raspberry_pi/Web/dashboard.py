#!/usr/bin/env python3
"""Refactored Web Dashboard - Main dashboard class."""

import json
import logging
import queue
import sqlite3
import time
import os
import base64
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from flask import request as flask_request

from .config import Config
from .handlers.log_handler import WebLogHandler
from .utils.helpers import format_uptime

class WebDashboard:
    """Web interface for controlling and monitoring the museum system."""

    INITIAL_LOG_HISTORY_LIMIT = 50
    REQUEST_LOG_HISTORY_LIMIT = 250
    LOG_FANOUT_QUEUE_LIMIT = 500
    LOG_FANOUT_DROP_WARNING_INTERVAL_SECONDS = 60
    RUNTIME_STATE_FANOUT_QUEUE_LIMIT = 500
    RUNTIME_STATE_FANOUT_DROP_WARNING_INTERVAL_SECONDS = 60
    
    def __init__(self, controller, app, socketio):
        self.controller = controller
        self.app = app
        self.socketio = socketio
        self.log = self._setup_logger()
        self._connected_sids = set()
        self._sids_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._web_server_status_lock = threading.Lock()
        self._web_server_status = {
            'state': 'starting',
            'last_error': None,
            'failed_starts': 0,
            'next_retry_seconds': None,
            'last_changed': time.time(),
        }
        
        self.log_buffer: List[Dict] = []  # In-memory log storage
        self._setup_log_fanout()
        self._setup_runtime_state_fanout()
        self.stats = {
            'total_scenes_played': 0,
            'scene_play_counts': {},
            'total_uptime': 0,
            'last_start_time': time.monotonic(),
            'connected_devices': {}
        }
        
        self._setup_logging()
        self._load_stats()
        self._setup_socketio_handlers()

    def _setup_log_fanout(self, start_worker: bool = True) -> None:
        """Initialize async websocket fanout for dashboard log entries."""
        self._log_lock = threading.Lock()
        self._log_fanout_queue = queue.Queue(maxsize=self.LOG_FANOUT_QUEUE_LIMIT)
        self._log_fanout_stop = threading.Event()
        self._dropped_log_fanout_events = 0
        self._last_log_drop_warning_ts = 0.0
        self._log_fanout_thread = None

        if start_worker:
            self._log_fanout_thread = threading.Thread(
                target=self._log_fanout_loop,
                name='dashboard-log-fanout',
                daemon=True,
            )
            self._log_fanout_thread.start()

    def _ensure_log_fanout_state(self) -> None:
        """Create log fanout fields for tests that instantiate with __new__."""
        if not hasattr(self, '_log_lock'):
            self._log_lock = threading.Lock()
        if not hasattr(self, '_log_fanout_queue'):
            self._log_fanout_queue = queue.Queue(maxsize=self.LOG_FANOUT_QUEUE_LIMIT)
        if not hasattr(self, '_log_fanout_stop'):
            self._log_fanout_stop = threading.Event()
        if not hasattr(self, '_dropped_log_fanout_events'):
            self._dropped_log_fanout_events = 0
        if not hasattr(self, '_last_log_drop_warning_ts'):
            self._last_log_drop_warning_ts = 0.0
        if not hasattr(self, '_log_fanout_thread'):
            self._log_fanout_thread = None

    def _setup_runtime_state_fanout(self, start_worker: bool = True) -> None:
        """Initialize async websocket fanout for actuator runtime states."""
        self._runtime_state_fanout_queue = queue.Queue(
            maxsize=self.RUNTIME_STATE_FANOUT_QUEUE_LIMIT
        )
        self._runtime_state_fanout_stop = threading.Event()
        self._dropped_runtime_state_fanout_events = 0
        self._last_runtime_state_drop_warning_ts = 0.0
        self._runtime_state_fanout_thread = None

        if start_worker:
            self._runtime_state_fanout_thread = threading.Thread(
                target=self._runtime_state_fanout_loop,
                name='dashboard-runtime-state-fanout',
                daemon=True,
            )
            self._runtime_state_fanout_thread.start()

    def _ensure_runtime_state_fanout_state(self) -> None:
        """Create runtime fanout fields for tests that instantiate with __new__."""
        if not hasattr(self, '_runtime_state_fanout_queue'):
            self._runtime_state_fanout_queue = queue.Queue(
                maxsize=self.RUNTIME_STATE_FANOUT_QUEUE_LIMIT
            )
        if not hasattr(self, '_runtime_state_fanout_stop'):
            self._runtime_state_fanout_stop = threading.Event()
        if not hasattr(self, '_dropped_runtime_state_fanout_events'):
            self._dropped_runtime_state_fanout_events = 0
        if not hasattr(self, '_last_runtime_state_drop_warning_ts'):
            self._last_runtime_state_drop_warning_ts = 0.0
        if not hasattr(self, '_runtime_state_fanout_thread'):
            self._runtime_state_fanout_thread = None

    def _append_log_entry_unlocked(self, log_entry: Dict) -> None:
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > Config.MAX_LOG_ENTRIES:
            self.log_buffer = self.log_buffer[-Config.MAX_LOG_ENTRIES:]

    def _append_log_entry_to_buffer(self, log_entry: Dict) -> None:
        self._ensure_log_fanout_state()
        with self._log_lock:
            self._append_log_entry_unlocked(log_entry)

    def get_log_history(self, limit: int = None) -> List[Dict]:
        """Return a stable snapshot of recent in-memory logs."""
        self._ensure_log_fanout_state()
        with self._log_lock:
            logs = list(self.log_buffer)

        if limit is not None and len(logs) > limit:
            return logs[-limit:]
        return logs

    def get_log_count(self) -> int:
        """Return the current in-memory log count."""
        self._ensure_log_fanout_state()
        with self._log_lock:
            return len(self.log_buffer)

    def clear_log_buffer(self) -> None:
        """Clear in-memory logs without touching persistent log files."""
        self._ensure_log_fanout_state()
        with self._log_lock:
            self.log_buffer.clear()

    def _queue_log_fanout(self, log_entry: Dict) -> None:
        self._ensure_log_fanout_state()
        try:
            self._log_fanout_queue.put_nowait(log_entry)
        except queue.Full:
            self._record_log_fanout_drop()

    def _record_log_fanout_drop(self) -> None:
        """Record a rate-limited in-buffer warning when websocket fanout lags."""
        self._ensure_log_fanout_state()
        now = time.monotonic()
        warning_entry = None

        with self._log_lock:
            self._dropped_log_fanout_events += 1
            if (
                self._last_log_drop_warning_ts
                and now - self._last_log_drop_warning_ts
                < self.LOG_FANOUT_DROP_WARNING_INTERVAL_SECONDS
            ):
                return

            dropped = self._dropped_log_fanout_events
            self._dropped_log_fanout_events = 0
            self._last_log_drop_warning_ts = now
            warning_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'level': 'WARNING',
                'module': 'web',
                'message': (
                    'Dashboard log websocket queue full; '
                    f'dropped {dropped} log event(s)'
                ),
            }
            self._append_log_entry_unlocked(warning_entry)

        try:
            self._log_fanout_queue.put_nowait(warning_entry)
        except queue.Full:
            pass

    def _drain_log_fanout_once(self, timeout: float = 0.5) -> bool:
        """Drain one queued log websocket event. Returns True when work was done."""
        self._ensure_log_fanout_state()
        try:
            log_entry = self._log_fanout_queue.get(timeout=timeout)
        except queue.Empty:
            return False

        try:
            self._broadcast_event('new_log', log_entry)
        except Exception:
            # Websocket fanout must never propagate back into logging/runtime code.
            pass
        finally:
            self._log_fanout_queue.task_done()

        return True

    def _log_fanout_loop(self) -> None:
        """Background worker that broadcasts queued log websocket events."""
        self._ensure_log_fanout_state()
        while not self._log_fanout_stop.is_set():
            self._drain_log_fanout_once(timeout=0.5)

    def stop_log_fanout_worker(self, timeout: float = 1.0) -> None:
        """Stop the dashboard log fanout worker; mainly useful for tests."""
        self._ensure_log_fanout_state()
        self._log_fanout_stop.set()
        thread = self._log_fanout_thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)

    def _queue_runtime_state_fanout(self, state_snapshot: dict) -> None:
        self._ensure_runtime_state_fanout_state()
        try:
            self._runtime_state_fanout_queue.put_nowait(dict(state_snapshot))
            return
        except queue.Full:
            self._drop_oldest_runtime_state_fanout_event()
            self._record_runtime_state_fanout_drop()

        try:
            self._runtime_state_fanout_queue.put_nowait(dict(state_snapshot))
        except queue.Full:
            self._record_runtime_state_fanout_drop()

    def _drop_oldest_runtime_state_fanout_event(self) -> None:
        self._ensure_runtime_state_fanout_state()
        try:
            self._runtime_state_fanout_queue.get_nowait()
            self._runtime_state_fanout_queue.task_done()
        except queue.Empty:
            pass

    def _record_runtime_state_fanout_drop(self) -> None:
        """Record a rate-limited warning when runtime-state fanout lags."""
        self._ensure_log_fanout_state()
        self._ensure_runtime_state_fanout_state()
        now = time.monotonic()
        warning_entry = None

        with self._log_lock:
            self._dropped_runtime_state_fanout_events += 1
            if (
                self._last_runtime_state_drop_warning_ts
                and now - self._last_runtime_state_drop_warning_ts
                < self.RUNTIME_STATE_FANOUT_DROP_WARNING_INTERVAL_SECONDS
            ):
                return

            dropped = self._dropped_runtime_state_fanout_events
            self._dropped_runtime_state_fanout_events = 0
            self._last_runtime_state_drop_warning_ts = now
            warning_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'level': 'WARNING',
                'module': 'web',
                'message': (
                    'Dashboard runtime-state websocket queue full; '
                    f'dropped {dropped} state update(s)'
                ),
            }
            self._append_log_entry_unlocked(warning_entry)

        try:
            self._log_fanout_queue.put_nowait(warning_entry)
        except queue.Full:
            pass

    def _drain_runtime_state_fanout_once(self, timeout: float = 0.5) -> bool:
        """
        Drain queued runtime-state websocket work.

        Returns True when at least one queued update was handled. Updates for
        the same topic are coalesced so the dashboard sees the newest state.
        """
        self._ensure_runtime_state_fanout_state()
        try:
            first_snapshot = self._runtime_state_fanout_queue.get(timeout=timeout)
        except queue.Empty:
            return False

        snapshots = [first_snapshot]
        while True:
            try:
                snapshots.append(self._runtime_state_fanout_queue.get_nowait())
            except queue.Empty:
                break

        latest_by_topic = {}
        topic_order = []
        no_topic_snapshots = []

        for snapshot in snapshots:
            topic = snapshot.get('topic') if isinstance(snapshot, dict) else None
            if topic:
                if topic not in latest_by_topic:
                    topic_order.append(topic)
                latest_by_topic[topic] = snapshot
            else:
                no_topic_snapshots.append(snapshot)

        try:
            for snapshot in no_topic_snapshots:
                self._broadcast_event('device_runtime_state_update', snapshot)
            for topic in topic_order:
                self._broadcast_event(
                    'device_runtime_state_update',
                    latest_by_topic[topic],
                )
        except Exception:
            # Dashboard fanout must never propagate into MQTT/runtime code.
            pass
        finally:
            for _snapshot in snapshots:
                self._runtime_state_fanout_queue.task_done()

        return True

    def _runtime_state_fanout_loop(self) -> None:
        """Background worker for queued actuator runtime-state websocket events."""
        self._ensure_runtime_state_fanout_state()
        while not self._runtime_state_fanout_stop.is_set():
            self._drain_runtime_state_fanout_once(timeout=0.5)

    def stop_runtime_state_fanout_worker(self, timeout: float = 1.0) -> None:
        """Stop the runtime-state fanout worker; mainly useful for tests."""
        self._ensure_runtime_state_fanout_state()
        self._runtime_state_fanout_stop.set()
        thread = self._runtime_state_fanout_thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)

    def _setup_logger(self):
        """Setup logger for dashboard."""
        from utils.logging_setup import get_logger
        return get_logger('web')

    def _setup_logging(self):
        """Configure logging handlers for the dashboard."""
        web_handler = WebLogHandler(self)
        for logger_name in ('museum', ''):
            logger = logging.getLogger(logger_name)
            logger.addHandler(web_handler)
        for logger_name in ('werkzeug', 'flask'):
            logging.getLogger(logger_name).setLevel(logging.ERROR)  # Suppress Flask/Werkzeug logs
        self.load_existing_logs()

    def _setup_socketio_handlers(self):
        """Setup SocketIO event handlers."""
        @self.socketio.on('connect')
        def handle_connect(auth=None):
            """Handle new SocketIO client connections with authentication."""
            credentials = flask_request.authorization
            if credentials is not None:
                if not self._check_auth(credentials.username, credentials.password):
                    return False
            else:
                username = None
                password = None

                # Browser Socket.IO clients commonly provide credentials via auth payload.
                token = None
                if isinstance(auth, dict):
                    token = auth.get("token")

                if token and isinstance(token, str) and token.startswith("Basic "):
                    try:
                        decoded = base64.b64decode(token[6:]).decode("utf-8")
                        username, password = decoded.split(":", 1)
                    except Exception:
                        return False
                else:
                    auth_header = flask_request.headers.get("Authorization", "")
                    if auth_header.startswith("Basic "):
                        try:
                            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                            username, password = decoded.split(":", 1)
                        except Exception:
                            return False

                if username is None or password is None:
                    return False

                if not self._check_auth(username, password):
                    return False

            try:
                with self._sids_lock:
                    self._connected_sids.add(flask_request.sid)

                # Send initial state on both initial connect and reconnect
                self._emit_to_sid(
                    'log_history',
                    self.get_log_history(self.INITIAL_LOG_HISTORY_LIMIT),
                    flask_request.sid,
                )
                self.update_stats()
                self._emit_to_sid('stats_update', self.stats, flask_request.sid)
                self._emit_to_sid('status_update', self._get_status_data(), flask_request.sid)
                self._emit_to_sid('runtime_snapshot', self.get_runtime_snapshot(), flask_request.sid)
                self.log.debug("SocketIO client connected")
            except Exception as e:
                self.log.error(f"Error on connect: {e}")

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle SocketIO client disconnections."""
            with self._sids_lock:
                self._connected_sids.discard(flask_request.sid)
            self.log.debug("SocketIO client disconnected")

        @self.socketio.on('request_logs')
        def handle_log_request():
            """Send log history to requesting SocketIO client."""
            try:
                # Avoid oversized websocket packets that can trigger disconnects.
                self._emit_to_sid(
                    'log_history',
                    self.get_log_history(self.REQUEST_LOG_HISTORY_LIMIT),
                    flask_request.sid,
                )
            except Exception as e:
                self.log.error(f"Error handling log request: {e}")

        @self.socketio.on('request_status')
        def handle_status_request():
            """Send current system status to requesting SocketIO client."""
            try:
                self._emit_to_sid('status_update', self._get_status_data(), flask_request.sid)
            except Exception as e:
                self.log.error(f"Error handling status request: {e}")

        @self.socketio.on('request_stats')
        def handle_stats_request():
            """Send updated statistics to requesting SocketIO client."""
            try:
                self.update_stats()
                self._emit_to_sid('stats_update', self.stats, flask_request.sid)
            except Exception as e:
                self.log.error(f"Error handling stats request: {e}")

        @self.socketio.on('request_runtime')
        def handle_runtime_request():
            """Send a complete runtime snapshot to requesting SocketIO client."""
            try:
                self._emit_to_sid('runtime_snapshot', self.get_runtime_snapshot(), flask_request.sid)
            except Exception as e:
                self.log.error(f"Error handling runtime request: {e}")

    def _emit_to_sid(self, event: str, payload, sid: str):
        """Emit an event to one connected client sid with a stable namespace."""
        self.socketio.emit(event, payload, to=sid, namespace='/')

    def _broadcast_event(self, event: str, payload):
        """Broadcast an event to all connected clients via explicit SID fanout."""
        with self._sids_lock:
            target_sids = list(self._connected_sids)

        for sid in target_sids:
            self._emit_to_sid(event, payload, sid)

    def _check_auth(self, username, password):
        """Check authentication credentials."""
        return username == Config.USERNAME and password == Config.PASSWORD

    def _get_status_data(self):
        """Get current system status data."""
        config = getattr(self.controller, 'config', {}) or {}
        return {
            'room_id': getattr(self.controller, 'room_id', 'Unknown'),
            'scene_running': getattr(self.controller, 'scene_running', False),
            'current_scene_name': getattr(self.controller, 'current_scene_name', None),
            'active_state': getattr(self.controller, 'current_scene_state', None),
            'mqtt_connected': self.controller.mqtt_client.is_connected() if self.controller.mqtt_client else False,
            'default_scene': config.get(
                'json_file_name',
                getattr(self.controller, 'json_file_name', None),
            ),
            'startup_mode': config.get('startup_mode', 'classic'),
            'ambient': self._get_ambient_status_data(),
            'display': self._get_display_status_data(),
            'web_dashboard': self.get_web_server_status(),
            'uptime': self.get_uptime(),
            'log_count': self.get_log_count()
        }

    def _get_ambient_status_data(self):
        ambient_service = getattr(self.controller, '_ambient_loop_service', None)
        if callable(ambient_service):
            return ambient_service().get_status()
        return {
            'enabled': False,
            'scene': None,
            'suspended': False,
            'start_policy': 'after_initial_connection_attempt',
            'cycle_cleanup': 'scene_only',
            'next_restart_at': None,
            'last_outcome': 'never_started',
        }

    def _get_display_status_data(self):
        display_power = getattr(self.controller, 'display_power_manager', None)
        if display_power and hasattr(display_power, 'get_status'):
            try:
                return display_power.get_status()
            except Exception as exc:
                self.log.error(f"Error reading display status: {exc}")
        return {
            'enabled': False,
            'backend': 'none',
            'active_reasons': [],
            'requested_state': 'unknown',
            'pending_standby_at': None,
            'last_command': None,
            'last_result': None,
            'last_error': None,
        }

    def _ensure_web_server_status_state(self) -> None:
        """Create web dashboard health fields for __new__ based tests."""
        if not hasattr(self, '_web_server_status_lock'):
            self._web_server_status_lock = threading.Lock()
        if not hasattr(self, '_web_server_status'):
            self._web_server_status = {
                'state': 'starting',
                'last_error': None,
                'failed_starts': 0,
                'next_retry_seconds': None,
                'last_changed': time.time(),
            }

    def set_web_server_status(
        self,
        state: str,
        *,
        last_error=None,
        failed_starts: int = 0,
        next_retry_seconds=None,
    ) -> None:
        """Record Flask/SocketIO serving health for diagnostics."""
        self._ensure_web_server_status_state()
        with self._web_server_status_lock:
            self._web_server_status = {
                'state': state,
                'last_error': str(last_error) if last_error else None,
                'failed_starts': int(failed_starts),
                'next_retry_seconds': next_retry_seconds,
                'last_changed': time.time(),
            }

    def get_web_server_status(self) -> dict:
        self._ensure_web_server_status_state()
        with self._web_server_status_lock:
            return dict(self._web_server_status)

    def get_device_runtime_states(self) -> list:
        """Return the current actuator runtime states without mutating dashboard stats."""
        store = getattr(self.controller, 'actuator_state_store', None)
        if store is None:
            return []
        return store.get_all_states()

    def get_runtime_snapshot(self) -> dict:
        """Return a complete runtime snapshot for page load/reconnect recovery."""
        connected_devices = {}
        registry = getattr(self.controller, 'mqtt_device_registry', None)
        if registry is not None:
            try:
                connected_devices = registry.get_connected_devices(cleanup=False)
            except Exception as exc:
                self.log.error(f"Error reading connected devices for runtime snapshot: {exc}")

        return {
            'status': self._get_status_data(),
            'device_states': self.get_device_runtime_states(),
            'connected_devices': connected_devices,
        }

    def get_uptime(self):
        """Get system uptime in seconds."""
        return time.monotonic() - getattr(self.controller, 'start_time', time.monotonic())

    def _load_existing_logs_from_legacy_text_file_unused(self):
        """Efektívne načíta len posledných 64KB logu namiesto celého súboru (zrýchľuje štart)."""
        try:
            if not Config.LOG_DIR.exists():
                self.log.debug(f"Log directory does not exist: {Config.LOG_DIR}")
                return
            main_log = Config.LOG_DIR / 'museum.log'
            if main_log.exists():
                # FIX: Čítame len koniec súboru pomocou seek
                with open(main_log, 'rb') as f:
                    f.seek(0, 2)  # Koniec súboru
                    size = f.tell()
                    offset = min(size, 64 * 1024)  # Posledných 64 KB
                    f.seek(size - offset)
                    content = f.read().decode('utf-8', errors='ignore')
                
                lines = content.splitlines()[-100:]  # Posledných 100 riadkov
                for line in lines:
                    if line.strip() and line.startswith('['):
                        try:
                            timestamp, rest = line.strip().split('] ', 1)
                            level, module, message = rest.split(' ', 2)
                            self._append_log_entry_to_buffer({
                                'timestamp': timestamp[1:],
                                'level': level.strip(),
                                'module': module.strip(),
                                'message': message,
                                'from_file': True
                            })
                        except ValueError:
                            continue
                loaded_file_logs = len([
                    log for log in self.get_log_history()
                    if log.get('from_file')
                ])
                self.log.debug(f"Loaded {loaded_file_logs} log entries efficiently")
            else:
                self.log.debug(f"Main log file does not exist: {main_log}")
        except Exception as e:
            self.log.error(f"Error loading existing logs: {e}")

    def load_existing_logs(self):
        """Load recent persistent logs into the in-memory dashboard buffer."""
        try:
            if not Config.LOG_DIR.exists():
                self.log.debug(f"Log directory does not exist: {Config.LOG_DIR}")
                return

            log_db = Config.LOG_DIR / 'museum_logs.db'
            if log_db.exists():
                loaded = self._load_existing_logs_from_db(log_db)
                self.log.debug(f"Loaded {loaded} log entries from SQLite history")
                return

            main_log = Config.LOG_DIR / 'museum.log'
            if main_log.exists():
                loaded = self._load_existing_logs_from_text_file(main_log)
                self.log.debug(f"Loaded {loaded} log entries from text history")
                return

            self.log.debug(f"No persistent log history found in {Config.LOG_DIR}")
        except Exception as e:
            self.log.error(f"Error loading existing logs: {e}")

    def _load_existing_logs_from_db(self, log_db: Path) -> int:
        """Load recent log records from the SQLite history database."""
        with sqlite3.connect(log_db, timeout=2.0) as conn:
            rows = conn.execute(
                """
                SELECT timestamp, level, module, message
                FROM logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (self.INITIAL_LOG_HISTORY_LIMIT,),
            ).fetchall()

        for timestamp, level, module, message in reversed(rows):
            self._append_log_entry_to_buffer({
                'timestamp': timestamp,
                'level': level,
                'module': module,
                'message': message,
                'from_db': True,
            })

        return len(rows)

    def _load_existing_logs_from_text_file(self, main_log: Path) -> int:
        """Fallback loader for older text log files."""
        with open(main_log, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            offset = min(size, 64 * 1024)
            f.seek(size - offset)
            content = f.read().decode('utf-8', errors='ignore')

        loaded = 0
        lines = content.splitlines()[-100:]
        for line in lines:
            if line.strip() and line.startswith('['):
                try:
                    timestamp, rest = line.strip().split('] ', 1)
                    level, module, message = rest.split(' ', 2)
                    self._append_log_entry_to_buffer({
                        'timestamp': timestamp[1:],
                        'level': level.strip(),
                        'module': module.strip(),
                        'message': message,
                        'from_file': True,
                    })
                    loaded += 1
                except ValueError:
                    continue

        return loaded

    def _load_stats(self):
        """Load saved statistics from file."""
        try:
            if Config.STATS_FILE.exists():
                with open(Config.STATS_FILE, 'r') as f:
                    loaded_stats = json.load(f)
                    self.stats.update({
                        'total_scenes_played': loaded_stats.get('total_scenes_played', 0),
                        'scene_play_counts': loaded_stats.get('scene_play_counts', {}),
                        'total_uptime': loaded_stats.get('total_uptime', 0),
                        'last_start_time': time.monotonic(),
                        'connected_devices': {}
                    })
                    self.log.debug(f"Loaded stats from: {Config.STATS_FILE}")
            else:
                self.log.debug(f"Stats file does not exist, using defaults: {Config.STATS_FILE}")
        except Exception as e:
            self.log.error(f"Error loading stats: {e}")

    def save_stats(self):
        """Save current statistics to file."""
        try:
            Config.STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.update_stats()
            with open(Config.STATS_FILE, 'w') as f:
                save_stats = {k: v for k, v in self.stats.items() if k != 'connected_devices'}  # Exclude transient data
                json.dump(save_stats, f, indent=2)
            self.log.debug(f"Stats saved to: {Config.STATS_FILE}")
        except Exception as e:
            self.log.error(f"Error saving stats: {e}")

    def update_stats(self, cleanup=True):
        """Update runtime statistics including uptime and connected devices."""
        now = time.monotonic()
        stats_lock = getattr(self, '_stats_lock', None)
        if stats_lock is None:
            stats_lock = threading.Lock()
            self._stats_lock = stats_lock

        with stats_lock:
            self.stats['total_uptime'] += now - self.stats['last_start_time']
            self.stats['last_start_time'] = now
        
        # Fix: Access device registry through the MQTT client structure
        if (hasattr(self.controller, 'mqtt_client') and 
            self.controller.mqtt_client and 
            hasattr(self.controller, 'mqtt_device_registry') and
            self.controller.mqtt_device_registry):
            self.stats['connected_devices'] = self.controller.mqtt_device_registry.get_connected_devices(
                cleanup=cleanup
            )
        else:
            self.stats['connected_devices'] = {}

    def update_scene_stats(self, scene_name: str):
        """Increment scene play count and save stats."""
        self.stats['total_scenes_played'] += 1
        self.stats['scene_play_counts'][scene_name] = self.stats['scene_play_counts'].get(scene_name, 0) + 1
        self.save_stats()

    def add_log_entry(self, log_entry: Dict):
        """Add a log entry to the buffer and queue websocket fanout."""
        self._append_log_entry_to_buffer(log_entry)
        self._queue_log_fanout(log_entry)

    def filter_logs(self, level_filter: str, limit: int) -> List[Dict]:
        """Filter logs by level and limit the number returned."""
        filtered_logs = self.get_log_history()
        if level_filter in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
        return filtered_logs[-limit:] if len(filtered_logs) > limit else filtered_logs
    
    def broadcast_status(self):
        """Okamžite pošle aktuálny stav (beží/nebeží) všetkým klientom."""
        self._broadcast_event('status_update', self._get_status_data())

    def broadcast_stats(self):
        """Broadcast the current stats snapshot to all connected clients."""
        self.update_stats(cleanup=False)
        self._broadcast_event('stats_update', self.stats)

    def broadcast_device_runtime_state(self, state_snapshot: dict) -> None:
        """Queue an incremental actuator state update for dashboard clients."""
        self._queue_runtime_state_fanout(state_snapshot)
