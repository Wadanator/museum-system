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
        
        self._initialize_audio_system()
    
    def _initialize_audio_system(self):
        """Initialize pygame mixer with fallback handling."""
        self.initialization_attempts += 1
        self.last_init_attempt = time.time()
        
        # Try different audio configurations
        audio_configs = [
            # Primary: 3.5mm jack
            {"freq": 44100, "size": -16, "channels": 2, "buffer": 2048, "env": "hw:0,0"},
            # Fallback: Default ALSA
            {"freq": 44100, "size": -16, "channels": 2, "buffer": 4096, "env": "default"},
            # Fallback: Any available device
            {"freq": 22050, "size": -16, "channels": 1, "buffer": 4096, "env": None}
        ]
        
        for i, config in enumerate(audio_configs):
            try:
                # Set ALSA environment if specified
                if config["env"]:
                    os.environ["ALSA_DEFAULT_PCM"] = config["env"]
                elif "ALSA_DEFAULT_PCM" in os.environ:
                    del os.environ["ALSA_DEFAULT_PCM"]
                
                # Quit any existing mixer
                try:
                    pygame.mixer.quit()
                except:
                    pass
                
                # Initialize with current config
                pygame.mixer.pre_init(
                    frequency=config["freq"], 
                    size=config["size"], 
                    channels=config["channels"], 
                    buffer=config["buffer"]
                )
                pygame.mixer.init()
                
                # Test if it actually works
                pygame.mixer.get_init()
                
                self.audio_available = True
                device_info = "3.5mm jack" if i == 0 else f"fallback device {i+1}"
                self.logger.info(f"Audio initialized successfully using {device_info}")
                return
                
            except Exception as e:
                self.logger.debug(f"Audio config {i+1} failed: {e}")
                continue
        
        # All configurations failed
        self.audio_available = False
        if self.initialization_attempts <= self.max_init_attempts:
            self.logger.warning(f"Audio initialization failed (attempt {self.initialization_attempts}/{self.max_init_attempts})")
            self.logger.warning("Audio will be disabled until manual retry or system restart")
        else:
            self.logger.error(f"Audio permanently disabled after {self.max_init_attempts} attempts")
    
    def _can_retry_init(self):
        """Check if we can retry audio initialization."""
        if self.audio_available:
            return False
        if self.initialization_attempts >= self.max_init_attempts:
            return False
        if time.time() - self.last_init_attempt < self.init_retry_delay:
            return False
        return True
    
    def _retry_audio_init(self):
        """Retry audio initialization if conditions are met."""
        if self._can_retry_init():
            self.logger.info("Retrying audio initialization...")
            self._initialize_audio_system()
    
    def _resolve_audio_file(self, audio_file):
        """Resolve audio file path, handling PLAY_ commands and extensions."""
        # Handle PLAY_ command format
        if audio_file.startswith("PLAY_"):
            filename = audio_file.replace("PLAY_", "").lower()
            for ext in ['.wav', '.mp3', '.ogg']:
                test_file = filename + ext
                full_path = os.path.join(self.audio_dir, test_file)
                if os.path.exists(full_path):
                    return test_file, full_path
            self.logger.warning(f"Audio file not found for command: {audio_file}")
            return None, None
        
        # Handle direct file reference
        full_path = os.path.join(self.audio_dir, audio_file)
        return audio_file, full_path
    
    def _validate_audio_file(self, audio_file, full_path):
        """Validate audio file exists and has supported format."""
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
        """Play audio file with fallback handling."""
        # Try to retry initialization if needed
        self._retry_audio_init()
        
        if not self.audio_available:
            self.logger.info(f"Audio disabled - would play: {audio_file}")
            return False
        
        try:
            # Resolve and validate file
            resolved_file, full_path = self._resolve_audio_file(audio_file)
            if not resolved_file or not self._validate_audio_file(resolved_file, full_path):
                return False
            
            # Stop current playback if any
            if self.currently_playing:
                pygame.mixer.music.stop()
            
            # Load and play audio
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.play()
            self.currently_playing = resolved_file
            self.logger.info(f"Playing audio: {resolved_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error playing audio {audio_file}: {e}")
            # If we get an error during playback, mark audio as unavailable
            self.audio_available = False
            return False

    def play_audio_with_volume(self, audio_file, volume=1):
        """Play audio file with specific volume level."""
        if self.play_audio(audio_file):
            try:
                pygame.mixer.music.set_volume(volume)
                self.logger.debug(f"Volume set to {volume}")
                return True
            except Exception as e:
                self.logger.warning(f"Error setting volume: {e}")
                return True  # Still return True as audio is playing
        return False

    def handle_command(self, message):
        """Handle audio commands with robust error handling."""
        if not message:
            return False
            
        try:
            if message.startswith("PLAY:"):
                # Handle PLAY:filename:volume
                parts = message.split(":")
                if len(parts) < 2:
                    return False
                filename = parts[1]
                volume = float(parts[2]) if len(parts) > 2 else 0.7
                return self.play_audio_with_volume(filename, volume)
                
            elif message.startswith("FADE_IN:"):
                # Handle FADE_IN:duration - not implemented yet
                self.logger.info(f"FADE_IN command not implemented: {message}")
                return True  # Don't treat as error
                
            elif message.startswith("BASS_BOOST:"):
                # Handle BASS_BOOST:ON/OFF - not implemented yet  
                self.logger.info(f"BASS_BOOST command not implemented: {message}")
                return True  # Don't treat as error
                
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
                # Handle direct filename
                return self.play_audio(message)
                
        except Exception as e:
            self.logger.error(f"Failed to handle audio command '{message}': {e}")
            return False

    # Public Audio Control Methods
    def is_playing(self):
        """Check if audio is currently playing."""
        if not self.audio_available:
            return False
        try:
            return pygame.mixer.music.get_busy()
        except:
            return False

    def pause_audio(self):
        """Pause currently playing audio."""
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
        """Resume paused audio."""
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
        """Stop currently playing audio."""
        if not self.audio_available:
            return True  # Return True as "stopping" silent audio is successful
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
        """Set audio volume (0.0 to 1.0)."""
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

    # Public Audio File Management
    def list_audio_files(self):
        """List all supported audio files in the audio directory."""
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
        """Get current audio system status."""
        return {
            'available': self.audio_available,
            'playing': self.is_playing(),
            'current_file': self.currently_playing,
            'init_attempts': self.initialization_attempts,
            'can_retry': self._can_retry_init()
        }

    def force_reinit(self):
        """Force audio reinitialization (for web dashboard)."""
        self.logger.info("Forcing audio reinitialization...")
        self.initialization_attempts = 0
        self.audio_available = False
        self._initialize_audio_system()
        return self.audio_available

    # Public Cleanup
    def cleanup(self):
        """Clean up audio resources."""
        try:
            self.stop_audio()
            if self.audio_available:
                pygame.mixer.quit()
            self.logger.info("Audio handler cleaned up")
        except Exception as e:
            self.logger.error(f"Error during audio cleanup: {e}")

if __name__ == "__main__":
    # Test script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(script_dir, "..", "audio")
    
    print(f"Audio directory: {audio_dir}")
    
    audio_handler = AudioHandler(audio_dir)
    
    print("Available audio files:")
    files = audio_handler.list_audio_files()
    if files:
        for i, file in enumerate(files, 1):
            print(f"  {i}. {file}")
    else:
        print("  No audio files found")
    
    print(f"\nAudio status: {audio_handler.get_audio_status()}")
    
    if files and audio_handler.audio_available:
        print(f"\nTesting playback of first file: {files[0]}")
        audio_handler.play_audio_with_volume(files[0], 1.0)
        import time
        print("Playing for 5 seconds...")
        time.sleep(5)
        audio_handler.stop_audio()
    
    audio_handler.cleanup()