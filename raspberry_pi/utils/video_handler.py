#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import time
import signal
from pathlib import Path

class VideoHandler:
    def __init__(self, video_dir, display=":0.0"):
        """
        Initialize VideoHandler for Raspberry Pi with dual HDMI support.
        
        Args:
            video_dir (str): Directory containing video files
            display (str): X11 display for second HDMI (":0.0" for HDMI-1)
        """
        self.video_dir = video_dir
        self.display = display
        self.currently_playing = None
        self.omx_process = None
        self.vlc_process = None
        self.playback_thread = None
        self.is_playing_flag = False
        self.playback_method = None
        self.black_screen_process = None
        
        # Ensure video directory exists
        os.makedirs(self.video_dir, exist_ok=True)
        
        # Check available video players and setup
        self._detect_video_player()
        self._setup_display()
        
        print("Video handler initialized successfully")
        print(f"Video directory: {self.video_dir}")
        print(f"Target display: {self.display}")
        print(f"Using player: {self.playback_method}")
    
    def _detect_video_player(self):
        """Detect available video players on the system."""
        # Check for omxplayer (Raspberry Pi optimized)
        try:
            subprocess.run(['omxplayer', '--version'], 
                         capture_output=True, check=True, timeout=5)
            self.playback_method = 'omxplayer'
            print("Found omxplayer (Raspberry Pi optimized)")
            return
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Check for VLC
        try:
            subprocess.run(['vlc', '--version'], 
                         capture_output=True, check=True, timeout=5)
            self.playback_method = 'vlc'
            print("Found VLC media player")
            return
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Check for ffplay (from ffmpeg)
        try:
            subprocess.run(['ffplay', '-version'], 
                         capture_output=True, check=True, timeout=5)
            self.playback_method = 'ffplay'
            print("Found ffplay")
            return
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        print("ERROR: No suitable video player found!")
        print("Please install one of: omxplayer, vlc, or ffmpeg")
        self.playback_method = None
    
    def _setup_display(self):
        """Setup display environment for second HDMI and maintain black screen."""
        try:
            # Set DISPLAY environment variable for X11
            os.environ['DISPLAY'] = self.display
            
            # Start persistent black screen
            self._start_black_screen()
            
        except Exception as e:
            print(f"WARNING: Display setup warning: {e}")
    
    def _start_black_screen(self):
        """Start a persistent black screen that stays active."""
        try:
            # Stop any existing black screen
            self._stop_black_screen()
            
            # Method 1: Try using a simple black window with X11
            try:
                cmd = [
                    'xterm', '-display', self.display,
                    '-fullscreen', '-bg', 'black', '-fg', 'black',
                    '-e', 'sleep', '999999'
                ]
                self.black_screen_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("Black screen started with xterm")
                return
            except:
                pass
            
            # Method 2: Try with feh showing a black image
            try:
                # Create a minimal black image if it doesn't exist
                black_image_path = "/tmp/black.png"
                if not os.path.exists(black_image_path):
                    subprocess.run([
                        'convert', '-size', '1920x1080', 'xc:black', black_image_path
                    ], capture_output=True, timeout=5)
                
                cmd = [
                    'feh', '--fullscreen', '--hide-pointer', 
                    '--no-menus', black_image_path
                ]
                env = {'DISPLAY': self.display}
                self.black_screen_process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("Black screen started with feh")
                return
            except:
                pass
            
            # Method 3: Try with mplayer
            try:
                cmd = [
                    'mplayer', '-fs', '-loop', '0',
                    '-lavdopts', 'threads=2',
                    '/dev/zero'
                ]
                env = {'DISPLAY': self.display}
                self.black_screen_process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("Black screen started with mplayer")
                return
            except:
                pass
            
            # Method 4: Simple X11 black window
            try:
                cmd = [
                    'xwininfo', '-display', self.display, '-root'
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                if result.returncode == 0:
                    # Create black background
                    subprocess.run([
                        'xsetroot', '-display', self.display, '-solid', 'black'
                    ], capture_output=True, timeout=5)
                    print("Black screen set with xsetroot")
                    return
            except:
                pass
                
            print("WARNING: Could not establish persistent black screen")
            
        except Exception as e:
            print(f"ERROR: Black screen setup failed: {e}")
    
    def _stop_black_screen(self):
        """Stop the persistent black screen."""
        if self.black_screen_process:
            try:
                self.black_screen_process.terminate()
                self.black_screen_process.wait(timeout=3)
            except:
                try:
                    self.black_screen_process.kill()
                except:
                    pass
            self.black_screen_process = None
    
    def _make_display_black(self):
        """Ensure display is black (restart black screen if needed)."""
        if not self.black_screen_process or self.black_screen_process.poll() is not None:
            self._start_black_screen()
        else:
            # Black screen is already running
            try:
                # Bring black screen to front
                subprocess.run([
                    'xsetroot', '-display', self.display, '-solid', 'black'
                ], capture_output=True, timeout=2)
            except:
                pass
    
    def play_video(self, video_file):
        """Play a video file on the second display."""
        try:
            # Handle different command formats
            if video_file.startswith("PLAY_"):
                # Legacy support - extract filename from command
                filename = video_file.replace("PLAY_", "").lower()
                # Try different extensions
                for ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']:
                    test_file = filename + ext
                    full_path = os.path.join(self.video_dir, test_file)
                    if os.path.exists(full_path):
                        video_file = test_file
                        break
                else:
                    print(f"ERROR: Video file not found for command: {video_file}")
                    return False
            
            full_path = os.path.join(self.video_dir, video_file)
            
            if not os.path.exists(full_path):
                print(f"ERROR: Video file not found: {full_path}")
                return False
            
            # Check file extension
            _, ext = os.path.splitext(video_file.lower())
            supported_formats = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
            if ext not in supported_formats:
                print(f"WARNING: Potentially unsupported video format: {ext}")
                print(f"Supported formats: {', '.join(supported_formats)}")
            
            # Stop any currently playing video
            self.stop_video()
            
            # Temporarily stop black screen for video playback
            self._stop_black_screen()
            
            # Start playback in separate thread
            self.currently_playing = video_file
            self.is_playing_flag = True
            self.playback_thread = threading.Thread(
                target=self._play_video_thread, 
                args=(full_path,)
            )
            self.playback_thread.daemon = True
            self.playback_thread.start()
            
            print(f"Playing video: {video_file}")
            return True
            
        except Exception as e:
            print(f"ERROR: Error playing video {video_file}: {e}")
            return False
    
    def _play_video_thread(self, full_path):
        """Play video in separate thread."""
        try:
            if self.playback_method == 'omxplayer':
                self._play_with_omxplayer(full_path)
            elif self.playback_method == 'vlc':
                self._play_with_vlc(full_path)
            elif self.playback_method == 'ffplay':
                self._play_with_ffplay(full_path)
            else:
                print("ERROR: No video player available")
                return
                
        except Exception as e:
            print(f"ERROR: Video playback error: {e}")
        finally:
            # Cleanup after playback
            self.is_playing_flag = False
            self.currently_playing = None
            # Restart black screen after video ends
            self._start_black_screen()
            print("Display returned to black screen")
    
    def _play_with_omxplayer(self, full_path):
        """Play video using omxplayer (Raspberry Pi optimized)."""
        try:
            # omxplayer command for HDMI output
            cmd = [
                'omxplayer',
                '--display', '7',  # Force HDMI output
                '--no-osd',        # No on-screen display
                '--aspect-mode', 'letterbox',
                full_path
            ]
            
            self.omx_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for playback to complete
            self.omx_process.wait()
            
        except Exception as e:
            print(f"ERROR: omxplayer error: {e}")
        finally:
            self.omx_process = None
    
    def _play_with_vlc(self, full_path):
        """Play video using VLC."""
        try:
            cmd = [
                'vlc',
                '--intf', 'dummy',           # No interface
                '--no-video-title-show',     # Don't show title
                '--fullscreen',              # Fullscreen mode
                '--no-osd',                  # No on-screen display
                '--play-and-exit',           # Exit after playing
                full_path
            ]
            
            env = os.environ.copy()
            env['DISPLAY'] = self.display
            
            self.vlc_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for playback to complete
            self.vlc_process.wait()
            
        except Exception as e:
            print(f"ERROR: VLC error: {e}")
        finally:
            self.vlc_process = None
    
    def _play_with_ffplay(self, full_path):
        """Play video using ffplay."""
        try:
            cmd = [
                'ffplay',
                '-fs',              # Fullscreen
                '-autoexit',        # Exit when done
                '-loglevel', 'quiet',  # Quiet output
                full_path
            ]
            
            env = os.environ.copy()
            env['DISPLAY'] = self.display
            
            self.vlc_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for playback to complete
            self.vlc_process.wait()
            
        except Exception as e:
            print(f"ERROR: ffplay error: {e}")
        finally:
            self.vlc_process = None
    
    def play_video_with_volume(self, video_file, volume=0.7):
        """Play video with specified volume (0.0 to 1.0)."""
        # Note: Volume control depends on system audio setup
        # This is a placeholder for volume control
        print(f"Video volume requested: {volume} (system dependent)")
        return self.play_video(video_file)
    
    def is_playing(self):
        """Check if video is currently playing."""
        return self.is_playing_flag and (
            (self.omx_process and self.omx_process.poll() is None) or
            (self.vlc_process and self.vlc_process.poll() is None) or
            (self.playback_thread and self.playback_thread.is_alive())
        )
    
    def stop_video(self):
        """Stop currently playing video."""
        try:
            if self.currently_playing:
                print(f"Stopping video: {self.currently_playing}")
                
                # Stop omxplayer
                if self.omx_process:
                    try:
                        self.omx_process.terminate()
                        self.omx_process.wait(timeout=3)
                    except:
                        try:
                            self.omx_process.kill()
                        except:
                            pass
                    self.omx_process = None
                
                # Stop VLC/ffplay
                if self.vlc_process:
                    try:
                        self.vlc_process.terminate()
                        self.vlc_process.wait(timeout=3)
                    except:
                        try:
                            self.vlc_process.kill()
                        except:
                            pass
                    self.vlc_process = None
                
                # Wait for thread to finish
                if self.playback_thread and self.playback_thread.is_alive():
                    self.is_playing_flag = False
                    self.playback_thread.join(timeout=3)
                
                self.currently_playing = None
                # Restart black screen after stopping video
                self._start_black_screen()
            
            return True
            
        except Exception as e:
            print(f"ERROR: Error stopping video: {e}")
            return False
    
    def pause_video(self):
        """Pause video (limited support depending on player)."""
        print("Pause requested (support varies by player)")
        # Note: Pausing is complex with external players
        # This would require more sophisticated process communication
        return False
    
    def resume_video(self):
        """Resume video (limited support depending on player)."""
        print("Resume requested (support varies by player)")
        # Note: Resuming is complex with external players
        return False
    
    def list_video_files(self):
        """List all supported video files in the video directory."""
        try:
            if not os.path.exists(self.video_dir):
                print(f"ERROR: Video directory not found: {self.video_dir}")
                return []
            
            supported_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
            video_files = []
            
            for file in os.listdir(self.video_dir):
                _, ext = os.path.splitext(file.lower())
                if ext in supported_extensions:
                    video_files.append(file)
            
            return sorted(video_files)
            
        except Exception as e:
            print(f"ERROR: Error listing video files: {e}")
            return []
    
    def get_video_info(self, video_file):
        """Get basic info about a video file using ffprobe if available."""
        try:
            full_path = os.path.join(self.video_dir, video_file)
            if not os.path.exists(full_path):
                return None
            
            # Try to get video info using ffprobe
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', full_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                return info
            
        except Exception as e:
            print(f"WARNING: Could not get video info for {video_file}: {e}")
        
        return None
    
    def cleanup(self):
        """Clean up video resources."""
        try:
            self.stop_video()
            self._stop_black_screen()
            print("Video handler cleaned up")
        except Exception as e:
            print(f"ERROR: Error during video cleanup: {e}")


# Example usage and testing
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    video_dir = os.path.join(script_dir, "..", "videos")
    
    print(f"Video directory: {video_dir}")
    
    # Initialize video handler
    video_handler = VideoHandler(video_dir)
    
    # List available video files
    print("\nAvailable video files:")
    files = video_handler.list_video_files()
    if files:
        for i, file in enumerate(files, 1):
            print(f"  {i}. {file}")
            
            # Show video info if possible
            info = video_handler.get_video_info(file)
            if info and 'format' in info:
                duration = info['format'].get('duration', 'unknown')
                print(f"      Duration: {duration}s")
    else:
        print("  No video files found")
        print("  Add some video files (.mp4, .avi, .mkv, etc.) to test playback")
    
    # Interactive testing
    if files:
        print(f"\nInteractive test mode")
        print("Commands: play <number>, stop, list, quit")
        
        try:
            while True:
                cmd = input("\nvideo> ").strip().lower()
                
                if cmd in ['quit', 'exit', 'q']:
                    break
                elif cmd == 'list':
                    for i, file in enumerate(files, 1):
                        print(f"  {i}. {file}")
                elif cmd == 'stop':
                    video_handler.stop_video()
                elif cmd.startswith('play '):
                    try:
                        file_num = int(cmd.split()[1]) - 1
                        if 0 <= file_num < len(files):
                            video_handler.play_video(files[file_num])
                        else:
                            print("Invalid file number")
                    except (ValueError, IndexError):
                        print("Usage: play <number>")
                elif cmd == 'status':
                    if video_handler.is_playing():
                        print(f"Playing: {video_handler.currently_playing}")
                    else:
                        print("No video playing")
                else:
                    print("Commands: play <number>, stop, list, status, quit")
                    
        except KeyboardInterrupt:
            print("\nInterrupted")
    
    video_handler.cleanup()