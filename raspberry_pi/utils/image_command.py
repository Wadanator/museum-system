#!/usr/bin/env python3
"""
Parsing and validation for dedicated scene image commands.

The image action is intentionally strict. Scene JSON should name a file inside
the currently configured room video directory; room and directory selection are
resolved from config, not embedded in the scene file.
"""

import os
from dataclasses import dataclass
from typing import Optional


IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
IMAGE_CLEAR_COMMANDS = {'CLEAR', 'DEFAULT'}


@dataclass(frozen=True)
class ImageCommand:
    """Parsed image command result."""

    valid: bool
    kind: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None


def _is_safe_filename(filename: str) -> bool:
    """Return True when filename is a simple basename, not a path."""
    if not filename:
        return False
    if '\x00' in filename:
        return False
    if '/' in filename or '\\' in filename:
        return False
    if filename in {'.', '..'}:
        return False
    return os.path.basename(filename) == filename


def parse_image_command(message) -> ImageCommand:
    """
    Parse a scene image action message.

    Accepted commands:
    - SHOW:<filename> where filename is a safe image basename
    - CLEAR or DEFAULT to return to the configured idle image
    """
    if not isinstance(message, str):
        return ImageCommand(
            valid=False,
            error="Image action message must be a string",
        )

    command = message.strip()
    upper_command = command.upper()

    if upper_command in IMAGE_CLEAR_COMMANDS:
        return ImageCommand(valid=True, kind="clear")

    if not command.startswith("SHOW:"):
        return ImageCommand(
            valid=False,
            error="Image action message must be SHOW:<filename> or CLEAR",
        )

    filename = command.split(":", 1)[1].strip()
    if not filename:
        return ImageCommand(
            valid=False,
            error="SHOW image command requires a filename",
        )

    if not _is_safe_filename(filename):
        return ImageCommand(
            valid=False,
            error="Image filename must be a basename, not a path",
        )

    extension = os.path.splitext(filename.lower())[1]
    if extension not in IMAGE_EXTENSIONS:
        return ImageCommand(
            valid=False,
            error=(
                "Image action supports only .png, .jpg, and .jpeg files"
            ),
        )

    return ImageCommand(valid=True, kind="show", filename=filename)
