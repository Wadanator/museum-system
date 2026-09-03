#!/usr/bin/env python3
"""
Display power manager for HDMI-CEC/script based screens.

Scene runtime calls request_on/release with logical reasons. This class
serializes the slow external scripts on a worker thread so scene playback never
waits for CEC.
"""

import queue
import subprocess
import threading
import time
from pathlib import Path

from utils.logging_setup import get_logger


COMMAND_ON = "on"
COMMAND_STANDBY = "standby"


class DisplayPowerBackend:
    """Small backend interface for display power commands."""

    name = "base"

    def power_on(self):
        raise NotImplementedError

    def standby(self):
        raise NotImplementedError


class NoopDisplayBackend(DisplayPowerBackend):
    """Backend used when display power control is disabled or simulated."""

    name = "noop"

    def __init__(self, logger=None):
        self.logger = logger or get_logger("display")

    def power_on(self):
        self.logger.debug("Display power ON skipped by noop backend")
        return True

    def standby(self):
        self.logger.debug("Display power STANDBY skipped by noop backend")
        return True


class ScriptDisplayBackend(DisplayPowerBackend):
    """Run existing shell scripts for display ON/STANDBY commands."""

    name = "script"

    def __init__(
        self,
        on_script,
        off_script,
        *,
        timeout_seconds=5.0,
        cec_target="0",
        logger=None,
    ):
        self.on_script = Path(on_script) if on_script else None
        self.off_script = Path(off_script) if off_script else None
        self.timeout_seconds = max(0.1, float(timeout_seconds))
        self.cec_target = str(cec_target).strip()
        self.logger = logger or get_logger("display")

    def power_on(self):
        return self._run_script(self.on_script, "ON")

    def standby(self):
        return self._run_script(self.off_script, "STANDBY")

    def _build_command(self, script_path):
        if script_path.suffix.lower() == ".sh":
            command = ["bash", str(script_path)]
        else:
            command = [str(script_path)]

        if self.cec_target:
            command.append(self.cec_target)
        return command

    def _run_script(self, script_path, label):
        if not script_path:
            self.logger.error("Display %s script is not configured", label)
            return False

        if not script_path.exists():
            self.logger.error("Display %s script not found: %s", label, script_path)
            return False

        command = self._build_command(script_path)
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.logger.error(
                "Display %s script timed out after %.1fs: %s",
                label,
                self.timeout_seconds,
                script_path,
            )
            return False
        except Exception as exc:
            self.logger.error(
                "Display %s script failed to start: %s (%s)",
                label,
                script_path,
                exc,
            )
            return False

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.returncode == 0:
            if stdout:
                self.logger.debug("Display %s script output: %s", label, stdout)
            return True

        self.logger.error(
            "Display %s script exited with %s: %s%s%s",
            label,
            result.returncode,
            script_path,
            f" | stdout={stdout}" if stdout else "",
            f" | stderr={stderr}" if stderr else "",
        )
        return False


