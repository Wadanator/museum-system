# Automated Museum with MQTT Control

This project implements an interactive museum system where each room features an automated guide system driven by timed scenes and MQTT-based hardware control, running primarily on Raspberry Pi with ESP32 devices for managing various hardware components.

---

## Overview

- Each room has a physical button to trigger predefined multimedia scenes  
- Scenes are defined in JSON files, orchestrating audio, video, and hardware actions  
- MQTT messaging enables communication between Raspberry Pi and ESP32 devices  
- ESP32 devices control diverse hardware like lights, motors, steam, relays, and more at specific times  
- A web dashboard provides real-time monitoring, scene management, and system control  
- A watchdog service ensures reliable operation with automatic restarts if needed  

---

## Key Features

### Scene-Based Automation  
JSON-defined scenes synchronize:  
- **Audio**: WAV, MP3, OGG  
- **Video**: MP4 (via MPV)  
- **Hardware Actions**: Lights, motors, steam, relays  

### MQTT Communication  
- Sends commands via MQTT to ESP32 devices for precise, timed control  
- Fallback to localhost broker if the primary fails  

### Button Triggers  
- Physical buttons initiate scenes for interactive visitor experiences  

### Web Dashboard  
- Flask-based interface with SocketIO  
- Real-time viewing of logs, scene management, and system status  

### System Reliability  
- Watchdog monitors CPU/memory usage  
- Automatically restarts the system if thresholds are exceeded  

### Logging  
- Multi-level logs: DEBUG, INFO, WARNING, ERROR, CRITICAL  
- Logs exportable through the dashboard  

---

## Directory Structure

```text
logs/               System logs including:
                      - museum-daily.log
                      - museum-errors.log
                      - museum-warnings.log
                      - museum.log

raspberry_pi/       Raspberry Pi code and resources  
audio/              Audio files (WAV, MP3, OGG) for exhibit playback  
config/             Configuration files  
scenes/             JSON files defining timed scenes for each room  
service/            Service-related files  
tools/              Utility scripts for testing and development  
utils/              Utility modules  
videos/             Video files (MP4) for exhibit playback  
Web/                Web interface files  

dashboard.html      Web dashboard HTML template  
web_dashboard.py    Web dashboard Python script  

audio_handler.py            Audio control module  s
config_manager.py           Configuration management module  
logging_setup.py            Logging setup module  
mqtt_client.py              MQTT client module  
scene_parser.py             Scene parsing module  
system_monitor.py           System monitoring module  
video_handler.py            Video control module  

main.py                     Main controller script  
setup_museum_service.sh     Shell script for setting up museum service  
watchdog.py                 Watchdog script for system monitoring and restarts  
