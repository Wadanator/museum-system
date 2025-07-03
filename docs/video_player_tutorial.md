# Video Playback Commands for SceneParser

This document outlines the video-related commands supported by the `SceneParser` and `VideoHandler` classes for controlling video playback via a JSON scene file.

## Supported Video Commands

These commands are used in the JSON `message` field when the `topic` ends with `/video` (e.g., `media/video`).

- **PLAY_VIDEO:filename.mp4**
  - Plays the specified `.mp4` video file from the `videos` directory.
  - Example: `"message": "PLAY_VIDEO:intro.mp4"`

- **STOP_VIDEO**
  - Stops the current video and displays a black screen (`black.png`).
  - Example: `"message": "STOP_VIDEO"`

- **PAUSE**
  - Pauses the current video (requires `pause_video` method, not implemented).
  - Example: `"message": "PAUSE"`

- **RESUME**
  - Resumes a paused video (requires `resume_video` method, not implemented).
  - Example: `"message": "RESUME"`

- **SEEK:seconds**
  - Seeks to a specific time in seconds (requires `seek_video` method, not implemented).
  - Example: `"message": "SEEK:10.5"`

- **Direct Filename (e.g., filename.mp4)**
  - Plays the specified `.mp4` video file directly.
  - Example: `"message": "scene1.mp4"`

## JSON Structure

The JSON scene file must be a list of actions with:
- **timestamp**: Time in seconds (float/integer) for action execution.
- **topic**: String ending with `/video` (e.g., `media/video`).
- **message**: One of the commands above.

### Example JSON

```json
[
    {"timestamp": 0.0, "topic": "media/video", "message": "PLAY_VIDEO:intro.mp4"},
    {"timestamp": 10.0, "topic": "media/video", "message": "STOP_VIDEO"},
    {"timestamp": 12.0, "topic": "media/video", "message": "scene1.mp4"}
]