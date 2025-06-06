# MQTT Topics Structure

## Topic Convention

All topics follow the hierarchical pattern: `room_id/device_type[/action]`

- **room_id**: Unique identifier for each room (e.g., `room1`, `gallery`, `entrance`)
- **device_type**: Type of device or system (e.g., `light`, `audio`, `motor`, `display`)
- **action**: Optional sub-action for complex devices

## Standard Device Topics

### Light Control
- **Topic**: `roomX/light`
- **Messages**:
  - `ON`: Turn on all lights
  - `OFF`: Turn off all lights
  - `BLINK`: Execute blink sequence (5 blinks, then stay on)
  - `DIM:X`: Set brightness level (X = 0-100)
  - `COLOR:RRGGBB`: Set RGB color (hex format)
  - `STROBE`: Continuous strobe effect
  - `FADE:X`: Fade to brightness level X over 2 seconds

### Audio Control
- **Topic**: `roomX/audio`
- **Messages**:
  - `PLAY_WELCOME`: Play welcome audio file
  - `PLAY_INFO`: Play information/description audio
  - `PLAY_AMBIENT`: Start ambient background sounds
  - `PLAY:filename.mp3`: Play specific audio file
  - `STOP`: Stop current audio playback
  - `PAUSE`: Pause current playback
  - `RESUME`: Resume paused playback
  - `VOLUME:X`: Set volume level (X = 0-100)
  - `LOOP_ON`: Enable audio looping
  - `LOOP_OFF`: Disable audio looping

### Motor Control
- **Topic**: `roomX/motor`
- **Messages**:
  - `START`: Start motor at default speed
  - `STOP`: Stop motor movement
  - `SPEED:X`: Set motor speed (X = 0-255)
  - `FORWARD`: Rotate clockwise
  - `REVERSE`: Rotate counter-clockwise
  - `POSITION:X`: Move to specific position (X = degrees or steps)
  - `HOME`: Return to home position

### Display Control
- **Topic**: `roomX/display`
- **Messages**:
  - `ON`: Turn on display
  - `OFF`: Turn off display
  - `TEXT:Your message here`: Display text message
  - `IMAGE:filename.jpg`: Show specific image
  - `BRIGHTNESS:X`: Set display brightness (X = 0-100)
  - `CLEAR`: Clear display content
  - `SLIDESHOW:START`: Begin slideshow
  - `SLIDESHOW:STOP`: End slideshow

### Environmental Sensors
- **Topic**: `roomX/sensor`
- **Messages** (typically status reports):
  - `MOTION:DETECTED`: Motion sensor triggered
  - `MOTION:CLEAR`: No motion detected
  - `TEMP:X.X`: Temperature reading in Celsius
  - `HUMIDITY:X.X`: Humidity percentage
  - `LIGHT:X`: Light level (0-1023)

### Door/Access Control
- **Topic**: `roomX/door`
- **Messages**:
  - `UNLOCK`: Unlock electromagnetic lock
  - `LOCK`: Lock door
  - `STATUS`: Request door status
  - `OPEN`: Door opened (sensor feedback)
  - `CLOSED`: Door closed (sensor feedback)

## System-Wide Topics

### Status and Diagnostics
- **Topic**: `system/status`
- **Messages**:
  - `HEALTH_CHECK`: Request all devices to report status
  - `RESTART`: Restart all systems
  - `UPDATE_CONFIG`: Reload configuration files

### Scene Control
- **Topic**: `system/scene`
- **Messages**:
  - `START:scene_name`: Start specific scene across multiple rooms
  - `STOP_ALL`: Stop all active scenes
  - `EMERGENCY_STOP`: Emergency shutdown of all devices

## Room-Specific Examples

### Gallery Room (room1)
```
room1/light          # Main lighting control
room1/audio          # Audio narration system
room1/display        # Information displays
room1/sensor         # Motion and environmental sensors
```

### Interactive Workshop (room2) 
```
room2/light          # Workshop lighting
room2/motor          # Interactive mechanical displays
room2/audio          # Workshop audio guide
room2/door           # Access control
```

### Entrance Hall (entrance)
```
entrance/light       # Welcome lighting
entrance/audio       # Greeting audio
entrance/display     # Welcome screen and information
entrance/door        # Main entrance control
```

## Advanced Topic Patterns

### Multi-Zone Control
For rooms with multiple zones or device groups:
```
room1/light/zone1    # Zone-specific lighting
room1/light/zone2
room1/audio/left     # Stereo audio channels
room1/audio/right
```

### Device-Specific Control
For multiple devices of the same type:
```
room1/motor/carousel    # Specific motor names
room1/motor/lift
room1/display/main      # Multiple displays
room1/display/info
```

## Message Format Standards

### Status Messages
All devices should support status requests:
- **Request**: Send any message to `roomX/device/status`
- **Response**: Device publishes to `roomX/device/status/response`

### Error Reporting
Devices report errors to:
- **Topic**: `roomX/device/error`
- **Format**: `ERROR_CODE:Description`

### Heartbeat
Devices send periodic heartbeat:
- **Topic**: `roomX/device/heartbeat`
- **Message**: `ALIVE:timestamp`

## Quality of Service (QoS) Levels

- **QoS 0**: Status updates, sensor readings (fire-and-forget)
- **QoS 1**: Scene commands, device control (at least once delivery)
- **QoS 2**: Critical commands, safety systems (exactly once delivery)

## Retained Messages

The following message types should use retained messages:
- Device status updates
- Current device states (ON/OFF, current settings)
- Configuration parameters

## Security Considerations

### Access Control Topics
- Use authentication for critical controls
- Separate topics for different user privilege levels
- Consider topic-based permissions

### Naming Conventions

1. **Use lowercase**: All topic names should be lowercase
2. **Use underscores**: Separate words with underscores, not spaces
3. **Be descriptive**: Topic names should clearly indicate their purpose
4. **Avoid special characters**: Stick to alphanumeric characters and underscores
5. **Keep hierarchy shallow**: Limit nesting to 3-4 levels maximum

## Adding New Topics

When implementing new functionality:

1. **Follow naming convention**: Use the established `room_id/device_type[/action]` pattern
2. **Document thoroughly**: Add the topic and all messages to this documentation
3. **Consider message format**: Use consistent message formats across similar devices
4. **Test thoroughly**: Verify topic functionality before deployment
5. **Update all systems**: Ensure scene files and device firmware support new topics
6. **Consider backwards compatibility**: Don't break existing functionality

## Example Scene Integration

Scene files reference these topics with timestamps:
```json
[
  {
    "timestamp": 0,
    "topic": "room1/light",
    "message": "DIM:30"
  },
  {
    "timestamp": 2.0,
    "topic": "room1/audio",
    "message": "PLAY_WELCOME"
  },
  {
    "timestamp": 5.0,
    "topic": "room1/display",
    "message": "TEXT:Welcome to our museum!"
  }
]
```

## Troubleshooting

### Common Issues
- **No response**: Check device subscription to correct topic
- **Partial response**: Verify message format and case sensitivity  
- **Delayed response**: Check network connectivity and QoS settings
- **Repeated messages**: Ensure proper message acknowledgment

### Debugging Tools
- Use MQTT client tools to monitor topic traffic
- Check device logs for subscription confirmations
- Verify broker configuration and permissions