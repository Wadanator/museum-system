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

class VideoHandler:
    def __init__(self, video_dir=None, ipc_socket=None, black_image=None, logger=None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.video_dir = video_dir or os.path.join(script_dir, "..", "videos")
        self.ipc_socket = ipc_socket or "/tmp/mpv_socket"
        self.black_image = os.path.join(self.video_dir, black_image or "black.png")
        self.logger = logger or logging.getLogger(__name__)
        self.process = None
        self.currently_playing = None
        self.process_lock = Lock()
        self.last_health_check = time.time()
        self.health_check_interval = 30
        self.max_restart_attempts = 3
        self.restart_count = 0
        self.restart_cooldown = 60

        os.makedirs(self.video_dir, exist_ok=True)
        self._ensure_black_image()
        self._start_mpv()
        self.logger.info("Video handler initialized")

    def _ensure_black_image(self):
        if not os.path.exists(self.black_image):
            try:
                import pygame
                pygame.init()
                surface = pygame.Surface((1920, 1080))
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
            except Exception as e:
                self.logger.warning(f"Socket cleanup failed: {e}")

    def _kill_existing_mpv_processes(self):
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == 'mpv' and any(self.ipc_socket in arg for arg in (proc.info['cmdline'] or [])):
                proc.kill()

    def _start_mpv(self):
        with self.process_lock:
            if not os.path.exists(self.black_image):
                self.logger.error(f"Black image missing: {self.black_image}")
                return False

            self._stop_current_process()
            self._cleanup_socket()
            self._kill_existing_mpv_processes()
            time.sleep(0.5)

            cmd = [
                'mpv', '--fs', '--no-osc', '--no-osd-bar', '--vo=drm', '--loop-file=inf',
                '--no-input-default-bindings', '--input-conf=/dev/null', '--quiet',
                '--no-terminal', '--hwdec=auto', '--cache=yes', '--demuxer-max-bytes=50M',
                '--demuxer-max-back-bytes=25M', f'--input-ipc-server={self.ipc_socket}',
                self.black_image
            ]

            try:
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
                time.sleep(1)
                if self.process.poll() is not None:
                    self.logger.error("MPV process failed to start")
                    return False
                if not os.path.exists(self.ipc_socket):
                    self.logger.error("IPC socket not created")
                    self._stop_current_process()
                    return False
                self.currently_playing = os.path.basename(self.black_image)
                self.restart_count = 0
                return True
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
            return True
        self.last_health_check = time.time()

        with self.process_lock:
            if not self.process or self.process.poll() is not None or not os.path.exists(self.ipc_socket):
                return self._restart_mpv()
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect(self.ipc_socket)
                sock.send(b'{"command": ["get_property", "pause"]}\n')
                sock.close()
                return True
            except:
                return self._restart_mpv()

    def _restart_mpv(self):
        if time.time() - self.last_restart_time < self.restart_cooldown or self.restart_count >= self.max_restart_attempts:
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
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(self.ipc_socket)
            sock.send(json.dumps({"command": command}).encode('utf-8') + b"\n")
            sock.recv(1024)
            sock.close()
            return True
        except Exception as e:
            self.logger.error(f"IPC command failed: {e}")
            self._restart_mpv()
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

    def force_restart(self):
        self.restart_count = 0
        self.last_restart_time = 0
        return self._restart_mpv()

    def cleanup(self):
        self._stop_current_process()
        self._kill_existing_mpv_processes()
        self.logger.info("Video handler cleaned up")