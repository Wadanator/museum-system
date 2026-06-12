#!/usr/bin/env python3
"""
Public video playback commands and end-of-video detection.

This mixin keeps scene-facing behavior separate from mpv process lifecycle
details. It is composed into VideoHandler.
"""

import os
from typing import Callable, Optional


VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.webm'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}


class VideoPlaybackMixin:
    """Expose scene and dashboard playback operations."""

    def handle_command(self, message: str) -> bool:
        """
        Parse and execute a video command string.

        Supported commands:
        - PLAY_VIDEO:<filename> - play a video file or display an image
        - STOP_VIDEO - stop playback and show idle image
        - PAUSE - pause playback
        - RESUME - resume playback
        - SEEK:<seconds> - seek to an absolute position
        - <filename> - treat as a plain filename and attempt playback/display

        Args:
            message: Command string to parse and execute.

        Returns:
            bool: True if the command was handled successfully, False otherwise.
        """
        try:
            if message.startswith("PLAY_VIDEO:"):
                filename = message.split(":", 1)[1]
                return self.play_video(filename)
            if message == "STOP_VIDEO":
                return self.stop_video()
            if message == "PAUSE":
                return self.pause_video()
            if message == "RESUME":
                return self.resume_video()
            if message.startswith("SEEK:"):
                seconds = float(message.split(":", 1)[1])
                return self.seek_video(seconds)
            return self.play_video(message)
        except Exception as e:
            self.logger.error(
                f"Failed to handle video command '{message}': {e}"
            )
            return False

    def _media_extension(self, filename: str) -> str:
        """Return the lowercase media file extension."""
        return os.path.splitext(filename.lower())[1]

    def _is_image_file(self, filename: str) -> bool:
        """Return True when the filename is a supported static image."""
        return self._media_extension(filename) in IMAGE_EXTENSIONS

    def _is_video_file(self, filename: str) -> bool:
        """Return True when the filename is a supported video."""
        return self._media_extension(filename) in VIDEO_EXTENSIONS

    def play_video(self, video_file: str) -> bool:
        """
        Load and play/display a video media file in mpv.

        Static images stay on screen until replaced manually, stopped, or
        overwritten by a video. Videos preserve the existing behavior:
        looping is disabled, the idle image is appended, and videoEnd can fire.

        Disables looping before loading videos so end-of-file detection works.
        Appends the idle image to the playlist so mpv transitions to it
        instantly when the video ends.

        Args:
            video_file: Filename of the video to play (relative to video_dir).

        Returns:
            bool: True if playback started successfully, False otherwise.
        """
        full_path = os.path.join(self.video_dir, video_file)
        if not os.path.exists(full_path):
            self.logger.warning(f"Video not found: {full_path}")
            return False
        if self._is_image_file(video_file):
            return self.show_image(video_file)
        if not self._is_video_file(video_file):
            self.logger.error(f"Unsupported format: {video_file}")
            return False

        self._send_ipc_command(["set_property", "loop-file", "no"])

        if not self._send_ipc_command(["loadfile", full_path, "replace"]):
            return False

        self._send_ipc_command(["loadfile", self.iddle_image, "append"])

        self.currently_playing = video_file
        self.logger.debug(f"Playing: {video_file}")
        return True

    def show_image(self, image_file: str) -> bool:
        """
        Display a static image indefinitely.

        Images are treated as a manual/static display state, not as a playing
        video. They do not append the idle image and do not trigger videoEnd.

        Args:
            image_file: Filename of the image to display (relative to video_dir).

        Returns:
            bool: True if the image was loaded successfully, False otherwise.
        """
        full_path = os.path.join(self.video_dir, image_file)
        if not os.path.exists(full_path):
            self.logger.warning(f"Image not found: {full_path}")
            return False
        if not self._is_image_file(image_file):
            self.logger.error(f"Unsupported image format: {image_file}")
            return False

        self._send_ipc_command(["set_property", "loop-file", "inf"])

        if not self._send_ipc_command(["loadfile", full_path, "replace"]):
            return False

        self.currently_playing = image_file
        self.was_playing = False
        self.logger.debug(f"Displaying image: {image_file}")
        return True

    def stop_video(self) -> bool:
        """
        Stop video playback and return to the idle image.

        Returns:
            bool: True if the idle image was loaded successfully, False otherwise.
        """
        self._send_ipc_command(["set_property", "loop-file", "inf"])

        if self._send_ipc_command(["loadfile", self.iddle_image, "replace"]):
            self.currently_playing = os.path.basename(self.iddle_image)
            self.was_playing = False
            return True
        return False

    def pause_video(self) -> bool:
        """
        Pause the currently playing video.

        Returns:
            bool: True if the IPC command was sent successfully.
        """
        return self._send_ipc_command(["set_property", "pause", True])

    def resume_video(self) -> bool:
        """
        Resume a paused video.

        Returns:
            bool: True if the IPC command was sent successfully.
        """
        return self._send_ipc_command(["set_property", "pause", False])

    def seek_video(self, seconds: float) -> bool:
        """
        Seek to an absolute position in the current video.

        Args:
            seconds: Target position in seconds from the start.

        Returns:
            bool: True if the IPC command was sent successfully.
        """
        return self._send_ipc_command(["seek", seconds, "absolute"])

    def set_end_callback(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback to be invoked when a video finishes playing.

        Args:
            callback: Callable accepting a filename string, called when
                a video completes playback naturally.
        """
        self.end_callback = callback

    def check_if_ended(self) -> None:
        """
        Detect natural video end and invoke the end callback.

        Should be called periodically from the scene loop.
        """
        tracked_file = self.currently_playing
        is_playing_now = self.is_playing()

        if is_playing_now is None:
            if (
                not tracked_file
                or tracked_file == os.path.basename(self.iddle_image)
                or self.currently_playing != tracked_file
            ):
                self.was_playing = False
            return

        if self.was_playing and not is_playing_now:
            if (
                not tracked_file
                or tracked_file == os.path.basename(self.iddle_image)
            ):
                self.was_playing = False
                return

            finished_file = tracked_file
            self.logger.debug(f"Video ended: {finished_file}")

            self.stop_video()

            if self.end_callback and finished_file:
                self.end_callback(finished_file)

        self.was_playing = is_playing_now

    def is_playing(self) -> Optional[bool]:
        """
        Return True if a video is playing, False if mpv confirms idle/end,
        or None when IPC state is unknown.
        """
        if (
            self.currently_playing == os.path.basename(self.iddle_image)
            or (
                self.currently_playing
                and self._is_image_file(self.currently_playing)
            )
        ):
            return False

        response = self._send_ipc_command(
            ["get_property", "path"],
            get_response=True,
        )

        if response and response.get("error") == "success":
            current_path = response.get("data")
            if not current_path:
                return None
            if os.path.basename(current_path) == os.path.basename(
                self.iddle_image
            ):
                return False
            return True

        return None

    def cleanup(self) -> None:
        """Stop the mpv process and kill any remaining mpv instances."""
        self._stop_current_process()
        self._kill_existing_mpv_processes()
        self.logger.debug("Video handler cleaned up")
