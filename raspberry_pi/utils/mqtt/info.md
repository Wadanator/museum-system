# MQTT Module Documentation

This directory contains the refactored MQTT functionality for the museum controller system, split into specialized modules with clear separation of responsibilities.

## Directory Structure

```
utils/mqtt/
├── __init__.py                    # Module initialization and exports
├── mqtt_client.py                 # Core MQTT connection management
├── mqtt_message_handler.py        # ESP32 status receiver + message router
├── mqtt_feedback_tracker.py       # Scene command feedback tracking
├── mqtt_device_registry.py        # ESP32 device registry
└── info.md                        # This documentation file
```

## Module Overview

### mqtt_client.py
**Purpose**: Core MQTT communication layer  
**USE**: Connects to your MQTT broker (192.168.0.127:1883) and sends/receives all MQTT messages

**Responsibilities**:
- Establishing and maintaining MQTT broker connections
- Publishing scene commands to ESP32 devices
- Handling connection retry logic and timeouts
- Managing connection state and callbacks
- Subscribe to device status topics

**Key Methods**:
- `connect()` - Connect to MQTT broker at 192.168.0.127
- `publish()` - Send scene commands like `room1/light = "ON"`
- `subscribe()` - Subscribe to `devices/+/status` and `+/status`  
- `set_handlers()` - Inject message processor, feedback tracker, device registry
- `manage_connection_health()` - Monitor broker connection

**USE EXAMPLE**: When scene runs, publishes `room1/steam = "ON"` to control ESP32

### mqtt_message_handler.py
**Purpose**: ESP32 status receiver and message router  
**USE**: Receives ALL incoming MQTT messages and decides what to do with them

**Responsibilities**:
- Receive status messages from ESP32 devices (`devices/esp32_01/status = "online"`)
- Receive scene feedback messages (`room1/status = "OK"`)
- Route ESP32 status to device registry
- Route feedback to feedback tracker
- Handle unknown message types

**Key Methods**:
- `handle_message()` - Main entry point for ALL incoming MQTT messages
- `set_handlers()` - Connect to feedback tracker and device registry
- `_is_device_status_message()` - Detect `devices/esp32_XX/status` messages
- `_is_feedback_message()` - Detect `room1/status` feedback messages

**USE EXAMPLE**: 
- ESP32 sends `devices/esp32_01/status = "online"` → routes to device registry
- ESP32 sends `room1/status = "OK"` after light command → routes to feedback tracker

### mqtt_feedback_tracker.py
**Purpose**: Scene command confirmation tracking  
**USE**: During scene execution, tracks if ESP32 devices confirm they received commands

**Responsibilities**:
- Monitor scene commands that need confirmation (not audio/video)
- Track pending confirmations with 1-second timeout
- Log successful confirmations (✅ Feedback OK) and timeouts (⏰ Feedback TIMEOUT)
- Only active during scene execution (disabled when idle)
- Correlate sent commands with received status messages

**Key Methods**:
- `enable_feedback_tracking()` - Start tracking when scene begins
- `disable_feedback_tracking()` - Stop tracking when scene ends
- `track_published_message()` - Register scene command for confirmation tracking
- `handle_feedback_message()` - Process `room1/status = "OK"` confirmations
- `_should_expect_feedback()` - Skip audio/video (handled locally by RPI)

**USE EXAMPLE**:
1. Scene starts → tracking enabled
2. Send `room1/light = "ON"` → expects `room1/status = "OK"`
3. ESP32 confirms → logs "✅ Feedback OK: room1/light (0.234s)"
4. Scene ends → tracking disabled

### mqtt_device_registry.py  
**Purpose**: ESP32 device connection registry  
**USE**: Keeps track of which ESP32 devices are online/offline for monitoring

**Responsibilities**:
- Track ESP32 connection status (online/offline)
- Log when ESP32 devices connect/disconnect
- Provide device status for web dashboard
- Store last-seen timestamps

**Key Methods**:
- `update_device_status()` - Update ESP32 status when `devices/esp32_XX/status` received
- `get_connected_devices()` - Get list of online ESP32s for web dashboard
- `get_all_devices()` - Get all ESP32s with their status  
- `clear_devices()` - Reset registry on system restart

**USE EXAMPLE**:
- ESP32_01 boots up → sends `devices/esp32_01/status = "online"` → logged as connected
- ESP32_01 loses power → sends `devices/esp32_01/status = "offline"` → logged as disconnected
- Web dashboard shows: "ESP32_01: Online, ESP32_02: Offline"

## Message Flow in Your Museum System

```
Your MQTT Broker (192.168.0.127:1883)
     ↕
mqtt_client.py (connects to broker)
     ↓ (ESP32 sends: devices/esp32_01/status = "online")  
     ↓ (ESP32 sends: room1/status = "OK")
mqtt_message_handler.py (message router)
     ├─→ mqtt_device_registry.py (tracks ESP32_01 = online)
     └─→ mqtt_feedback_tracker.py (logs scene command confirmed)
```

## Your MQTT Topic Patterns

### ESP32 Device Status Topics
**USE**: ESP32 devices announce when they come online/offline
- `devices/esp32_01/status = "online"` - ESP32_01 connected to WiFi  
- `devices/esp32_01/status = "offline"` - ESP32_01 lost connection
- `devices/esp32_02/status = "online"` - ESP32_02 connected

