# Museum Automation System Architecture

## System Overview

The automated museum system uses a distributed architecture with MQTT communication:

- **MQTT Broker**: Central communication hub
- **Raspberry Pi Controllers**: One per room, manages scene playback
- **ESP32 Devices**: Control hardware (lights, audio, motors)

## Communication Flow

1. User presses button in a room
2. Raspberry Pi loads the corresponding scene from JSON file
3. Raspberry Pi publishes MQTT messages according to scene timestamps
4. ESP32 devices receive messages and control physical hardware

## MQTT Topics Structure

Topics follow a hierarchical structure: `room_id/device_type`

Examples:
- `room1/light`
- `room1/audio`
- `room2/motor`

## Hardware Components

### Raspberry Pi
- Controls the scene playback
- Connects to network via Ethernet
- Communicates with button input
- Manages JSON scene files

### ESP32 Devices
- Connect to network via Ethernet (using ESP32-Ethernet-Kit)
- Subscribe to MQTT topics
- Control physical hardware components
