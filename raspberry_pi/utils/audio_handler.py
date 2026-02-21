#!/usr/bin/env python3
"""
Audio handler for pygame-based audio playback.

Manages music streaming, SFX RAM caching, multi-channel polyphony,
and command-driven playback control for museum room audio.
"""

import pygame
import os
import time
from utils.logging_setup import get_logger


class AudioHandler:
    """
    Pygame-based audio handler supporting music streaming and SFX RAM caching.

    Manages two parallel playback paths:
    - Music: streamed from disk via pygame.mixer.music (one track at a time).
    - SFX: preloaded into RAM as Sound objects and played on mixer channels.

    Provides command parsing, volume control, end-of-track detection,
    and status reporting for dashboard integration.
    """

    def __init__(self, audio_dir, logger=None, max_init_attempts=3,
                 init_retry_delay=5):
        """
        Initialize the audio handler and attempt mixer setup.

        Args:
            audio_dir: Path to the directory containing audio files.
            logger: Logger instance for audio events.
            max_init_attempts: Maximum number of mixer initialization attempts.
            init_retry_delay: Seconds to wait between initialization retries.
        """
        self.audio_dir = audio_dir
        self.logger = logger or get_logger('audio')

        # Settings
        self.max_init_attempts = max_init_attempts
        self.init_retry_delay = init_retry_delay

        # File size threshold for automatic streaming (if no sfx_ prefix)
        self.STREAM_THRESHOLD = 5 * 1024 * 1024

        # State
        self.audio_available = False
        self.initialization_attempts = 0
        self.last_init_attempt = 0

        # Tracking
        self.current_music_file = None      # Currently playing music (streamed)
        self.music_was_playing = False

        # RAM cache for SFX (Sound objects loaded into memory)
        self.sound_cache = {}

        # Active effects tracking: {"filename": [channel_obj, channel_obj, ...]}
        # Used for dashboard status and STOP:<filename> commands
        self.active_effects = {}

        self.end_callback = None

        self._initialize_audio_system()

    def _initialize_audio_system(self):
        """
        Initialize the pygame mixer with multiple fallback configurations.

        Tries up to three audio configurations in order of preference,
        setting up 32 mixer channels for polyphonic SFX playback.
        Sets self.audio_available to True on success, False on total failure.
        """
        self.initialization_attempts += 1
        self.last_init_attempt = time.time()

        audio_configs = [
            {"freq": 48000, "size": -16, "channels": 2, "buffer": 4096,
             "env": "default"},
            {"freq": 44100, "size": -16, "channels": 2, "buffer": 4096,
             "env": "hw:0,0"},
            {"freq": 22050, "size": -16, "channels": 1, "buffer": 2048,
             "env": None}
        ]

        for i, config in enumerate(audio_configs):
            try:
                if config["env"]:
                    os.environ["ALSA_DEFAULT_PCM"] = config["env"]
                elif "ALSA_DEFAULT_PCM" in os.environ:
                    del os.environ["ALSA_DEFAULT_PCM"]

                try:
                    pygame.mixer.quit()
                except:
                    pass

                pygame.mixer.pre_init(
                    frequency=config["freq"],
                    size=config["size"],
                    channels=config["channels"],
                    buffer=config["buffer"]
                )
                pygame.mixer.init()

                # Increase channel count to support polyphonic SFX playback
                pygame.mixer.set_num_channels(32)

                self.audio_available = True
                device_info = (
                    "3.5mm jack (default)"
                    if config["env"] == "default"
                    else f"device config {i + 1}"
                )
                self.logger.info(
                    f"Audio initialized successfully using {device_info}"
                )
                return

            except Exception as e:
                self.logger.debug(f"Audio config {i + 1} failed: {e}")
                continue

        self.audio_available = False
        self.logger.error("Audio initialization failed completely")

    def preload_files_for_scene(self, file_list):
        """
        Clear the RAM cache and preload SFX files for the upcoming scene.

        Only files with the 'sfx_' prefix are loaded into RAM.
        All currently playing audio is stopped before loading begins.

        Args:
            file_list: List of audio filenames to evaluate for preloading.
        """
        if not self.audio_available:
            return

        self.logger.info("Starting Dynamic Preload for Scene...")

        # 1. Stop all current audio
        self.stop_all()

        # 2. Clear the existing RAM cache
        cleaned_count = len(self.sound_cache)
        self.sound_cache.clear()

        # 3. Load new SFX files into RAM
        loaded_count = 0
        for filename in file_list:
            # Only load files with the 'sfx_' prefix
            if filename.lower().startswith("sfx_"):
                resolved_file, full_path = self._resolve_audio_file(filename)

                if resolved_file and self._validate_audio_file(
                        resolved_file, full_path):
                    try:
                        # Load into RAM as a Sound object
                        sound_obj = pygame.mixer.Sound(full_path)
                        self.sound_cache[resolved_file] = sound_obj
                        loaded_count += 1
                        self.logger.debug(f"Loaded to RAM: {resolved_file}")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to preload {filename}: {e}"
                        )

        self.logger.info(
            f"Preload complete. {loaded_count} SFX files ready in RAM. "
            f"(Cleared {cleaned_count})"
        )

    def play_audio_file(self, filename, volume=1.0):
        """
        Play an audio file using the appropriate playback path.

        Path 1 — RAM cache (SFX): if the resolved filename is present in the
        sound cache, it is played on a mixer channel for polyphonic support.

        Path 2 — Stream from disk (music): if not cached, the file is loaded
        and streamed via pygame.mixer.music. Only one stream plays at a time.

        Args:
            filename: Audio filename or path to play.
            volume: Playback volume between 0.0 and 1.0 (default: 1.0).

        Returns:
            bool: True if playback started successfully, False otherwise.
        """
        self._retry_audio_init()
        if not self.audio_available:
            return False

        try:
            resolved_name, full_path = self._resolve_audio_file(filename)
            if not resolved_name:
                return False

            # --- Path 1: File is in RAM cache (SFX) ---
            if resolved_name in self.sound_cache:
                try:
                    sound = self.sound_cache[resolved_name]
                    sound.set_volume(volume)
                    # play() returns a Channel object for tracking
                    channel = sound.play()

                    if channel:
                        # Store the channel for dashboard tracking and STOP commands
                        if resolved_name not in self.active_effects:
                            self.active_effects[resolved_name] = []
                        self.active_effects[resolved_name].append(channel)

                        self.logger.info(
                            f"Playing SFX (RAM): {resolved_name} (Vol: {volume})"
                        )
                        return True
                    else:
                        self.logger.warning(
                            f"No free channels for SFX: {resolved_name}"
                        )
                        return False
                except Exception as e:
                    self.logger.error(
                        f"Failed to play RAM SFX {resolved_name}: {e}"
                    )
                    return False

            # --- Path 2: Not in cache -> stream from disk (music) ---
            file_size = os.path.getsize(full_path)

            # Stop any currently playing music before loading a new stream
            if self.current_music_file:
                pygame.mixer.music.stop()

            try:
                pygame.mixer.music.load(full_path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play()

                self.current_music_file = resolved_name
                self.music_was_playing = True
                self.logger.info(
                    f"Playing MUSIC (Stream): {resolved_name} (Vol: {volume})"
                )
                return True
            except Exception as e:
                self.logger.error(
                    f"Failed to stream music {resolved_name}: {e}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error in play_audio_file: {e}")
            return False

    def handle_command(self, message):
        """
        Parse and execute an audio command string received from MQTT or JSON.

        Supported commands:
        - PLAY:<filename>[:<volume>] — play a file at optional volume
        - STOP — stop all audio
        - STOP:<filename> — stop a specific file
        - PAUSE — pause all audio
        - RESUME — resume all paused audio
        - VOLUME:<value> — set global music volume (0.0–1.0)
        - <filename> — treat as a plain filename and attempt playback

        Args:
            message: Command string to parse and execute.

        Returns:
            bool: True if the command was handled successfully, False otherwise.
        """
        if not message:
            return False

        try:
            # Strip whitespace and normalize to string
            clean_message = str(message).strip()

            if clean_message.startswith("PLAY:"):
                parts = clean_message.split(":")
                filename = parts[1]
                volume = float(parts[2]) if len(parts) > 2 else 1.0
                return self.play_audio_file(
                    filename, max(0.0, min(1.0, volume))
                )

            # Case-insensitive STOP check
            elif clean_message.upper() == "STOP":
                return self.stop_all()

            elif clean_message.startswith("STOP:"):
                # Stop a specific named file
                target = clean_message.split(":")[1]
                return self.stop_specific(target)

            elif clean_message == "PAUSE":
                return self.pause_audio()

            elif clean_message == "RESUME":
                return self.resume_audio()

            elif clean_message.startswith("VOLUME:"):
                try:
                    vol = float(clean_message.split(":")[1])
                    return self.set_volume(vol)
                except:
                    return False

            else:
                # Not a recognized command — attempt to play as a filename
                return self.play_audio_file(clean_message)

        except Exception as e:
            self.logger.error(
                f"Failed to handle audio command '{message}': {e}"
            )
            return False

    def stop_all(self):
        """
        Stop all currently playing audio (music stream and all SFX channels).

        Fades out the music stream before stopping it, then halts all SFX
        mixer channels and clears the active effects tracker.

        Returns:
            bool: True if audio was stopped successfully, False on error.
        """
        if not self.audio_available:
            return True

        try:
            if pygame.mixer.music.get_busy():
                self.logger.info("Stopping music stream...")
                pygame.mixer.music.fadeout(500)
                time.sleep(0.1)
                pygame.mixer.music.stop()
                try:
                    pygame.mixer.music.unload()
                except:
                    pass

            self.current_music_file = None

            # Stop all SFX mixer channels (RAM playback)
            pygame.mixer.stop()

            # Clear the active effects tracker
            self.active_effects.clear()

            self.logger.info("Stopped ALL audio")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping all: {e}")
            return False

    def stop_specific(self, filename):
        """
        Stop playback of a specific audio file.

        Checks both the music stream and active SFX channels for a match
        and stops whichever is currently playing the specified file.

        Args:
            filename: Filename of the audio to stop.

        Returns:
            bool: Always True (stop is best-effort).
        """
        resolved_name, _ = self._resolve_audio_file(filename)
        if not resolved_name:
            resolved_name = filename

        # 1. Check if it is the current music stream
        if self.current_music_file == resolved_name:
            pygame.mixer.music.stop()
            self.current_music_file = None
            self.logger.info(f"Stopped specific MUSIC: {resolved_name}")

        # 2. Check if it is an active SFX effect
        if resolved_name in self.active_effects:
            for ch in self.active_effects[resolved_name]:
                ch.stop()
            del self.active_effects[resolved_name]
            self.logger.info(f"Stopped specific SFX: {resolved_name}")

        return True

    def pause_audio(self):
        """
        Pause all currently playing audio (music and all SFX channels).

        Returns:
            bool: True if pause was applied, False if audio is unavailable.
        """
        if not self.audio_available:
            return False
        pygame.mixer.music.pause()
        pygame.mixer.pause()  # Pause all SFX channels
        return True

    def resume_audio(self):
        """
        Resume all paused audio (music and all SFX channels).

        Returns:
            bool: True if resume was applied, False if audio is unavailable.
        """
        if not self.audio_available:
            return False
        pygame.mixer.music.unpause()
        pygame.mixer.unpause()  # Resume all SFX channels
        return True

    def set_volume(self, volume):
        """
        Set the music stream volume.

        Note: pygame.mixer.Sound volume is set per object, so there is no
        direct global volume control for SFX channels via pygame.mixer.

        Args:
            volume: Volume level between 0.0 and 1.0.

        Returns:
            bool: True if volume was set, False if audio is unavailable.
        """
        if not self.audio_available:
            return False
        volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(volume)
        return True

    def _resolve_audio_file(self, audio_file):
        """
        Resolve an audio filename to a clean name and full filesystem path.

        Strips the 'PLAY_' prefix if present and attempts to locate the file
        with or without an extension by trying .mp3, .wav, and .ogg.

        Args:
            audio_file: Raw audio filename or command-prefixed filename.

        Returns:
            tuple: (resolved_filename, full_path) if found,
                   or (None, None) if the file cannot be located.
        """
        clean_name = audio_file.replace("PLAY_", "")
        full_path = os.path.join(self.audio_dir, clean_name)
        if os.path.exists(full_path):
            return clean_name, full_path

        base, ext = os.path.splitext(clean_name)
        if not ext:
            for try_ext in ['.mp3', '.wav', '.ogg']:
                test_path = os.path.join(self.audio_dir, base + try_ext)
                if os.path.exists(test_path):
                    return base + try_ext, test_path

        # File not found — caller is responsible for handling None
        return None, None

    def _validate_audio_file(self, audio_file, full_path):
        """
        Validate that an audio file exists at the given path.

        Args:
            audio_file: Filename used for logging purposes.
            full_path: Full filesystem path to verify.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        if not os.path.exists(full_path):
            self.logger.warning(f"Audio file not found: {full_path}")
            return False
        return True

    def _can_retry_init(self):
        """
        Determine whether a mixer re-initialization attempt is permitted.

        Returns:
            bool: True if retry conditions are met, False otherwise.
        """
        if self.audio_available:
            return False
        if self.initialization_attempts >= self.max_init_attempts:
            return False
        if time.time() - self.last_init_attempt < self.init_retry_delay:
            return False
        return True

    def _retry_audio_init(self):
        """Retry mixer initialization if permitted by retry conditions."""
        if self._can_retry_init():
            self.logger.info("Retrying audio initialization...")
            self._initialize_audio_system()

    # --- Compatibility Aliases ---

    def play_audio(self, message):
        """Alias for handle_command."""
        return self.handle_command(message)

    def stop_audio(self):
        """Alias for stop_all."""
        return self.stop_all()

    # --- End-of-Track Detection (for transitions and dashboard) ---

    def set_end_callback(self, callback):
        """
        Register a callback to be invoked when a track finishes playing.

        Args:
            callback: Callable accepting a filename string, called when
                a music stream or SFX completes playback naturally.
        """
        self.end_callback = callback

    def check_if_ended(self):
        """
        Detect and report naturally completed audio playback.

        Called periodically from the main loop. Checks the music stream
        and all active SFX channels, invoking the end callback for any
        that have finished and cleaning up their tracking entries.
        """
        if not self.audio_available:
            return

        # 1. Check music stream
        is_music_playing = pygame.mixer.music.get_busy()
        if self.music_was_playing and not is_music_playing:
            if self.current_music_file:
                self.logger.info(f"Music finished: {self.current_music_file}")
                if self.end_callback:
                    self.end_callback(self.current_music_file)
                self.current_music_file = None
        self.music_was_playing = is_music_playing

        # 2. Check active SFX channels (RAM)
        # Retain only channels that are still busy, remove completed ones
        ended_effects = []
        for filename, channels in self.active_effects.items():
            active_channels = [ch for ch in channels if ch.get_busy()]
            self.active_effects[filename] = active_channels

            # If no channels remain, the sound has fully completed
            if not active_channels:
                ended_effects.append(filename)

        for filename in ended_effects:
            # self.logger.info(f"SFX finished: {filename}")  # Optional logging
            del self.active_effects[filename]
            if self.end_callback:
                self.end_callback(filename)

    def cleanup(self):
        """Stop all audio and shut down the pygame mixer."""
        try:
            self.stop_all()
            pygame.mixer.quit()
        except:
            pass

    # --- Dashboard / Status Methods ---

    def is_playing(self):
        """
        Check whether any audio is currently playing.

        Returns:
            bool: True if music or any SFX is active, False otherwise.
        """
        music_busy = False
        if self.audio_available:
            try:
                music_busy = pygame.mixer.music.get_busy()
            except:
                pass
        return music_busy or bool(self.active_effects)

    def get_audio_status(self):
        """
        Return a status snapshot of the audio system for dashboard use.

        Returns:
            dict: Status dictionary containing availability, playback state,
                current music filename, active SFX count, and cached file list.
        """
        return {
            'available': self.audio_available,
            'playing': self.is_playing(),
            'current_music': self.current_music_file,
            'active_sfx_count': len(self.active_effects),
            'ram_cached_files': list(self.sound_cache.keys())  # Debug info
        }