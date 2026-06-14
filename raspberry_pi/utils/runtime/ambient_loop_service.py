"""Ambient startup and restart policy helper."""

import os
import threading
import time
from datetime import datetime, timedelta, timezone


_VALID_OUTCOMES = {
    'never_started',
    'normal_end',
    'missing_scene',
    'load_failure',
    'parser_unavailable',
    'start_failure',
    'error',
    'explicit_stop',
    'shutdown',
}


def _utc_iso(dt: datetime) -> str:
    return (
        dt.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace('+00:00', 'Z')
    )


class AmbientLoopService:
    """Own ambient-mode decisions without creating scene threads itself."""

    def __init__(self, owner, logger) -> None:
        self.owner = owner
        self.log = logger
        self._lock = threading.Lock()
        self._wait_event = threading.Event()
        self._shutdown_requested = False
        self._suspended = False
        self._boot_start_attempted = False
        self._mqtt_restore_start_attempted = False
        self._next_restart_at = None
        self._last_outcome = 'never_started'

    def _config(self) -> dict:
        return getattr(self.owner, 'config', {}) or {}

    def _is_shutdown_requested(self) -> bool:
        return bool(
            self._shutdown_requested
            or getattr(self.owner, 'shutdown_requested', False)
        )

    def _is_suspended(self) -> bool:
        with self._lock:
            return self._suspended

    def startup_mode(self) -> str:
        return str(self._config().get('startup_mode', 'classic')).lower()

    def is_enabled(self) -> bool:
        return self.startup_mode() == 'ambient'

    def scene_name(self) -> str:
        config = self._config()
        return (
            config.get('ambient_scene')
            or config.get('json_file_name')
            or getattr(self.owner, 'json_file_name', '')
        )

    def get_status(self) -> dict:
        config = self._config()
        with self._lock:
            return {
                'enabled': self.is_enabled(),
                'scene': self.scene_name(),
                'suspended': self._suspended,
                'start_policy': config.get(
                    'ambient_start_policy',
                    'after_initial_connection_attempt',
                ),
                'cycle_cleanup': config.get('ambient_cycle_cleanup', 'scene_only'),
                'next_restart_at': self._next_restart_at,
                'last_outcome': self._last_outcome,
            }

    def should_ignore_default_start(self) -> bool:
        return bool(
            self.is_enabled()
            and self._config().get('ambient_ignore_default_start', True)
        )

    def should_allow_named_scene_start(self) -> bool:
        if not self.is_enabled():
            return True
        return bool(self._config().get('ambient_allow_named_scene_start', True))

    def start_after_boot_if_needed(self) -> bool:
        """Start ambient after boot if policy allows it and only once."""
        if not self.is_enabled():
            return False
        if self._config().get(
            'ambient_start_policy',
            'after_initial_connection_attempt',
        ) != 'after_initial_connection_attempt':
            return False

        with self._lock:
            if (
                self._boot_start_attempted
                or self._suspended
                or self._is_shutdown_requested()
            ):
                return False
            self._boot_start_attempted = True

        return self._start_ambient_scene('Ambient mode: auto-start on boot')

    def start_after_mqtt_restore_if_needed(self) -> bool:
        """Start ambient on MQTT restore for wait_for_mqtt policy, only once."""
        if not self.is_enabled():
            return False
        if self._config().get(
            'ambient_start_policy',
            'after_initial_connection_attempt',
        ) != 'wait_for_mqtt':
            return False

        with self._lock:
            if (
                self._mqtt_restore_start_attempted
                or self._suspended
                or self._is_shutdown_requested()
            ):
                return False
            self._mqtt_restore_start_attempted = True

        return self._start_ambient_scene('Ambient mode: MQTT restored auto-start')

    def should_restart_after_scene(self, scene_filename: str, *, normal_end: bool) -> bool:
        if not normal_end:
            return False
        if not self.is_enabled() or self._is_shutdown_requested() or self._is_suspended():
            return False

        finished = os.path.basename(scene_filename or '')
        ambient = os.path.basename(self.scene_name() or '')
        return bool(finished and ambient and finished == ambient)

    def restart_delay_seconds(self, *, normal_end: bool) -> float:
        key = (
            'ambient_restart_delay_seconds'
            if normal_end
            else 'ambient_error_retry_seconds'
        )
        return float(self._config().get(key, 0.0))

    def wait_for_restart_delay(self, delay_seconds: float) -> bool:
        """Wait for a restart delay and wake quickly on suspend/shutdown."""
        delay_seconds = max(0.0, float(delay_seconds))

        if self._is_shutdown_requested() or self._is_suspended():
            return False
        if delay_seconds == 0:
            return True

        deadline = time.monotonic() + delay_seconds
        next_restart = _utc_iso(
            datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        )

        with self._lock:
            if self._shutdown_requested or self._suspended:
                return False
            self._next_restart_at = next_restart
            self._wait_event.clear()

        try:
            while True:
                if self._is_shutdown_requested() or self._is_suspended():
                    return False

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return True

                self._wait_event.wait(min(0.2, remaining))
        finally:
            with self._lock:
                self._next_restart_at = None

    def suspend_by_operator_stop(self) -> None:
        with self._lock:
            self._suspended = True
            self._last_outcome = 'explicit_stop'
            self._next_restart_at = None
            self._wait_event.set()

    def resume(self) -> None:
        with self._lock:
            self._suspended = False
            if not self._shutdown_requested:
                self._wait_event.clear()

    def request_shutdown(self) -> None:
        with self._lock:
            self._shutdown_requested = True
            self._last_outcome = 'shutdown'
            self._next_restart_at = None
            self._wait_event.set()

    def record_outcome(self, outcome: str) -> None:
        if outcome not in _VALID_OUTCOMES:
            self.log.warning("Unknown ambient outcome %r; using 'error'", outcome)
            outcome = 'error'
        with self._lock:
            self._last_outcome = outcome

    def _start_ambient_scene(self, log_message: str) -> bool:
        if self._is_shutdown_requested() or self._is_suspended():
            return False

        starter = getattr(self.owner, '_initiate_scene_start', None)
        if not callable(starter):
            self.log.error("Ambient start requested but scene starter is unavailable")
            self.record_outcome('start_failure')
            return False

        started = bool(starter(self.scene_name(), log_message))
        if not started:
            self.record_outcome('start_failure')
        return started
