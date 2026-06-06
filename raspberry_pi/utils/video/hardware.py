#!/usr/bin/env python3
"""
Hardware decoding helpers for mpv video playback.

Raspberry Pi OS and mpv builds differ enough that the selected hardware
decoder must stay configurable. These helpers keep the fallback detection
isolated from playback and process management.
"""

import subprocess
from typing import Optional


class VideoHardwareMixin:
    """Resolve the mpv hardware decoding backend."""

    def _select_hwdec(self, configured_hwdec: Optional[str]) -> str:
        """
        Resolve the hardware decoding mode used for mpv startup.

        Args:
            configured_hwdec: Config value. Empty/None defaults to auto-safe;
                "detect" uses the legacy OS-based Raspberry Pi heuristic.

        Returns:
            str: The --hwdec value to pass to mpv.
        """
        value = (configured_hwdec or "auto-safe").strip()
        if not value:
            return "auto-safe"
        if value.lower() == "detect":
            return self._detect_hwdec()
        self.logger.debug(f"Hardware decoding configured: {value}")
        return value

    def _detect_hwdec(self) -> str:
        """
        Detect the correct hardware decoding backend for this OS.

        Uses /etc/debian_version to determine the OS generation:
        - Bullseye = Debian 11 -> rpi4-mmal (MMAL available on older builds)
        - Bookworm = Debian 12+ -> v4l2m2m-copy (MMAL removed in 64-bit kernel)

        This is more reliable than testing mpv directly because mpv returns
        a non-zero exit code for invalid input regardless of hwdec support.

        Returns:
            str: The --hwdec value to pass to mpv.
        """
        try:
            result = subprocess.run(
                ['cat', '/etc/debian_version'],
                capture_output=True,
                text=True,
                timeout=3,
            )
            version_str = result.stdout.strip()
            major = int(version_str.split('.')[0])
            if major >= 12:
                self.logger.debug(
                    "Hardware decoding: v4l2m2m-copy "
                    "(Bookworm / Debian 12+)"
                )
                return 'v4l2m2m-copy'
        except Exception:
            pass

        self.logger.debug("Hardware decoding: rpi4-mmal (Bullseye / Debian 11)")
        return 'rpi4-mmal'
