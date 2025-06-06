# Museum System - Audio Playing Tutorial

## Table of Contents
1. [Overview](#overview)
2. [Supported Audio Formats](#supported-audio-formats)
3. [Audio Directory Setup](#audio-directory-setup)
4. [Audio Commands in Scenes](#audio-commands-in-scenes)
5. [Scene File Examples](#scene-file-examples)
6. [Interactive Audio Testing](#interactive-audio-testing)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Overview

The Museum System supports dynamic audio playback with multiple file formats, volume control, and precise timing. Audio files are played through the enhanced AudioHandler which integrates with pygame for reliable cross-platform audio support.

## Supported Audio Formats

✅ **Supported Formats:**
- `.wav` - Uncompressed audio (best quality, larger files)
- `.mp3` - Compressed audio (good quality, smaller files)
- `.ogg` - Open-source compressed audio (good quality, smaller files)

❌ **Not Supported:**
- `.flac`, `.aac`, `.wma`, `.m4a`

## Audio Directory Setup

### 1. Create Audio Directory Structure
```
raspberry_pi/
├── audio/                    # Main audio directory
│   ├── welcome.mp3          # Welcome message
│   ├── background_music.wav # Background ambience
│   ├── narration.ogg        # Story narration
│   ├── sound_effects/       # Subfolder for effects
│   │   ├── thunder.wav
│   │   └── footsteps.mp3
│   └── languages/           # Multi-language support
│       ├── en/
│       │   └── intro.mp3
│       └── sk/
│           └── intro.mp3
```

### 2. File Naming Conventions
- Use descriptive names: `welcome_message.mp3` instead of `audio1.mp3`
- No spaces in filenames: `background_music.wav` not `background music.wav`
- Use lowercase: `narration.ogg` not `NARRATION.OGG`
- Include duration in name if helpful: `intro_30sec.mp3`

## Audio Commands in Scenes

### Basic Audio Commands

| Command Format | Description | Example |
|----------------|-------------|---------|
| `"filename.ext"` | Play file with default volume (0.7) | `"welcome.mp3"` |
| `"PLAY:filename.ext:volume"` | Play file with specific volume (0.0-1.0) | `"PLAY:music.wav:0.3"` |
| `"STOP"` | Stop currently playing audio | `"STOP"` |
| `"PAUSE"` | Pause current audio | `"PAUSE"` |
| `"RESUME"` | Resume paused audio | `"RESUME"` |
| `"VOLUME:level"` | Change volume of current audio | `"VOLUME:0.8"` |
| `"PLAY_NAME"` | Legacy format (searches for name.wav/mp3/ogg) | `"PLAY_WELCOME"` |

### Volume Levels Guide
- `1.0` - Maximum volume (100%)
- `0.8` - Loud (80%) - Good for main narration
- `0.5` - Medium (50%) - Good for dialogue
- `0.3` - Quiet (30%) - Good for background music
- `0.1` - Very quiet (10%) - Subtle ambient sounds
- `0.0` - Muted (0%)

## Scene File Examples

### Example 1: Simple Welcome Scene
```json
[
  {
    "timestamp": 0,
    "topic": "room1/light",
    "message": "ON"
  },
  {
    "timestamp": 1.0,
    "topic": "room1/audio",
    "message": "welcome.mp3"
  },
  {
    "timestamp": 8.0,
    "topic": "room1/audio",
    "message": "STOP"
  },
  {
    "timestamp": 10.0,
    "topic": "room1/light",
    "message": "OFF"
  }
]
```

### Example 2: Complex Audio Scene with Background Music
```json
[
  {
    "timestamp": 0,
    "topic": "room1/audio",
    "message": "PLAY:background_music.wav:0.2"
  },
  {
    "timestamp": 2.0,
    "topic": "room1/audio",
    "message": "PLAY:welcome_message.mp3:0.8"
  },
  {
    "timestamp": 8.0,
    "topic": "room1/audio",
    "message": "VOLUME:0.1"
  },
  {
    "timestamp": 10.0,
    "topic": "room1/audio",
    "message": "PLAY:main_narration.ogg:0.9"
  },
  {
    "timestamp": 25.0,
    "topic": "room1/audio",
    "message": "PLAY:dramatic_sound.wav:1.0"
  },
  {
    "timestamp": 30.0,
    "topic": "room1/audio",
    "message": "STOP"
  }
]
```

### Example 3: Multi-Language Scene
```json
[
  {
    "timestamp": 0,
    "topic": "room1/audio",
    "message": "PLAY:languages/en/intro.mp3:0.8"
  },
  {
    "timestamp": 15.0,
    "topic": "room1/audio",
    "message": "PAUSE"
  },
  {
    "timestamp": 17.0,
    "topic": "room1/audio",
    "message": "PLAY:languages/sk/intro.mp3:0.8"
  },
  {
    "timestamp": 32.0,
    "topic": "room1/audio",
    "message": "STOP"
  }
]
```

## Interactive Audio Testing

### 1. Start the Museum Controller
```bash
cd raspberry_pi
python3 main.py
```

### 2. Enter Interactive Mode
Press `Ctrl+C` to enter interactive mode

### 3. Available Audio Commands
```
> audio                    # List all available audio files
> play welcome.mp3         # Test specific audio file
> stop                     # Stop current audio
> status                   # Check audio status
```

### 4. Testing Scene Files
```
> scene                    # Run default scene
> button                   # Simulate button press
```

## Troubleshooting

### Common Issues and Solutions

#### 🔇 No Audio Playing
**Problem**: Audio commands execute but no sound
**Solutions:**
1. Check if audio files exist in the `audio/` directory
2. Verify file format is supported (.wav, .mp3, .ogg)
3. Test system audio: `speaker-test -t wav -c 2`
4. Check volume: `alsamixer`

#### 📁 File Not Found Errors
**Problem**: `Audio file not found: /path/to/file.mp3`
**Solutions:**
1. Verify filename spelling and extension
2. Check file is in correct audio directory
3. Use `> audio` command to list available files
4. Ensure no spaces or special characters in filename

#### 🔊 Volume Too Low/High
**Problem**: Audio too quiet or too loud
**Solutions:**
1. Adjust volume in scene file: `"PLAY:file.mp3:0.5"`
2. Use `"VOLUME:0.8"` command to change during playback
3. Check system volume settings

#### ⏯️ Audio Doesn't Stop
**Problem**: Audio continues playing after scene ends
**Solutions:**
1. Add `"STOP"` command at end of scene
2. Use interactive mode: `> stop`
3. Restart the controller

### Debug Commands
```bash
# Check audio system
aplay -l                   # List audio devices
speaker-test -t wav -c 2   # Test speakers

# Check file formats
file audio/*.mp3           # Verify file types
ls -la audio/             # List audio files

# Monitor MQTT for audio commands
mosquitto_sub -h localhost -t "room1/audio" -v
```

## Best Practices

### 📁 File Organization
- Keep audio files organized in subfolders
- Use consistent naming conventions
- Test all files before creating scenes
- Keep backup copies of important audio files

### 🎵 Audio Quality
- Use appropriate bitrates: 128kbps for speech, 192kbps+ for music
- Normalize audio levels to avoid volume jumps
- Test on actual hardware (Pi speakers/headphones)
- Consider file size vs. quality trade-offs

### ⏱️ Timing and Synchronization
- Allow buffer time between audio commands (0.5s minimum)
- Test scene timing with actual audio file durations
- Use `STOP` before starting new audio to avoid overlap
- Consider fade-in/fade-out effects in audio files

### 🔧 Scene Design
```json
{
  "timestamp": 5.0,
  "topic": "room1/audio",
  "message": "STOP"
},
{
  "timestamp": 5.5,
  "topic": "room1/audio", 
  "message": "PLAY:next_audio.mp3:0.7"
}
```

### 📊 Performance Tips
- Use compressed formats (.mp3, .ogg) for longer files
- Use .wav for short sound effects
- Preload critical audio files
- Monitor system resources during playback

### 🌍 Multi-Language Support
```
audio/
├── en/
│   ├── welcome.mp3
│   └── narration.mp3
└── sk/
    ├── welcome.mp3
    └── narration.mp3
```

Scene command: `"PLAY:en/welcome.mp3:0.8"`

---

## Quick Reference Card

| Task | Command | Example |
|------|---------|---------|
| Play audio | `"filename.ext"` | `"welcome.mp3"` |
| Play with volume | `"PLAY:file:volume"` | `"PLAY:music.wav:0.5"` |
| Stop audio | `"STOP"` | `"STOP"` |
| Change volume | `"VOLUME:level"` | `"VOLUME:0.8"` |
| List files | `> audio` | In interactive mode |
| Test file | `> play filename` | In interactive mode |

**Remember**: Always test your scenes thoroughly before deploying to ensure smooth audio playback and proper timing!