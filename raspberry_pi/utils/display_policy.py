#!/usr/bin/env python3
"""
Display power policy helpers for scene runtime.

The runtime only needs to know whether a scene/action needs a powered display.
Actual CEC execution lives in DisplayPowerManager.
"""

import os


DISPLAY_POLICY_AUTO = "auto"
DISPLAY_POLICY_REQUIRED = "required"
DISPLAY_POLICY_NEVER = "never"
DISPLAY_POLICIES = {
    DISPLAY_POLICY_AUTO,
    DISPLAY_POLICY_REQUIRED,
    DISPLAY_POLICY_NEVER,
}

DISPLAY_SCENE_VIDEO_REASON = "scene_video"
DISPLAY_SCENE_REQUIRED_REASON = "scene_required"

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
DISPLAY_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS
VIDEO_CONTROL_COMMANDS = {
    "STOP",
    "STOP_VIDEO",
    "PAUSE",
    "RESUME",
    "TOGGLE_PAUSE",
}
IMAGE_CLEAR_COMMANDS = {"CLEAR", "DEFAULT"}


def normalize_display_policy(value, logger=None):
    """Return a valid display policy, defaulting invalid values to auto."""
    if value is None:
        return DISPLAY_POLICY_AUTO

    policy = str(value).strip().lower()
    if policy in DISPLAY_POLICIES:
        return policy

    if logger:
        logger.warning(
            "Invalid displayPolicy=%r; using %r",
            value,
            DISPLAY_POLICY_AUTO,
        )
    return DISPLAY_POLICY_AUTO


def _media_extension(filename):
    if not isinstance(filename, str):
        return ""
    return os.path.splitext(filename.strip().lower())[1]


def _has_display_extension(filename):
    return _media_extension(filename) in DISPLAY_EXTENSIONS


def _is_video_control_message(command):
    upper_command = command.upper()
    if upper_command in VIDEO_CONTROL_COMMANDS:
        return True
    return upper_command.startswith("SEEK:")


def is_video_playback_message(message):
    """
    Return True when a video action starts visible media.

    VideoHandler accepts both PLAY_VIDEO:<file> and bare filenames. It can also
    display image files through the legacy video action path, so image
    extensions are treated as display content here too.
    """
    if not isinstance(message, str):
        return False

    command = message.strip()
    if not command or _is_video_control_message(command):
        return False

    if command.upper().startswith("PLAY_VIDEO:"):
        filename = command.split(":", 1)[1].strip()
        return _has_display_extension(filename)

    return _has_display_extension(command)


def is_image_show_message(message):
    """Return True when an image action requests a visible still image."""
    if not isinstance(message, str):
        return False

    command = message.strip()
    if not command or command.upper() in IMAGE_CLEAR_COMMANDS:
        return False

    if not command.startswith("SHOW:"):
        return False

    filename = command.split(":", 1)[1].strip()
    return _media_extension(filename) in IMAGE_EXTENSIONS


def action_requests_display(action):
    """Return True when an action should wake or keep the display on."""
    if not isinstance(action, dict):
        return False

    action_type = action.get("action")
    if action_type == "video":
        return is_video_playback_message(action.get("message"))
    if action_type == "image":
        return is_image_show_message(action.get("message"))
    return False


def scene_contains_display_content(data):
    """Recursively scan scene JSON for any action that needs a display."""
    if isinstance(data, dict):
        if action_requests_display(data):
            return True
        return any(scene_contains_display_content(value) for value in data.values())

    if isinstance(data, list):
        return any(scene_contains_display_content(item) for item in data)

    return False