class DisplayPowerManager:
    """Reference-counted display power control for scenes and operators."""

    def __init__(
        self,
        *,
        enabled=False,
        backend=None,
        idle_timeout_seconds=300.0,
        min_seconds_between_power_commands=15.0,
        standby_on_service_stop=False,
        startup_power_state="unchanged",
        async_commands=True,
        logger=None,
    ):
        self.enabled = bool(enabled)
        self.backend = backend or NoopDisplayBackend(logger=logger)
        self.idle_timeout_seconds = max(0.0, float(idle_timeout_seconds))
        self.min_seconds_between_power_commands = max(
            0.0,
            float(min_seconds_between_power_commands),
        )
        self.standby_on_service_stop = bool(standby_on_service_stop)
        self.startup_power_state = startup_power_state
        self.async_commands = bool(async_commands)
        self.logger = logger or get_logger("display")

        self._lock = threading.Lock()
        self._active_reasons = set()
        self._standby_timer = None
        self._pending_standby_at = None
        self._requested_state = "unknown"
        self._last_command = None
        self._last_command_at = 0.0
        self._last_result = None
        self._last_error = None

        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread = None

        if self.async_commands:
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="display-power-worker",
                daemon=True,
            )
            self._worker_thread.start()

        self._apply_startup_power_state()

    @classmethod
    def from_config(cls, config, logger=None):
        """Build a display power manager from the flat application config."""
        log = logger or get_logger("display")
        backend_name = str(config.get("display_backend", "noop")).strip().lower()

        if backend_name in {"script", "cec"}:
            backend = ScriptDisplayBackend(
                config.get("display_on_script"),
                config.get("display_off_script"),
                timeout_seconds=config.get("display_command_timeout_seconds", 5.0),
                cec_target=config.get("display_cec_target", "0"),
                logger=log,
            )
        else:
            backend = NoopDisplayBackend(logger=log)

        return cls(
            enabled=config.get("display_enabled", False),
            backend=backend,
            idle_timeout_seconds=config.get("display_idle_timeout_seconds", 300.0),
            min_seconds_between_power_commands=config.get(
                "display_min_seconds_between_power_commands",
                15.0,
            ),
            standby_on_service_stop=config.get(
                "display_standby_on_service_stop",
                False,
            ),
            startup_power_state=config.get(
                "display_startup_power_state",
                "unchanged",
            ),
            logger=log,
        )

    def request_on(self, reason):
        """Keep the display powered while the given reason remains active."""
        if not self.enabled:
            return False

        reason = self._normalize_reason(reason)
        should_send = False
        with self._lock:
            had_reasons = bool(self._active_reasons)
            self._active_reasons.add(reason)
            self._cancel_standby_timer_locked()
            if not had_reasons or self._requested_state != COMMAND_ON:
                should_send = True

        if should_send:
            self._enqueue_command(COMMAND_ON, reason)
        return True

    def release(self, reason):
        """Release a display-on reason and schedule standby if none remain."""
        if not self.enabled:
            return False

        reason = self._normalize_reason(reason)
        with self._lock:
            self._active_reasons.discard(reason)
            no_active_reasons = not self._active_reasons

        if no_active_reasons:
            self._schedule_standby()
        return True

    def force_on(self, reason="manual"):
        """Immediately request display ON for a manual or external command."""
        if not self.enabled:
            return False

        reason = self._normalize_reason(reason)
        with self._lock:
            self._active_reasons.add(reason)
            self._cancel_standby_timer_locked()

        self._enqueue_command(COMMAND_ON, reason, force=True)
        return True

    def force_standby(self, reason="manual"):
        """Clear all reasons and immediately request display STANDBY."""
        if not self.enabled:
            return False

        reason = self._normalize_reason(reason)
        with self._lock:
            self._active_reasons.clear()
            self._cancel_standby_timer_locked()

        self._enqueue_command(COMMAND_STANDBY, reason, force=True)
        return True

    def get_status(self):
        """Return a dashboard/API friendly status snapshot."""
        with self._lock:
            return {
                "enabled": self.enabled,
                "backend": getattr(self.backend, "name", type(self.backend).__name__),
                "active_reasons": sorted(self._active_reasons),
                "requested_state": self._requested_state,
                "pending_standby_at": self._pending_standby_at,
                "last_command": self._last_command,
                "last_result": self._last_result,
                "last_error": self._last_error,
            }

    def cleanup(self):
        """Stop worker resources and optionally put the display in standby."""
        with self._lock:
            self._active_reasons.clear()
            self._cancel_standby_timer_locked()

        if self.enabled and self.standby_on_service_stop:
            self._enqueue_command(COMMAND_STANDBY, "service_cleanup", force=True, wait=True)

        if self.async_commands and self._worker_thread:
            self._stop_event.set()
            self._queue.put(None)
            self._worker_thread.join(timeout=2.0)
            if self._worker_thread.is_alive():
                self.logger.warning("Display power worker did not stop before timeout")

    def _apply_startup_power_state(self):
        if not self.enabled:
            return
        if self.startup_power_state == COMMAND_ON:
            self._enqueue_command(COMMAND_ON, "startup", force=True)
        elif self.startup_power_state == COMMAND_STANDBY:
            self._enqueue_command(COMMAND_STANDBY, "startup", force=True)

    def _normalize_reason(self, reason):
        text = str(reason or "").strip()
        return text or "unknown"

    def _schedule_standby(self):
        if self.idle_timeout_seconds <= 0:
            self._enqueue_command(COMMAND_STANDBY, "idle_timeout")
            return

        with self._lock:
            self._cancel_standby_timer_locked()
            standby_at = time.time() + self.idle_timeout_seconds
            self._pending_standby_at = standby_at
            timer = threading.Timer(self.idle_timeout_seconds, self._standby_if_idle)
            timer.daemon = True
            self._standby_timer = timer
            timer.start()

    def _standby_if_idle(self):
        with self._lock:
            self._standby_timer = None
            self._pending_standby_at = None
            if self._active_reasons:
                return

        self._enqueue_command(COMMAND_STANDBY, "idle_timeout")

    def _cancel_standby_timer_locked(self):
        if self._standby_timer:
            self._standby_timer.cancel()
            self._standby_timer = None
        self._pending_standby_at = None

    def _enqueue_command(self, command, reason, *, force=False, wait=False):
        if command not in {COMMAND_ON, COMMAND_STANDBY}:
            return False

        now = time.monotonic()
        with self._lock:
            if (
                not force
                and self._last_command == command
                and now - self._last_command_at < self.min_seconds_between_power_commands
            ):
                self._requested_state = command
                self.logger.debug(
                    "Display %s suppressed by debounce for reason %s",
                    command,
                    reason,
                )
                return True
            self._requested_state = command

        if not self.async_commands:
            return self._execute_command(command, reason)

        done_event = threading.Event() if wait else None
        self._queue.put((command, reason, force, done_event))
        if done_event:
            done_event.wait(timeout=10.0)
        return True

    def _worker_loop(self):
        while not self._stop_event.is_set():
            item = self._queue.get()
            try:
                if item is None:
                    return
                command, reason, _force, done_event = item
                self._execute_command(command, reason)
                if done_event:
                    done_event.set()
            finally:
                self._queue.task_done()

    def _execute_command(self, command, reason):
        try:
            if command == COMMAND_ON:
                ok = bool(self.backend.power_on())
            else:
                ok = bool(self.backend.standby())
            error = None
        except Exception as exc:
            ok = False
            error = str(exc)
            self.logger.error("Display %s command failed: %s", command, exc)

        with self._lock:
            self._last_command = command
            self._last_command_at = time.monotonic()
            self._last_result = ok
            self._last_error = error
            self._requested_state = command

        if ok:
            self.logger.info("Display %s requested (%s)", command, reason)
        elif not error:
            self.logger.error("Display %s command returned failure (%s)", command, reason)
        return ok
