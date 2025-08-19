# Utils Folder Structure

The `utils` folder contains helper scripts and tools used within the project. These scripts provide essential functions for logging management, MQTT communication, video and audio handling, system monitoring, button processing, and configuration management.  
Below is a description of each file in the `utils` folder and its purpose.

---

## Files in the `utils` Folder

### 1. mqtt_client.py
**Purpose:** Manage MQTT communication with the broker.  
**Description:** Defines the `MQTTClient` class, which handles connecting to the MQTT broker, sending and receiving messages, managing connected devices, and tracking feedback during scene execution. Supports automatic reconnection, error handling, and logging.  
**Key Features:**
- Connect to the MQTT broker with retry logic.  
- Publish messages to specific topics.  
- Track feedback for MQTT commands.  
- Monitor the state of connected devices.  

---

### 2. video_handler.py
**Purpose:** Manage video playback on Raspberry Pi.  
**Description:** The `VideoHandler` class controls video playback using the MPV player via IPC socket. Optimized for performance on Raspberry Pi, supports hardware acceleration, and manages a black image as the default idle state.  
**Key Features:**
- Start and stop video playback.  
- Handle commands such as pause, resume, and seek.  
- Monitor MPV process health and auto-restart on failure.  
- Manage black screen for idle state.  

---

### 3. system_monitor.py
**Purpose:** Monitor system health and MQTT connection.  
**Description:** The `SystemMonitor` class monitors system resources (CPU, memory, disk) and MQTT connection status. Provides periodic health checks and logs system statistics.  
**Key Features:**
- Perform system and MQTT health checks.  
- Log system statistics (memory, CPU, disk usage).  
- Notify readiness via `systemd-notify`.  
- Log system startup information.  

---

### 4. button_handler.py
**Purpose:** Manage hardware button input on Raspberry Pi.  
**Description:** The `ButtonHandler` class processes GPIO button input with debounce support to filter out noise. Uses polling to detect button presses and allows custom callback functions.  
**Key Features:**
- Initialize GPIO pin for button.  
- Detect button presses with debounce logic.  
- Trigger callback function on press.  
- Clean up GPIO resources on exit.  

---

### 5. logging_setup.py
**Purpose:** Configure and manage logging.  
**Description:** Provides functions for setting up a comprehensive logging system with console and file support. Creates main logs, warnings, errors, and daily rotating logs.  
**Key Features:**
- Support for multiple log formats (detailed, simple, JSON).  
- Colored console logging.  
- Rotate log files by size and time.  
- Global handling of uncaught exceptions.  
- Logging configuration via dictionary.  

---

### 6. audio_handler.py
**Purpose:** Manage audio playback on Raspberry Pi.  
**Description:** The `AudioHandler` class uses the Pygame library to play audio files through the 3.5 mm jack. Supports commands such as play, stop, pause, resume, and volume adjustment.  
**Key Features:**
- Play audio files (.wav, .mp3, .ogg).  
- Manage volume and playback commands (e.g., `PLAY:`, `VOLUME:`).  
- List available audio files in the directory.  
- Initialize audio system with 3.5 mm jack as default output.  

---

### 7. scene_parser.py
**Purpose:** Process and execute scenes defined in JSON files.  
**Description:** The `SceneParser` class loads and processes scenes from JSON files, which define timed actions for MQTT, audio, and video. Integrates with the MQTT client to track feedback and handle local commands for media.  
**Key Features:**
- Load and validate JSON scene files.  
- Execute actions based on timestamps.  
- Integrate with MQTT client for command execution and feedback tracking.  
- Manage scene progress and state.  

---

### 8. config_manager.py
**Purpose:** Load and manage system configuration.  
**Description:** The `ConfigManager` class loads configuration from a `config.ini` file and provides access to settings for MQTT, GPIO, logging, file paths, and other system parameters.  
**Key Features:**
- Load and validate configuration file.  
- Provide logging configuration (level, directories, format).  
- Access system settings such as MQTT broker, GPIO pins, and directories for scenes, audio, and video.  

---

## Summary
The `utils` folder is the core of the system, offering modular and reusable components for managing MQTT communication, media playback, system monitoring, input handling, and logging. Each file is designed to operate independently while integrating seamlessly with other parts of the system, creating a robust and flexible solution for managing museum installations.
