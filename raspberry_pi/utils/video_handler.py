#!/usr/bin/env python3
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
    def __init__(self, video_dir=None, ipc_socket=None, black_image=None, logger=None, 
                 health_check_interval=60, max_restart_attempts=3, restart_cooldown=60):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.video_dir = video_dir or os.path.join(script_dir, "..", "videos")
        self.ipc_socket = ipc_socket or "/tmp/mpv_socket"
        self.black_image = os.path.join(self.video_dir, black_image or "black.png")
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

        os.makedirs(self.video_dir, exist_ok=True)
        self._ensure_black_image()
        self._start_mpv()
        self.logger.info("Video handler initialized")

    def _ensure_black_image(self):
        if not os.path.exists(self.black_image):
            try:
                import pygame
                pygame.init()
                surface = pygame.Surface((640, 480))  # Smaller resolution
                surface.fill((0, 0, 0))
                pygame.image.save(surface, self.black_image)
                pygame.quit()
                self.logger.info(f"Created black image at {self.black_image}")
            except Exception as e:
                self.logger.error(f"Failed to create black image: {e}")

    def _cleanup_socket(self):
        if os.path.exists(self.ipc_socket):
            try:
                os.remove(self.ipc_socket)
            except PermissionError:
                self.logger.error(f"Permission denied when removing socket: {self.ipc_socket}")
            except Exception as e:
                self.logger.error(f"Socket cleanup failed: {e}")

    def _kill_existing_mpv_processes(self):
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == 'mpv' and any(self.ipc_socket in arg for arg in (proc.info['cmdline'] or [])):
                proc.kill()

    def _check_tmp_permissions(self):
        if not os.access('/tmp', os.W_OK):
            self.logger.error("No write permissions in /tmp")
            return False
        return True

    def _start_mpv(self):
        with self.process_lock:
            if not os.path.exists(self.black_image):
                self.logger.error(f"Black image missing: {self.black_image}")
                return False

            if not self._check_tmp_permissions():
                return False

            self._stop_current_process()
            self._cleanup_socket()
            self._kill_existing_mpv_processes()
            time.sleep(0.5)

            # Optimized MPV command for Raspberry Pi performance
            cmd = [
                'mpv', '--fs', '--no-osc', '--no-osd-bar', '--vo=gpu',
                '--hwdec=rpi4-mmal',  # Use RPi4 hardware acceleration (change to v4l2m2m if needed)
                '--cache=no',  # Disable cache to save RAM
                '--demuxer-max-bytes=3M',  # Small buffer for low memory usage
                '--profile=low-latency',  # Optimize for responsive playback
                '--loop-file=inf',
                '--no-input-default-bindings', '--input-conf=/dev/null', '--quiet',
                '--no-terminal', 
                f'--input-ipc-server={self.ipc_socket}',
                self.black_image
            ]

            try:
                self.logger.debug(f"Starting mpv with command: {' '.join(cmd)}")
                self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
                for _ in range(5):
                    time.sleep(1)
                    if os.path.exists(self.ipc_socket):
                        self.currently_playing = os.path.basename(self.black_image)
                        self.restart_count = 0
                        self.logger.info("MPV process started and IPC socket created")
                        return True
                self.logger.error("IPC socket not created after retries")
                self._stop_current_process()
                return False
            except Exception as e:
                self.logger.error(f"MPV start error: {e}")
                self.process = None
                return False

    def _stop_current_process(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
        self.process = None
        self.currently_playing = None
        self._cleanup_socket()

    def _check_process_health(self):
        if time.time() - self.last_health_check < self.health_check_interval:
            self.logger.debug("MPV process and IPC socket healthy")
            return True
        self.last_health_check = time.time()

        with self.process_lock:
            if not self.process or self.process.poll() is not None or not os.path.exists(self.ipc_socket):
                return self._restart_mpv()
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2)
                    sock.connect(self.ipc_socket)
                    sock.send(b'{"command": ["get_property", "pause"]}\n')
                return True
            except:
                return self._restart_mpv()

    def _restart_mpv(self):
        if time.time() - self.last_restart_time < self.restart_cooldown or self.restart_count >= self.max_restart_attempts:
            self.logger.critical(f"Cannot restart MPV: exceeded {self.max_restart_attempts} attempts or in cooldown")
            return False
        self.restart_count += 1
        self.last_restart_time = time.time()
        self._stop_current_process()
        time.sleep(2)
        return self._start_mpv()

    def _send_ipc_command(self, command):
        if not self._check_process_health():
            return False
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect(self.ipc_socket)
                sock.send(json.dumps({"command": command}).encode('utf-8') + b"\n")
                sock.recv(1024)
            return True
        except Exception as e:
            self.logger.error(f"IPC command failed: {e}")
            self._restart_mpv()
            return False

    def handle_command(self, message):
        """Handle video command messages from scene parser."""
        try:
            if message.startswith("PLAY_VIDEO:"):
                filename = message.split(":", 1)[1]  # Use split(1) to handle colons in filenames
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
                # Handle direct filename
                return self.play_video(message)
                
        except Exception as e:
            self.logger.error(f"Failed to handle video command '{message}': {e}")
            return False

    def play_video(self, video_file):
        full_path = os.path.join(self.video_dir, video_file)
        if not os.path.exists(full_path):
            self.logger.warning(f"Video not found: {full_path}")
            return False
        if os.path.splitext(video_file.lower())[1] not in ['.mp4', '.avi', '.mkv', '.mov', '.webm']:
            self.logger.error(f"Unsupported format: {video_file}")
            return False
        if self._send_ipc_command(["loadfile", full_path]):
            self.currently_playing = video_file
            self.logger.info(f"Playing: {video_file}")
            return True
        return False

    def stop_video(self):
        if self._send_ipc_command(["loadfile", self.black_image, "replace"]):
            self.currently_playing = os.path.basename(self.black_image)
            return True
        return False

    def pause_video(self):
        return self._send_ipc_command(["set_property", "pause", True])

    def resume_video(self):
        return self._send_ipc_command(["set_property", "pause", False])

    def seek_video(self, seconds):
        return self._send_ipc_command(["seek", seconds, "absolute"])

    def is_playing(self):
        return self.process and self.currently_playing != os.path.basename(self.black_image) and self.process.poll() is None

    def cleanup(self):
        self._stop_current_process()
        self._kill_existing_mpv_processes()
        self.logger.info("Video handler cleaned up")