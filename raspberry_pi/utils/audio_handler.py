#!/usr/bin/env python3
import pygame
import os
import sys

class AudioHandler:
    def __init__(self, audio_dir):
        self.audio_dir = audio_dir
        self.currently_playing = None
        
        # Initialize pygame mixer with better settings for various formats
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            print("✅ Audio handler initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing pygame mixer: {e}")
            sys.exit(1)
    
    def play_audio(self, audio_file):
        """Play an audio file from the audio directory. Supports WAV, MP3, OGG formats."""
        try:
            # Check if it's a direct filename or a command
            if audio_file.startswith("PLAY_"):
                # Legacy support - extract filename from command
                filename = audio_file.replace("PLAY_", "").lower()
                # Try different extensions
                for ext in ['.wav', '.mp3', '.ogg']:
                    test_file = filename + ext
                    full_path = os.path.join(self.audio_dir, test_file)
                    if os.path.exists(full_path):
                        audio_file = test_file
                        break
                else:
                    print(f"❌ Audio file not found for command: {audio_file}")
                    return False
            
            full_path = os.path.join(self.audio_dir, audio_file)
            
            if not os.path.exists(full_path):
                print(f"❌ Audio file not found: {full_path}")
                return False
            
            # Check file extension
            _, ext = os.path.splitext(audio_file.lower())
            if ext not in ['.wav', '.mp3', '.ogg']:
                print(f"⚠️  Unsupported audio format: {ext}")
                print("Supported formats: .wav, .mp3, .ogg")
                return False
            
            # Stop any currently playing audio
            if self.currently_playing:
                pygame.mixer.music.stop()
            
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.play()
            self.currently_playing = audio_file
            print(f"🎵 Playing audio: {audio_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error playing audio {audio_file}: {e}")
            return False
    
    def play_audio_with_volume(self, audio_file, volume=0.7):
        """Play audio file with specified volume (0.0 to 1.0)."""
        if self.play_audio(audio_file):
            pygame.mixer.music.set_volume(volume)
            print(f"🔊 Volume set to {volume}")
            return True
        return False
    
    def is_playing(self):
        """Check if audio is currently playing."""
        return pygame.mixer.music.get_busy()
    
    def pause_audio(self):
        """Pause currently playing audio."""
        try:
            if self.currently_playing and self.is_playing():
                pygame.mixer.music.pause()
                print(f"⏸️  Paused audio: {self.currently_playing}")
                return True
        except Exception as e:
            print(f"❌ Error pausing audio: {e}")
        return False
    
    def resume_audio(self):
        """Resume paused audio."""
        try:
            pygame.mixer.music.unpause()
            print(f"▶️  Resumed audio: {self.currently_playing}")
            return True
        except Exception as e:
            print(f"❌ Error resuming audio: {e}")
            return False
    
    def stop_audio(self):
        """Stop currently playing audio."""
        try:
            if self.currently_playing:
                pygame.mixer.music.stop()
                print(f"⏹️  Stopped audio: {self.currently_playing}")
                self.currently_playing = None
            return True
        except Exception as e:
            print(f"❌ Error stopping audio: {e}")
            return False
    
    def set_volume(self, volume):
        """Set volume for currently playing audio (0.0 to 1.0)."""
        try:
            volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
            pygame.mixer.music.set_volume(volume)
            print(f"🔊 Volume set to {volume}")
            return True
        except Exception as e:
            print(f"❌ Error setting volume: {e}")
            return False
    
    def list_audio_files(self):
        """List all supported audio files in the audio directory."""
        try:
            if not os.path.exists(self.audio_dir):
                print(f"❌ Audio directory not found: {self.audio_dir}")
                return []
            
            supported_extensions = ['.wav', '.mp3', '.ogg']
            audio_files = []
            
            for file in os.listdir(self.audio_dir):
                _, ext = os.path.splitext(file.lower())
                if ext in supported_extensions:
                    audio_files.append(file)
            
            return sorted(audio_files)
        except Exception as e:
            print(f"❌ Error listing audio files: {e}")
            return []
    
    def cleanup(self):
        """Clean up audio resources."""
        try:
            self.stop_audio()
            pygame.mixer.quit()
            print("🧹 Audio handler cleaned up")
        except Exception as e:
            print(f"❌ Error during audio cleanup: {e}")

# Example usage and testing
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(script_dir, "..", "audio")
    
    print(f"Audio directory: {audio_dir}")
    
    audio_handler = AudioHandler(audio_dir)
    
    # List available audio files
    print("\n📁 Available audio files:")
    files = audio_handler.list_audio_files()
    if files:
        for i, file in enumerate(files, 1):
            print(f"  {i}. {file}")
    else:
        print("  No audio files found")
    
    # Test audio playback if files exist
    if files:
        print(f"\n🎵 Testing playback of first file: {files[0]}")
        audio_handler.play_audio_with_volume(files[0], 0.5)
        
        import time
        print("Playing for 5 seconds...")
        time.sleep(5)
        
        audio_handler.stop_audio()
    
    audio_handler.cleanup()