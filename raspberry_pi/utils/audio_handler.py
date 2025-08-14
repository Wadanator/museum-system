#!/usr/bin/env python3
import pygame
import os
import logging
from utils.logging_setup import get_logger

class AudioHandler:
    def __init__(self, audio_dir, logger=None):
        self.audio_dir = audio_dir
        self.currently_playing = None
        self.logger = logger or get_logger('audio')
        
        self._initialize_audio_system()
    
    def _initialize_audio_system(self):
        """Initialize pygame mixer with 3.5mm jack output."""
        os.environ["ALSA_DEFAULT_PCM"] = "hw:0,0"
        
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
            pygame.mixer.init()
            self.logger.info("Audio handler initialized with 3.5mm jack output")
        except Exception as e:
            self.logger.error(f"Error initializing pygame mixer: {e}")
            raise SystemExit(1)
    
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
        """Play audio file through 3.5mm jack."""
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
            self.logger.info(f"Playing audio: {resolved_file} through 3.5mm jack")
            return True
            
        except Exception as e:
            self.logger.error(f"Error playing audio {audio_file}: {e}")
            return False

    def play_audio_with_volume(self, audio_file, volume=1):
        """Play audio file with specific volume level."""
        if self.play_audio(audio_file):
            pygame.mixer.music.set_volume(volume)
            self.logger.debug(f"Volume set to {volume}")
            return True
        return False

    def handle_command(self, message):
        try:
            if message.startswith("PLAY:"):
                parts = message.split(":")
                filename = parts[1]
                volume = float(parts[2]) if len(parts) > 2 else 0.7
                return self.play_audio_with_volume(filename, volume)
                
            elif message == "STOP":
                return self.stop_audio()
                
            elif message == "PAUSE":
                return self.pause_audio()
                
            elif message == "RESUME":
                return self.resume_audio()
                
            elif message.startswith("VOLUME:"):
                volume = float(message.split(":")[1])
                return self.set_volume(volume)
                
            else:
                # Handle direct filename or PLAY_ commands
                return self.play_audio(message)
                
        except Exception as e:
            self.logger.error(f"Failed to handle audio command '{message}': {e}")
            return False

    # Public Audio Control Methods
    def is_playing(self):
        """Check if audio is currently playing."""
        return pygame.mixer.music.get_busy()

    def pause_audio(self):
        """Pause currently playing audio."""
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
        try:
            pygame.mixer.music.unpause()
            self.logger.info(f"Resumed audio: {self.currently_playing}")
            return True
        except Exception as e:
            self.logger.error(f"Error resuming audio: {e}")
            return False

    def stop_audio(self):
        """Stop currently playing audio."""
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

    # Public Cleanup
    def cleanup(self):
        """Clean up audio resources."""
        try:
            self.stop_audio()
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
    
    if files:
        print(f"\nTesting playback of first file: {files[0]}")
        audio_handler.play_audio_with_volume(files[0], 1.0)
        import time
        print("Playing for 5 seconds...")
        time.sleep(5)
        audio_handler.stop_audio()
    
    audio_handler.cleanup()