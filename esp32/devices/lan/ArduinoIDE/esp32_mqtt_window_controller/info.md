# ESP32 LAN MQTT Window Controller

Firmware for the Waveshare ESP32-S3-ETH-8DI-8RO / PoE module plus an external
4-channel PWM Modbus RTU module. It controls the left and right side of the
physical window over MQTT.

## What This Controls

- 2 active DC motor outputs: left side and right side of the window.
- 4 active PWM Modbus channels total: two directions per active side.
- Optional end-stop inputs: OPEN and CLOSED stop for each side.
- MQTT commands from the Raspberry Pi museum system.

## Hardware Mapping

Waveshare controller:

| Function | Pin |
|---|---:|
| RS485 TX | GPIO17 |
| RS485 RX | GPIO18 |
| DI1 | GPIO4 |
| DI2 | GPIO5 |
| DI3 | GPIO6 |
| DI4 | GPIO7 |
| RGB status LED | GPIO38 |

External 4-channel PWM Modbus RTU module:

| Window side | Enabled | OPEN PWM | CLOSE PWM | OPEN end-stop | CLOSED end-stop | MQTT topic |
|---|---|---:|---:|---:|---:|---|
| Left | yes | CH1 / duty register `0x0002` | CH2 / duty register `0x0005` | DI1 / GPIO4 | DI2 / GPIO5 | `room1/window/left` |
| Right | yes | CH3 / duty register `0x0008` | CH4 / duty register `0x000B` | DI3 / GPIO6 | DI4 / GPIO7 | `room1/window/right` |

Test defaults in `config.cpp`:

- `endstopsEnabled = false` for both active sides.
- `defaultSpeed = 30` percent.
- active profile: `WINDOW_PROFILE_TEST_NO_ENDSTOPS_SAFE`.
- `maxMoveMs = 10000` ms.

For production with real mechanics, switch to `WINDOW_PROFILE_PROD_WITH_ENDSTOPS`
after wiring the end-stops and keep `maxMoveMs` based on measured travel time
plus a safety margin. Do not run with an unlimited movement time.

## MQTT Interface

Broker defaults to `TechMuzeumRoom1.local`, base topic defaults to `room1/`.

Subscribed command topics:

- `room1/window/left`
- `room1/window/right`
- `room1/window/STOP`
- `room1/STOP`

Payloads:

- `OPEN`
- `OPEN:<speed>`
- `CLOSE`
- `CLOSE:<speed>`
- `SPEED:<speed>`
- `STOP`
- `OFF` (alias for `STOP`)

`speed` is clamped to `0..100` and converted to the PWM module duty scale
`0..10000`.

Feedback:

- `<command_topic>/feedback -> OK`
- `<command_topic>/feedback -> ERROR`
- `<command_topic>/feedback -> ERROR:INVALID_SPEED`
- `<command_topic>/feedback -> ERROR:ENDSTOP`
- `<command_topic>/feedback -> ERROR:TIMEOUT`
- `<command_topic>/feedback -> ERROR:HARDWARE`

State topics publish retained JSON:

```json
{"state":"OPENING","direction":"OPENING","speed":30,"node_id":"Room1_Window_Ctrl","source":"command","ts_ms":12345}
```

Status topic:

- `devices/Room1_Window_Ctrl/status -> online/offline`

The firmware does not require a separate Raspberry Pi heartbeat. If the broker
or RPi-side MQTT path disappears, the ESP detects MQTT loss and stops active PWM
after `NETWORK_FAILOVER_GRACE`.

## Safety Behavior

- The firmware never commands both PWM directions for the same side at the same
  time.
- Before a direction receives non-zero duty, the opposite channel is written to
  zero over Modbus.
- Direction changes schedule a non-blocking `DIRECTION_CHANGE_DEADTIME_MS` dead-time before enabling the requested PWM channel.
- End-stops are optional in test mode and should be enabled for production.
- Reaching an enabled end-stop immediately writes both channels for that side to zero.
- `maxMoveMs` stops a side if it runs too long without reaching an end-stop. The ESP task watchdog is configured to 1.5x the active `maxMoveMs`.
- `room1/STOP`, `room1/window/STOP`, MQTT loss, inactivity timeout, and OTA
  start stop all window outputs.
- MQTT `OK` is published only after the command has been accepted and the
  relevant Modbus write path returns success.

## Arduino IDE Requirements

- ESP32 Arduino core 3.x or newer.
- Board: `ESP32S3 Dev Module`.
- Libraries used by this firmware: `PubSubClient`, `ArduinoOTA`, `ModbusMaster`,
  ESP32 `Network`/`ETH` support.