### Room Control Topics (Scene Commands)
**USE**: Your scenes send these commands to control room devices
- `room1/light = "ON"` - Turn on room1 lights via ESP32
- `room1/light = "OFF"` - Turn off room1 lights  
- `room1/motor = "START"` - Start room1 motor
- `room1/steam = "ON"` - Turn on steam effect

### Feedback Topics (Command Confirmations)  
**USE**: ESP32 devices send back confirmation that commands were received
- `room1/status = "OK"` - Command executed successfully
- `room1/status = "ERROR"` - Command failed
- `devices/esp32_01/status = "OK"` - Direct device confirmation

### Local Topics (No MQTT - Handled by RPI)
**USE**: Audio/Video played directly on Raspberry Pi, no ESP32 involved
- `room1/audio = "sound1.mp3"` - Play audio file locally
- `room1/video = "video1.mp4"` - Play video file locally

## Your Scene Execution Flow

**EXAMPLE**: Scene plays in room1

1. **Scene Starts**: 
   - `mqtt_feedback_tracker.enable_feedback_tracking()` - Start monitoring confirmations

2. **Scene Commands**:
   ```
   [0.0s] room1/light = "ON"     → ESP32_01 receives, sends back room1/status = "OK" 
   [2.5s] room1/audio = "bg.mp3" → RPI plays locally (no MQTT)
   [5.0s] room1/steam = "ON"     → ESP32_02 receives, sends back room1/status = "OK"
   [10.0s] room1/motor = "START" → ESP32_01 receives, sends back room1/status = "OK"
   ```

3. **Feedback Tracking**:
   ```
   ✅ Feedback OK: room1/light (0.234s)
   ✅ Feedback OK: room1/steam (0.156s) 
   ✅ Feedback OK: room1/motor (0.198s)
   ```

4. **Scene Ends**:
   - `mqtt_feedback_tracker.disable_feedback_tracking()` - Stop monitoring

## Integration Points in Your System

### With main.py (MuseumController)
```python
# Initialize MQTT system for your museum
self.mqtt_client = MQTTClient("192.168.0.127", 1883, f"rpi_room_{self.room_id}")
self.mqtt_feedback_tracker = MQTTFeedbackTracker()
self.mqtt_device_registry = MQTTDeviceRegistry() 
self.mqtt_message_handler = MQTTMessageHandler()

# Connect components
self.mqtt_message_handler.set_handlers(
    feedback_tracker=self.mqtt_feedback_tracker,  # Handle scene confirmations
    device_registry=self.mqtt_device_registry     # Track ESP32 connections
)
```

### With scene_parser.py (Scene Execution)
```python
# Scene starts
if mqtt_client.feedback_tracker:
    mqtt_client.feedback_tracker.enable_feedback_tracking()

# Execute scene actions
for action in scene_actions:
    if action["topic"].endswith("/audio"):
        self.audio_handler.play(action["message"])  # Local RPI
    elif action["topic"].endswith("/video"):  
        self.video_handler.play(action["message"])  # Local RPI
    else:
        mqtt_client.publish(action["topic"], action["message"])  # Send to ESP32

# Scene ends  
if mqtt_client.feedback_tracker:
    mqtt_client.feedback_tracker.disable_feedback_tracking()
```

### With web_dashboard.py (Device Monitoring)
```python
# Show ESP32 status on web dashboard
connected_devices = self.mqtt_device_registry.get_connected_devices()
# Returns: {"esp32_01": {"status": "online", "last_updated": 1234567890}}
```

## Error Handling in Your System

**Connection Failures**: If MQTT broker goes down
- Retries connection 5 times with 2s delays
- Continues running scenes in "simulation mode" (logs commands but doesn't send)
- Automatically reconnects when broker comes back online

**ESP32 Device Failures**: If ESP32 stops responding  
- Device registry marks as offline
- Feedback tracker logs timeouts: `⏰ Feedback TIMEOUT: room1/light (>1.000s)`
- Scene continues executing (doesn't stop for one failed device)

**Message Processing Errors**: If malformed messages received
- Logs error but continues processing other messages
- Protects system from crashing on bad data from ESP32

## Logging in Your System

Each module logs to specific logger names:
- `mqtt` - Connection events, publish/subscribe operations
- `mqtt_handler` - Message routing decisions  
- `mqtt_feedback` - Scene command confirmations and timeouts
- `mqtt_devices` - ESP32 connection changes

**Example Log Output During Scene**:
```
[INFO] mqtt - Publishing to room1/light: ON
[DEBUG] mqtt_feedback - 📤 Sent: room1/light -> expecting feedback on: room1/status  
[INFO] mqtt_feedback - ✅ Feedback OK: room1/light (0.234s)
[DEBUG] mqtt_devices - Device esp32_01 status: online
```

## Thread Safety for Your System

- **MQTT callbacks**: All ESP32 messages processed in MQTT thread
- **Feedback timeouts**: Background threads check for missing confirmations  
- **Scene execution**: Main thread sends commands, MQTT thread receives confirmations
- **Web dashboard**: Separate thread accessing device registry safely
- **Device registry**: Thread-safe updates when ESP32 status changes

**USE**: This means your scenes can run while web dashboard shows real-time ESP32 status without conflicts.