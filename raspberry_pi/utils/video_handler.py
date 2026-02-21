#!/usr/bin/env python3
"""
Video handler for mpv-based video playback on Raspberry Pi.

Manages the mpv process lifecycle, IPC socket communication, health
monitoring, automatic restarts, and end-of-video detection.
"""

import subprocess
import os
import logging
import json
import socket
import time
import psutil
import signal
from threading import Lock
from utils.logging_setup import get_logger


class VideoHandler:
    """
    Controls video playback via an mpv process using a Unix IPC socket.

    Handles mpv startup, health checks, automatic restarts, and command
    dispatch. Displays a black idle image when no video is playing.
    """

    def __init__(self, video_dir=None, ipc_socket=None, iddle_image=None,
                 logger=None, health_check_interval=60, max_restart_attempts=3,
                 restart_cooldown=60):
        """
        Initialize the video handler and start the mpv process.

        Args:
            video_dir: Path to the directory containing video files.
            ipc_socket: Path to the mpv Unix IPC socket file.
            iddle_image: Filename of the idle/black image shown when not playing.
            logger: Logger instance for video events.
            health_check_interval: Seconds between mpv health checks.
            max_restart_attempts: Maximum number of mpv restart attempts.
            restart_cooldown: Seconds to wait between restart attempts.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.video_dir = video_dir or os.path.join(script_dir, "..", "videos")
        self.ipc_socket = ipc_socket or "/tmp/mpv_socket"
        self.iddle_image = os.path.join(
            self.video_dir, iddle_image or "black.png"
        )
        self.logger = logger or get_logger('video')
        self.process = None
        self.currently_playing = None
        self.process_lock = Lock()

        self.health_check_interval = health_check_interval
        self.max_restart_attempts = max_restart_attempts
        self.restart_cooldown = restart_cooldown

        self.last_health_check = time.time()
        self.restart_count = 0
        self.last_restart_time = 0

        # Video end callback
        self.end_callback = None
        self.was_playing = False

        os.makedirs(self.video_dir, exist_ok=True)
        self._ensure_iddle_image()
        self._start_mpv()
        self.logger.info("Video handler initialized")

    def _ensure_iddle_image(self):
        """
        Create a black idle image using pygame if it does not already exist.

        Used as the default display when no video is playing. Logs an error
        if image creation fails.
        """
        if not os.path.exists(self.iddle_image):
            try:
                import pygame
                pygame.init()
                surface = pygame.Surface((640, 480))
                surface.fill((0, 0, 0))
                pygame.image.save(surface, self.iddle_image)
                pygame.quit()
                self.logger.debug(f"Created black image at {self.iddle_image}")
            except Exception as e:
                self.logger.error(f"Failed to create black image: {e}")

    def _cleanup_socket(self):
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

    def _kill_existing_mpv_processes(self):
        """
        Kill any existing mpv processes that are using the same IPC socket.

        Prevents socket conflicts when restarting mpv.
        """
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == 'mpv' and any(
                self.ipc_socket in arg
                for arg in (proc.info['cmdline'] or [])
            ):
                proc.kill()

    def _check_tmp_permissions(self):
        """
        Verify that /tmp is writable for IPC socket creation.

        Returns:
            bool: True if /tmp is writable, False otherwise.
        """
        if not os.access('/tmp', os.W_OK):
            self.logger.error("No write permissions in /tmp")
            return False
        return True

    def _start_mpv(self):
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
                self.logger.error(
                    f"Black image missing: {self.iddle_image}"
                )
                return False

            if not self._check_tmp_permissions():
                return False

            self._stop_current_process()
            self._cleanup_socket()
            self._kill_existing_mpv_processes()
            time.sleep(0.5)

            cmd = [
                'mpv', '--fs', '--no-osc', '--no-osd-bar', '--vo=gpu',
                ##'--hwdec=rpi4-mmal',
                '--hwdec=rpi4-mmal',
                '--cache=no',
                '--demuxer-max-bytes=3M',
                '--profile=low-latency',
                '--loop-file=inf',
                '--idle=yes',
                '--no-input-default-bindings', '--input-conf=/dev/null', '--quiet',
                '--no-terminal',
                f'--input-ipc-server={self.ipc_socket}',
                self.iddle_image
            ]

            try:
                self.logger.debug(
                    f"Starting mpv with command: {' '.join(cmd)}"
                )
                # Use setsid to create a new process group for clean teardown
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid
                )
                # Poll for IPC socket creation for up to 5 seconds
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

    def _stop_current_process(self):
        """
        Terminate the current mpv process and clean up the IPC socket.

        Attempts a graceful SIGTERM first, then force-kills the process
        group if termination times out.
        """
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except:
                # Force kill the entire process group if graceful termination fails
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
        self.process = None
        self.currently_playing = None
        self._cleanup_socket()

    def _check_process_health(self):
        """
        Check mpv process health at the configured interval.

        Skips the check if the interval has not elapsed. Verifies the
        process is alive, the socket exists, and responds to an IPC ping.
        Triggers a restart if any check fails.

        Returns:
            bool: True if the process is healthy or the check was skipped,
                False if restart failed.
        """
        if time.time() - self.last_health_check < self.health_check_interval:
            return True
        self.last_health_check = time.time()

        with self.process_lock:
            if (not self.process or self.process.poll() is not None
                    or not os.path.exists(self.ipc_socket)):
                return self._restart_mpv()
            try:
                # Send a lightweight IPC ping to verify responsiveness
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2)
                    sock.connect(self.ipc_socket)
                    sock.send(b'{"command": ["get_property", "pause"]}\n')
                return True
            except:
                return self._restart_mpv()

    def _restart_mpv(self):
        """
        Attempt to restart the mpv process within retry and cooldown limits.

        Returns:
            bool: True if restart succeeded, False if limits are exceeded.
        """
        if (time.time() - self.last_restart_time < self.restart_cooldown
                or self.restart_count >= self.max_restart_attempts):
            self.logger.critical(
                f"Cannot restart MPV: exceeded {self.max_restart_attempts} "
                f"attempts or in cooldown"
            )
            return False
        self.restart_count += 1
        self.last_restart_time = time.time()
        self._stop_current_process()
        time.sleep(2)
        return self._start_mpv()

    def _send_ipc_command(self, command, get_response=False):
        """
        Send a JSON command to mpv via the Unix IPC socket.

        Triggers a restart if the command times out or raises an exception,
        as these conditions indicate mpv has likely frozen or crashed.

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
                    self.logger.error(
                        "IPC command failed: MPV closed the connection "
                        "(empty response)"
                    )
                    return False if not get_response else None

                if get_response:
                    response = json.loads(response_line)
                    return response
                else:
                    return True

        except socket.timeout:
            self.logger.error(f"IPC command timed out: {command}")
            # Timeout likely means mpv has frozen — restart to recover
            self._restart_mpv()
            return False if not get_response else None
        except Exception as e:
            self.logger.error(
                f"IPC command failed with exception: {e} for command: {command}"
            )
            self._restart_mpv()
            return False if not get_response else None

        except Exception as e:
            self.logger.error(f"IPC command failed: {e}")
            self._restart_mpv()
            return False if not get_response else None

    def handle_command(self, message):
        """
        Parse and execute a video command string.

        Supported commands:
        - PLAY_VIDEO:<filename> — play a video file
        - STOP_VIDEO — stop playback and show idle image
        - PAUSE — pause playback
        - RESUME — resume playback
        - SEEK:<seconds> — seek to an absolute position
        - <filename> — treat as a plain filename and attempt playback

        Args:
            message: Command string to parse and execute.

        Returns:
            bool: True if the command was handled successfully, False otherwise.
        """
        try:
            if message.startswith("PLAY_VIDEO:"):
                filename = message.split(":", 1)[1]
                return self.play_video(filename)
            elif message == "STOP_VIDEO":
                return self.stop_video()
            elif message == "PAUSE":
                return self.pause_video()
            elif message == "RESUME":
                return self.resume_video()
            elif message.startswith("SEEK:"):
                seconds = float(message.split(":", 1)[1])
                return self.seek_video(seconds)
            else:
                return self.play_video(message)
        except Exception as e:
            self.logger.error(
                f"Failed to handle video command '{message}': {e}"
            )
            return False

    def play_video(self, video_file):
        """
        Load and play a video file in mpv.

        Disables looping before loading so end-of-file detection works.
        Validates the file path and extension before sending the IPC command.

        Args:
            video_file: Filename of the video to play (relative to video_dir).

        Returns:
            bool: True if playback started successfully, False otherwise.
        """
        full_path = os.path.join(self.video_dir, video_file)
        if not os.path.exists(full_path):
            self.logger.warning(f"Video not found: {full_path}")
            return False
        if os.path.splitext(video_file.lower())[1] not in [
            '.mp4', '.avi', '.mkv', '.mov', '.webm'
        ]:
            self.logger.error(f"Unsupported format: {video_file}")
            return False

        # Disable looping so the end-of-file event fires naturally
        self._send_ipc_command(["set_property", "loop-file", "no"])

        if self._send_ipc_command(["loadfile", full_path]):
            self.currently_playing = video_file
            self.logger.info(f"Playing: {video_file}")
            return True
        return False

    def stop_video(self):
        """
        Stop video playback and return to the idle image.

        Re-enables infinite looping on the idle image before loading it.

        Returns:
            bool: True if the idle image was loaded successfully, False otherwise.
        """
        # Re-enable looping for the idle image
        self._send_ipc_command(["set_property", "loop-file", "inf"])

        if self._send_ipc_command(
                ["loadfile", self.iddle_image, "replace"]):
            self.currently_playing = os.path.basename(self.iddle_image)
            return True
        return False

    def pause_video(self):
        """
        Pause the currently playing video.

        Returns:
            bool: True if the IPC command was sent successfully.
        """
        return self._send_ipc_command(["set_property", "pause", True])

    def resume_video(self):
        """
        Resume a paused video.

        Returns:
            bool: True if the IPC command was sent successfully.
        """
        return self._send_ipc_command(["set_property", "pause", False])

    def seek_video(self, seconds):
        """
        Seek to an absolute position in the current video.

        Args:
            seconds: Target position in seconds from the start.

        Returns:
            bool: True if the IPC command was sent successfully.
        """
        return self._send_ipc_command(["seek", seconds, "absolute"])

    def is_playing(self):
        """
        Check whether a video (not the idle image) is currently playing.

        Queries the mpv idle-active property via IPC to determine playback state.

        Returns:
            bool: True if a video is actively playing, False otherwise.
        """
        if self.currently_playing == os.path.basename(self.iddle_image):
            return False

        response = self._send_ipc_command(
            ["get_property", "idle-active"], get_response=True
        )

        if response and response.get("error") == "success":
            is_idle = response.get("data", True)
            return not is_idle

        return False

    def set_end_callback(self, callback):
        """
        Register a callback to be invoked when a video finishes playing.

        Args:
            callback: Callable accepting a filename string, called when
                a video completes playback naturally.
        """
        self.end_callback = callback

    def check_if_ended(self):
        """
        Detect natural video end and invoke the end callback.

        Compares the current playing state against the previous tick.
        When a transition from playing to not-playing is detected, stops
        the video (returning to idle) and fires the end callback.

        Should be called periodically from the main loop.
        """
        is_playing_now = self.is_playing()

        if self.was_playing and not is_playing_now:
            finished_file = self.currently_playing
            self.logger.info(f"Video ended: {finished_file}")

            self.stop_video()

            if self.end_callback:
                self.end_callback(finished_file)

        self.was_playing = is_playing_now

    def cleanup(self):
        """Stop the mpv process and kill any remaining mpv instances."""
        self._stop_current_process()
        self._kill_existing_mpv_processes()
        self.logger.debug("Video handler cleaned up")