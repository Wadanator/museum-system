#!/usr/bin/env python3
import subprocess
import os
import logging
import json
import socket

class VideoHandler:
    def __init__(self, video_dir=None, logger=None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.video_dir = video_dir or os.path.join(script_dir, "..", "videos")
        self.logger = logger or logging.getLogger(__name__)
        self.process = None
        self.currently_playing = None
        self.black_image = os.path.join(self.video_dir, "black.png")
        self.ipc_socket = "/tmp/mpv_socket"

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
                self.logger.error(f"Error creating black image: {e}")

    def _start_mpv(self):
        if not os.path.exists(self.black_image):
            self.logger.warning(f"Black image not found: {self.black_image}")
            return

        self._stop_current_process()
        cmd = [
            'mpv', '--fs', '--no-osc', '--no-osd-bar', '--vo=drm',
            '--loop-file=inf', f'--input-ipc-server={self.ipc_socket}',
            self.black_image
        ]
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.currently_playing = "black.png"
        self.logger.debug("Started mpv with black screen")

    def _stop_current_process(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            self.currently_playing = None
        if os.path.exists(self.ipc_socket):
            os.remove(self.ipc_socket)

    def _send_ipc_command(self, command):
        if not self.process or self.process.poll() is not None:
            self._start_mpv()
            if not self.process:
                return False

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.ipc_socket)
            sock.send((json.dumps({"command": command}) + "\n").encode('utf-8'))
            sock.close()
            return True
        except Exception as e:
            self.logger.error(f"Error sending IPC command {command}: {e}")
            return False

    def play_video(self, video_file):
        full_path = os.path.join(self.video_dir, video_file)
        if not os.path.exists(full_path):
            self.logger.warning(f"Video file not found: {full_path}")
            return False

        if os.path.splitext(video_file.lower())[1] not in ['.mp4']:
            self.logger.error("Supported format: .mp4")
            return False

        if self._send_ipc_command(["loadfile", full_path]):
            self.currently_playing = video_file
            self.logger.info(f"Playing video: {video_file}")
            return True
        return False

    def stop_video(self):
        if self._send_ipc_command(["loadfile", self.black_image, "replace"]):
            self.currently_playing = "black.png"
            self.logger.debug("Returned to black screen")
            return True
        return False

    def pause_video(self):
        return self._send_ipc_command(["set_property", "pause", True])

    def resume_video(self):
        return self._send_ipc_command(["set_property", "pause", False])

    def seek_video(self, seconds):
        return self._send_ipc_command(["seek", seconds, "absolute"])

    def is_playing(self):
        return (self.process and self.currently_playing != "black.png" and
                self.process.poll() is None)

    def cleanup(self):
        self._stop_current_process()
        self.logger.info("Video handler cleaned up")