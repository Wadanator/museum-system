#!/usr/bin/env python3
import pygame
import os
import time
from utils.logging_setup import get_logger

class AudioHandler:
    def __init__(self, audio_dir, logger=None, max_init_attempts=3, init_retry_delay=5):
        self.audio_dir = audio_dir
        self.currently_playing = None
        self.logger = logger or get_logger('audio')
        self.audio_available = False
        self.initialization_attempts = 0
        self.max_init_attempts = max_init_attempts
        self.init_retry_delay = init_retry_delay
        self.last_init_attempt = 0
        
        # Audio end callback
        self.end_callback = None
        self.was_playing = False
        
        self._initialize_audio_system()
    
    def _initialize_audio_system(self):
        """Initialize pygame mixer with fallback handling."""
        self.initialization_attempts += 1
        self.last_init_attempt = time.time()
        
        # ZMENA: "default" je prvé, aby fungoval software mixing (prehrávanie zvuku a videa naraz)
        audio_configs = [
            {"freq": 48000, "size": -16, "channels": 2, "buffer": 8192, "env": "default"},
            {"freq": 44100, "size": -16, "channels": 2, "buffer": 4096, "env": "hw:0,0"},
            {"freq": 22050, "size": -16, "channels": 1, "buffer": 4096, "env": None}
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
                pygame.mixer.get_init()
                
                self.audio_available = True
                device_info = "3.5mm jack (default)" if config["env"] == "default" else f"device config {i+1}"
                self.logger.info(f"Audio initialized successfully using {device_info}")
                return
                
            except Exception as e:
                self.logger.debug(f"Audio config {i+1} failed: {e}")
                continue
        
        self.audio_available = False
        if self.initialization_attempts <= self.max_init_attempts:
            self.logger.warning(f"Audio initialization failed (attempt {self.initialization_attempts}/{self.max_init_attempts})")
            self.logger.warning("Audio will be disabled until manual retry or system restart")
        else:
            self.logger.error(f"Audio permanently disabled after {self.max_init_attempts} attempts")
    
    def _can_retry_init(self):
        if self.audio_available:
            return False
        if self.initialization_attempts >= self.max_init_attempts:
            return False
        if time.time() - self.last_init_attempt < self.init_retry_delay:
            return False
        return True
    
    def _retry_audio_init(self):
        if self._can_retry_init():
            self.logger.info("Retrying audio initialization...")
            self._initialize_audio_system()
    
    def _resolve_audio_file(self, audio_file):
        if audio_file.startswith("PLAY_"):
            filename = audio_file.replace("PLAY_", "").lower()
            for ext in ['.wav', '.mp3', '.ogg']:
                test_file = filename + ext
                full_path = os.path.join(self.audio_dir, test_file)
                if os.path.exists(full_path):
                    return test_file, full_path
            self.logger.warning(f"Audio file not found for command: {audio_file}")
            return None, None
        
        full_path = os.path.join(self.audio_dir, audio_file)
        return audio_file, full_path
    
    def _validate_audio_file(self, audio_file, full_path):
        if not os.path.exists(full_path):
            self.logger.warning(f"Audio file not found: {full_path}")
            return False
        
        _, ext = os.path.splitext(audio_file.lower())
        if ext not in ['.wav', '.mp3', '.ogg']:
            self.logger.error(f"Unsupported audio format: {ext}")
            self.logger.info("Supported formats: .wav, .mp3, .ogg")
            return False
        
        return True
    
    def play_audio(self, audio_file):
        self._retry_audio_init()
        
        if not self.audio_available:
            self.logger.info(f"Audio disabled - would play: {audio_file}")
            return False
        
        try:
            resolved_file, full_path = self._resolve_audio_file(audio_file)
            if not resolved_file or not self._validate_audio_file(resolved_file, full_path):
                return False
            
            if self.currently_playing:
                pygame.mixer.music.stop()
            
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.play()
            self.currently_playing = resolved_file
            self.was_playing = True
            self.logger.info(f"Playing audio: {resolved_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error playing audio {audio_file}: {e}")
            self.audio_available = False
            return False

    def play_audio_with_volume(self, audio_file, volume=1):
        if self.play_audio(audio_file):
            try:
                pygame.mixer.music.set_volume(volume)
                self.logger.debug(f"Volume set to {volume}")
                return True
            except Exception as e:
                self.logger.warning(f"Error setting volume: {e}")
                return True
        return False

    def handle_command(self, message):
        if not message:
            return False
            
        try:
            if message.startswith("PLAY:"):
                parts = message.split(":")
                if len(parts) < 2:
                    return False
                filename = parts[1]
                volume = float(parts[2]) if len(parts) > 2 else 0.7
                return self.play_audio_with_volume(filename, volume)
                
            elif message.startswith("FADE_IN:"):
                self.logger.info(f"FADE_IN command not implemented: {message}")
                return True
                
            elif message.startswith("BASS_BOOST:"):
                self.logger.info(f"BASS_BOOST command not implemented: {message}")
                return True
                
            elif message == "STOP":
                return self.stop_audio()
            elif message == "PAUSE":
                return self.pause_audio()
            elif message == "RESUME":
                return self.resume_audio()
            elif message.startswith("VOLUME:"):
                try:
                    volume = float(message.split(":")[1])
                    return self.set_volume(volume)
                except (ValueError, IndexError):
                    return False
            else:
                return self.play_audio(message)
                
        except Exception as e:
            self.logger.error(f"Failed to handle audio command '{message}': {e}")
            return False

    def is_playing(self):
        if not self.audio_available:
            return False
        try:
            return pygame.mixer.music.get_busy()
        except:
            return False

    def pause_audio(self):
        if not self.audio_available:
            return False
        try:
            if self.currently_playing and self.is_playing():
                pygame.mixer.music.pause()
                self.logger.info(f"Paused audio: {self.currently_playing}")
                return True
        except Exception as e:
            self.logger.error(f"Error pausing audio: {e}")
        return False

    def resume_audio(self):
        if not self.audio_available:
            return False
        try:
            pygame.mixer.music.unpause()
            self.logger.info(f"Resumed audio: {self.currently_playing}")
            return True
        except Exception as e:
            self.logger.error(f"Error resuming audio: {e}")
            return False

    def stop_audio(self):
        if not self.audio_available:
            return True
        try:
            if self.currently_playing:
                pygame.mixer.music.stop()
                self.logger.info(f"Stopped audio: {self.currently_playing}")
                self.currently_playing = None
            return True
        except Exception as e:
            self.logger.error(f"Error stopping audio: {e}")
            return False

    def set_volume(self, volume):
        if not self.audio_available:
            return False
        try:
            volume = max(0.0, min(1.0, volume))
            pygame.mixer.music.set_volume(volume)
            self.logger.debug(f"Volume set to {volume}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting volume: {e}")
            return False

    def list_audio_files(self):
        try:
            if not os.path.exists(self.audio_dir):
                self.logger.warning(f"Audio directory not found: {self.audio_dir}")
                return []
            
            supported_extensions = ['.wav', '.mp3', '.ogg']
            audio_files = []
            
            for file in os.listdir(self.audio_dir):
                _, ext = os.path.splitext(file.lower())
                if ext in supported_extensions:
                    audio_files.append(file)
            
            return sorted(audio_files)
        except Exception as e:
            self.logger.error(f"Error listing audio files: {e}")
            return []

    def get_audio_status(self):
        return {
            'available': self.audio_available,
            'playing': self.is_playing(),
            'current_file': self.currently_playing,
            'init_attempts': self.initialization_attempts,
            'can_retry': self._can_retry_init()
        }

    def force_reinit(self):
        self.logger.info("Forcing audio reinitialization...")
        self.initialization_attempts = 0
        self.audio_available = False
        self._initialize_audio_system()
        return self.audio_available

    def set_end_callback(self, callback):
        self.end_callback = callback
    
    def check_if_ended(self):
        is_playing_now = self.is_playing()
        
        if self.was_playing and not is_playing_now:
            finished_file = self.currently_playing
            self.logger.info(f"Audio ended: {finished_file}")
            
            if self.end_callback:
                self.end_callback(finished_file)
            
            self.currently_playing = None # Pridané pre istotu vyčistenia
        
        self.was_playing = is_playing_now

    def cleanup(self):
        try:
            self.stop_audio()
            if self.audio_available:
                pygame.mixer.quit()
            self.logger.info("Audio handler cleaned up")
        except Exception as e:
            self.logger.error(f"Error during audio cleanup: {e}")