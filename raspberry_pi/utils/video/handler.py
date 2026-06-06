#!/usr/bin/env python3
"""
Video handler for mpv-based video playback on Raspberry Pi.

The public VideoHandler class composes smaller mixins so process management,
hardware decoding selection, and playback commands stay easier to maintain.
"""

import logging
import os
import shlex
import time
from threading import RLock
from typing import List, Optional

from utils.logging_setup import get_logger
from utils.video.hardware import VideoHardwareMixin
from utils.video.playback import VideoPlaybackMixin
from utils.video.process import VideoProcessMixin


class VideoHandler(
    VideoPlaybackMixin,
    VideoProcessMixin,
    VideoHardwareMixin,
):
    """
    Controls video playback via an mpv process using a Unix IPC socket.

    Handles mpv startup, health checks, automatic restarts, command dispatch,
    and natural end-of-video detection.
    """

    def __init__(self, video_dir: Optional[str] = None,
                 ipc_socket: Optional[str] = None,
                 iddle_image: Optional[str] = None,
                 logger: Optional[logging.Logger] = None,
                 health_check_interval: int = 60,
                 max_restart_attempts: int = 3,
                 restart_cooldown: int = 60,
                 mpv_hwdec: Optional[str] = None,
                 mpv_vo: Optional[str] = None,
                 mpv_gpu_context: Optional[str] = None,
                 mpv_hwdec_codecs: Optional[str] = None,
                 mpv_framedrop: Optional[str] = None,
                 mpv_extra_args: Optional[List[str]] = None) -> None:
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
            mpv_hwdec: mpv --hwdec value. Use "detect" for OS-based fallback.
            mpv_vo: mpv --vo value.
            mpv_gpu_context: mpv --gpu-context value, useful for DRM/KMS output.
            mpv_hwdec_codecs: mpv --hwdec-codecs value.
            mpv_framedrop: mpv --framedrop value.
            mpv_extra_args: Additional raw mpv arguments.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.video_dir = video_dir or os.path.join(script_dir, "..", "..", "videos")
        self.ipc_socket = ipc_socket or "/tmp/mpv_socket"
        self.iddle_image = os.path.join(
            self.video_dir,
            iddle_image or "black.png",
        )
        self.logger = logger or get_logger('video')
        self.process = None
        self.currently_playing: Optional[str] = None

        # RLock prevents deadlock when health checks trigger nested restarts.
        self.process_lock = RLock()

        self.health_check_interval = health_check_interval
        self.max_restart_attempts = max_restart_attempts
        self.restart_cooldown = restart_cooldown

        self.last_health_check = time.time()
        self.restart_count = 0
        self.last_restart_time = 0
        self.ipc_failure_log_interval = min(60, max(10, restart_cooldown // 2))
        self.last_ipc_failure_log = 0.0
        self.last_restart_block_log = 0.0

        self.end_callback = None
        self.was_playing = False

        self.mpv_vo = (mpv_vo or "gpu").strip()
        self.mpv_gpu_context = (mpv_gpu_context or "drm").strip()
        self.mpv_hwdec_codecs = (mpv_hwdec_codecs or "h264,hevc").strip()
        self.mpv_framedrop = (mpv_framedrop or "vo").strip()
        if isinstance(mpv_extra_args, str):
            self.mpv_extra_args = shlex.split(mpv_extra_args)
        else:
            self.mpv_extra_args = mpv_extra_args or []

        # Raspberry Pi OS and mpv builds differ, so keep hwdec configurable.
        self._hwdec: str = self._select_hwdec(mpv_hwdec)

        os.makedirs(self.video_dir, exist_ok=True)
        self._ensure_iddle_image()
        self._start_mpv()
        self.logger.debug("Video handler initialized")
