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
    def __init__(self, video_dir=None, ipc_socket=None, iddle_image=None, logger=None, 
                 health_check_interval=60, max_restart_attempts=3, restart_cooldown=60):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.video_dir = video_dir or os.path.join(script_dir, "..", "videos")
        self.ipc_socket = ipc_socket or "/tmp/mpv_socket"
        self.iddle_image = os.path.join(self.video_dir, iddle_image or "black.png")
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
        if not os.path.exists(self.iddle_image):
            try:
                import pygame
                pygame.init()
                surface = pygame.Surface((640, 480))
                surface.fill((0, 0, 0))
                pygame.image.save(surface, self.iddle_image)
                pygame.quit()
                self.logger.info(f"Created black image at {self.iddle_image}")
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
            if not os.path.exists(self.iddle_image):
                self.logger.error(f"Black image missing: {self.iddle_image}")
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
                self.logger.debug(f"Starting mpv with command: {' '.join(cmd)}")
                self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
                for _ in range(5):
                    time.sleep(1)
                    if os.path.exists(self.ipc_socket):
                        self.currently_playing = os.path.basename(self.iddle_image)
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

    def _send_ipc_command(self, command, get_response=False):
        if not self._check_process_health():
            return False if not get_response else None
        
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                sock.connect(self.ipc_socket)
                
                request = json.dumps({"command": command}).encode('utf-8') + b'\n'
                sock.sendall(request)

                sock.settimeout(5)
                reader = sock.makefile('r')
                response_line = reader.readline()

                if not response_line:
                    self.logger.error("IPC command failed: MPV closed the connection (empty response)")
                    return False if not get_response else None
                
                if get_response:
                    response = json.loads(response_line)
                    return response
                else:
                    return True

        except socket.timeout:
            self.logger.error(f"IPC command timed out: {command}")
            # Pri timeoute je lepšie reštartovať mpv, lebo pravdepodobne zamrzol
            self._restart_mpv()
            return False if not get_response else None
        except Exception as e:
            self.logger.error(f"IPC command failed with exception: {e} for command: {command}")
            self._restart_mpv()
            return False if not get_response else None  

        except Exception as e:
            self.logger.error(f"IPC command failed: {e}")
            self._restart_mpv()
            return False if not get_response else None

    def handle_command(self, message):
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
        
        self._send_ipc_command(["set_property", "loop-file", "no"])
        
        if self._send_ipc_command(["loadfile", full_path]):
            self.currently_playing = video_file
            self.logger.info(f"Playing: {video_file}")
            return True
        return False

    def stop_video(self):
        self._send_ipc_command(["set_property", "loop-file", "inf"])
        
        if self._send_ipc_command(["loadfile", self.iddle_image, "replace"]):
            self.currently_playing = os.path.basename(self.iddle_image)
            return True
        return False

    def pause_video(self):
        return self._send_ipc_command(["set_property", "pause", True])

    def resume_video(self):
        return self._send_ipc_command(["set_property", "pause", False])

    def seek_video(self, seconds):
        return self._send_ipc_command(["seek", seconds, "absolute"])

    def is_playing(self):
        if self.currently_playing == os.path.basename(self.iddle_image):
            return False

        response = self._send_ipc_command(["get_property", "idle-active"], get_response=True)
        
        if response and response.get("error") == "success":
            is_idle = response.get("data", True)
            return not is_idle
        
        return False

    def set_end_callback(self, callback):
        self.end_callback = callback
    
    def check_if_ended(self):
        is_playing_now = self.is_playing()
        
        if self.was_playing and not is_playing_now:
            finished_file = self.currently_playing
            self.logger.info(f"Video ended: {finished_file}")
            
            self.stop_video()
            
            if self.end_callback:
                self.end_callback(finished_file)
        
        self.was_playing = is_playing_now

    def cleanup(self):
        self._stop_current_process()
        self._kill_existing_mpv_processes()
        self.logger.info("Video handler cleaned up")