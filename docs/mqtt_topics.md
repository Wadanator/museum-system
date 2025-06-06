# MQTT Topics Structure

## Topic Convention

All topics follow the pattern: `room_id/device_type`

## Standard Topics

### Light Control
- Topic: `roomX/light`
- Messages:
  - `ON`: Turn on all lights
  - `OFF`: Turn off all lights
  - `BLINK`: Blink lights sequence

### Audio Control
- Topic: `roomX/audio`
- Messages:
  - `PLAY_WELCOME`: Play welcome audio file
  - `PLAY_INFO`: Play information audio file
  - `STOP`: Stop audio playback

### Motor Control
- Topic: `roomX/motor`
- Messages:
  - `START`: Start motor movement
  - `STOP`: Stop motor movement
  - `SPEED:X`: Set motor speed (where X is a value)

## Room-Specific Examples

### Room 1
- `room1/light`
- `room1/audio`

### Room 2
- `room2/light`
- `room2/motor`

## Adding New Topics

When adding new functionality:
1. Follow the naming convention
2. Document the topic and messages
3. Ensure all devices are configured for the new topics
