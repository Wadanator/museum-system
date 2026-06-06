#!/usr/bin/env python3
"""
mpv process lifecycle, health checks, and IPC communication.

The methods in this mixin intentionally operate on attributes owned by
VideoHandler. Keeping them here separates process concerns from playback
commands while preserving the public VideoHandler API.
"""

import json
import os
import signal
import socket
import subprocess
import time

import psutil

from utils.video.mpv_command import build_mpv_command


class VideoProcessMixin:
    """Manage the persistent mpv process and its IPC socket."""

    def _ensure_iddle_image(self) -> None:
        """
        Create a black idle image using pygame if it does not already exist.

        Avoids calling pygame.quit() to prevent interference with the
        AudioHandler's pygame.mixer which may already be running.
        """
        if not os.path.exists(self.iddle_image):
            try:
                import pygame
                if not pygame.get_init():
                    pygame.init()
                surface = pygame.Surface((640, 480))
                surface.fill((0, 0, 0))
                pygame.image.save(surface, self.iddle_image)
                self.logger.debug(f"Created black image at {self.iddle_image}")
            except Exception as e:
                self.logger.error(f"Failed to create black image: {e}")

    def _cleanup_socket(self) -> None:
        """Remove the IPC socket file if it exists."""
        if os.path.exists(self.ipc_socket):
            try:
                os.remove(self.ipc_socket)
            except PermissionError:
                self.logger.error(
                    f"Permission denied when removing socket: {self.ipc_socket}"
                )
            except Exception as e:
                self.logger.error(f"Socket cleanup failed: {e}")

    def _kill_existing_mpv_processes(self) -> None:
        """
        Kill any existing mpv processes that are using the same IPC socket.

        Prevents socket conflicts when restarting mpv.
        """
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] == 'mpv' and any(
                    self.ipc_socket in arg
                    for arg in (proc.info['cmdline'] or [])
                ):
                    proc.kill()
        except Exception as e:
            self.logger.debug(f"Error killing existing mpv processes: {e}")

    def _check_tmp_permissions(self) -> bool:
        """
        Verify that /tmp is writable for IPC socket creation.

        Returns:
            bool: True if /tmp is writable, False otherwise.
        """
        if not os.access('/tmp', os.W_OK):
            self.logger.error("No write permissions in /tmp")
            return False
        return True

    def _process_socket_ready(self) -> bool:
        """Return True only when mpv is running and its IPC socket exists."""
        return bool(
            self.process
            and self.process.poll() is None
            and os.path.exists(self.ipc_socket)
        )

    def _log_throttled(self, level: str, timestamp_attr: str,
                       message: str) -> None:
        """Log repeated mpv failures at most once per throttle interval."""
        now = time.time()
        interval = getattr(self, 'ipc_failure_log_interval', 30)
        last_log = getattr(self, timestamp_attr, 0.0)

        if now - last_log >= interval:
            getattr(self.logger, level)(message)
            setattr(self, timestamp_attr, now)
        else:
            self.logger.debug(f"{message} (suppressed)")

    def _build_mpv_command(self) -> list:
        """
        Build the mpv command line.

        Kept as a method so playback-critical defaults can be unit-tested
        without launching mpv.
        """
        return build_mpv_command(
            idle_image=self.iddle_image,
            ipc_socket=self.ipc_socket,
            vo=self.mpv_vo,
            gpu_context=self.mpv_gpu_context,
            hwdec=self._hwdec,
            hwdec_codecs=self.mpv_hwdec_codecs,
            framedrop=self.mpv_framedrop,
            extra_args=self.mpv_extra_args,
        )

    def _start_mpv(self) -> bool:
        """
        Start the mpv process with IPC socket and hardware decoding options.

        Waits up to 5 seconds for the IPC socket to appear before declaring
        failure. Cleans up any existing process and socket before starting.

        Returns:
            bool: True if mpv started and the IPC socket was created,
                False otherwise.
        """
        with self.process_lock:
            if not os.path.exists(self.iddle_image):
                self.logger.error(f"Black image missing: {self.iddle_image}")
                return False

            if not self._check_tmp_permissions():
                return False

            self._stop_current_process()
            self._cleanup_socket()
            self._kill_existing_mpv_processes()
            time.sleep(0.5)

            cmd = self._build_mpv_command()

            try:
                self.logger.debug(f"Starting mpv with command: {' '.join(cmd)}")
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid,
                )
                for _ in range(5):
                    time.sleep(1)
                    if os.path.exists(self.ipc_socket):
                        self.currently_playing = os.path.basename(
                            self.iddle_image
                        )
                        self.restart_count = 0
                        self.logger.debug(
                            "MPV process started and IPC socket created"
                        )
                        return True

                self.logger.error("IPC socket not created after retries")
                self._stop_current_process()
                return False

            except Exception as e:
                self.logger.error(f"MPV start error: {e}")
                self.process = None
                return False

    def _stop_current_process(self) -> None:
        """
        Terminate the current mpv process and clean up the IPC socket.

        Attempts a graceful SIGTERM first, then force-kills the process
        group if termination times out.
        """
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
                except Exception as e:
                    self.logger.debug(
                        f"Force kill failed with unexpected error: {e}"
                    )
        self.process = None
        self.currently_playing = None
        self._cleanup_socket()

    def _restart_mpv(self) -> bool:
        """
        Attempt to restart the mpv process within retry and cooldown limits.

        Returns:
            bool: True if restart succeeded, False if limits are exceeded.
        """
        now = time.time()
        seconds_since_restart = now - self.last_restart_time
        in_cooldown = seconds_since_restart < self.restart_cooldown

        if self.restart_count >= self.max_restart_attempts:
            if in_cooldown:
                retry_in = self.restart_cooldown - seconds_since_restart
                self._log_throttled(
                    'critical',
                    'last_restart_block_log',
                    f"Cannot restart MPV: exceeded {self.max_restart_attempts} "
                    f"attempts; suppressing retries for {retry_in:.0f}s",
                )
                return False

            self.logger.warning(
                "MPV restart cooldown elapsed; allowing new restart attempts"
            )
            self.restart_count = 0

        if in_cooldown:
            retry_in = self.restart_cooldown - seconds_since_restart
            self._log_throttled(
                'warning',
                'last_restart_block_log',
                f"MPV restart skipped; next retry allowed in {retry_in:.0f}s",
            )
            return False

        self.restart_count += 1
        self.last_restart_time = time.time()
        self._stop_current_process()
        time.sleep(2)
        return self._start_mpv()

    def _check_process_health(self) -> bool:
        """
        Check mpv process health at the configured interval.

        Returns:
            bool: True if the process is healthy or the check was skipped,
                False if restart failed.
        """
        if time.time() - self.last_health_check < self.health_check_interval:
            return True
        self.last_health_check = time.time()

        with self.process_lock:
            if (
                not self.process
                or self.process.poll() is not None
                or not os.path.exists(self.ipc_socket)
            ):
                self.logger.warning(
                    "MPV health check failed: process or socket missing"
                )
                return self._restart_mpv()

            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2)
                    sock.connect(self.ipc_socket)
                    sock.send(b'{"command": ["get_property", "pause"]}\n')
                return True
            except Exception:
                self.logger.warning(
                    "MPV health check failed: IPC not responding"
                )
                return self._restart_mpv()

    def _send_ipc_command(self, command: list,
                          get_response: bool = False) -> object:
        """
        Send a JSON command to mpv via the Unix IPC socket.

        Args:
            command: List representing the mpv IPC command and arguments.
            get_response: If True, parse and return the JSON response dict.

        Returns:
            bool or dict or None: True on success (get_response=False),
                response dict on success (get_response=True),
                False or None on failure depending on get_response.
        """
        if not self._check_process_health():
            return False if not get_response else None

        if not self._process_socket_ready():
            self._log_throttled(
                'error',
                'last_ipc_failure_log',
                f"IPC command skipped: MPV process/socket unavailable "
                f"for command: {command}",
            )
            self._restart_mpv()
            return False if not get_response else None

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                sock.connect(self.ipc_socket)

                request = (
                    json.dumps({"command": command}).encode('utf-8') + b'\n'
                )
                sock.sendall(request)

                sock.settimeout(5)
                reader = sock.makefile('r')
                response_line = reader.readline()

                if not response_line:
                    self._log_throttled(
                        'error',
                        'last_ipc_failure_log',
                        "IPC command failed: MPV closed the connection "
                        "(empty response)",
                    )
                    return False if not get_response else None

                if get_response:
                    return json.loads(response_line)
                return True

        except socket.timeout:
            self._log_throttled(
                'error',
                'last_ipc_failure_log',
                f"IPC command timed out: {command}",
            )
            self._restart_mpv()
            return False if not get_response else None

        except Exception as e:
            self._log_throttled(
                'error',
                'last_ipc_failure_log',
                f"IPC command failed: {e} for command: {command}",
            )
            self._restart_mpv()
            return False if not get_response else None
