# ESP32 LAN MQTT Window Cover Controller

Firmware variant for the Waveshare ESP32-S3-ETH-8DI-8RO / PoE module plus an
external 4-channel PWM Modbus RTU module. It is derived from
`esp32_mqtt_controller_RELAY`, but the relay/effects use case has been removed
and replaced with a two-motor design-window controller.

## What This Controls

- 2 active DC motors for a design window / cover mechanism.
- 4 software motor slots in `config.cpp`; slots 3 and 4 are disabled now.
- 4 active PWM Modbus channels total: two directions per active motor.
- 4 active end-stop inputs total: OPEN and CLOSED stop for each active motor.
- MQTT commands from the Raspberry Pi museum system.

## Kept From The LAN Relay Firmware

- W5500 LAN as primary transport.
- WiFi fallback when LAN is unavailable.
- MQTT reconnect and retained online/offline status.
- OTA updates via ArduinoOTA.
- Watchdog timer.
- Status LED behavior.
- Modular files: config, hardware, PWM driver, MQTT, WiFi, OTA, WDT, diagnostics.

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

| Motor slot | Enabled | OPEN PWM | CLOSE PWM | OPEN end-stop | CLOSED end-stop | MQTT topic |
|---|---|---:|---:|---:|---:|---|
| 1 | yes | CH1 / register `0x0000` | CH2 / register `0x0001` | DI1 / GPIO4 | DI2 / GPIO5 | `room1/cover/1` |
| 2 | yes | CH3 / register `0x0002` | CH4 / register `0x0003` | DI3 / GPIO6 | DI4 / GPIO7 | `room1/cover/2` |
| 3 | no | future CH5 | future CH6 | DI5 / GPIO8 | DI6 / GPIO9 | `room1/cover/3` |
| 4 | no | future CH7 | future CH8 | DI7 / GPIO10 | DI8 / GPIO11 | `room1/cover/4` |

The default PWM duty is `800` on a `0..1000` scale. Confirm the exact register
map and duty scale against the specific PWM module manual before connecting real
motors. These values are isolated in `config.cpp` as `PWM_REGISTER_BASE`,
`PWM_CHANNEL_COUNT`, `PWM_DUTY_MAX`, and per-cover `pwmDuty`.

With the current two-PWM-channels-per-motor scheme, four active motors need
eight PWM outputs. That can be a larger PWM module or another explicit hardware
extension; the current 4-channel module is fully used by the two active motors.

The default end-stop logic expects NC wiring (`endstopActiveLow = true`). If the
physical wiring is NO or the DI module reports active-high, change the relevant
entries in `config.cpp`.

## MQTT Interface

Broker defaults to `192.168.0.127`, base topic defaults to `room1/`.

Subscribed command topics:

- `room1/cover/1`
- `room1/cover/2`
- `room1/STOP`
- `room1/system/heartbeat`

Disabled slots `cover/3` and `cover/4` are not subscribed until their
`enabled` flag is changed to `true` and enough PWM channels are configured.

Cover payloads:

- `OPEN`
- `CLOSE`
- `STOP`

Feedback:

- `<command_topic>/feedback -> OK`
- `<command_topic>/feedback -> ERROR`
- `<command_topic>/feedback -> ERROR:ENDSTOP`
- `<command_topic>/feedback -> ERROR:TIMEOUT`
- `<command_topic>/feedback -> ERROR:HEARTBEAT`
- `<command_topic>/feedback -> ERROR:HARDWARE`

State topics:

- `room1/cover/N/state -> OPENING`
- `room1/cover/N/state -> CLOSING`
- `room1/cover/N/state -> OPEN`
- `room1/cover/N/state -> CLOSED`
- `room1/cover/N/state -> STOPPED`
- `room1/cover/N/state -> UNKNOWN`
- `room1/cover/N/state -> ERROR`

Status topic:

- `devices/Window_Covers_Ctrl/status -> online/offline`

## Safety Behavior

- The firmware never commands both PWM directions for the same motor at the same
  time.
- Before a direction receives non-zero duty, the opposite channel is written to
  zero over Modbus.
- Direction changes stop the motor first and wait `DIRECTION_CHANGE_DEADTIME_MS`.
- End-stops are checked before movement and every `ENDSTOP_POLL_INTERVAL_MS`
  during movement.
- Reaching an end-stop immediately writes both channels for that motor to zero.
- `maxMoveMs` stops a motor if it runs too long without reaching an end-stop.
- `room1/STOP`, MQTT loss, heartbeat timeout, inactivity timeout, and OTA start
  stop all motors.
- MQTT `OK` is published only after the command has been accepted and the
  relevant Modbus write path returns success.

## Arduino IDE Requirements

- ESP32 Arduino core 3.x or newer.
- Board: `ESP32S3 Dev Module`.
- Libraries used by this firmware: `PubSubClient`, `ArduinoOTA`, `ModbusMaster`,
  ESP32 `Network`/`ETH` support.

## Standards Notes

This is written in the style of `esp32/Docs/ESP32_PRODUCTION_REWORK_PLAN.md`:
configuration is centralized, command handling returns explicit result strings,
and safety writes are centralized in the hardware/PWM layer. It is not claimed
to be MISRA/Barr-C/Google-C++ compliant until static analysis, a rule checklist,
and a deviation report are completed.
