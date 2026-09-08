# ESP32 WiFi MQTT Motor Controller

This is the separate ESP-NOW motor copy. Start with
[the bridge guide](../../../../espnow/README.md), which overrides the legacy
transport description below. The default bridge profile accepts one configured
master and does not connect to MQTT or an AP. USB is the bridge maintenance path;
WiFi OTA belongs to legacy mode. The original sibling sketch is the rollback backup.

Firmware for controlling two bidirectional DC motors over MQTT. Each motor is
driven through independent left/right PWM outputs and a dedicated enable pin.

## MQTT Interface

Subscribed command topics:

- `room1/motor1`
- `room1/motor2`
- `room1/STOP`

Status topic:

- `devices/Room1_ESP_Motory/status`

Feedback topic format:

- `<command_topic>/feedback`

## Command Payloads

Motor topics accept the following payloads:

- `ON:<speed>:<direction>`
- `ON:<speed>:<direction>:<rampTime>`
- `OFF`
- `SPEED:<value>`
- `DIR:<value>`

Examples:

- `room1/motor1` -> `ON:80:L`
- `room1/motor2` -> `ON:90:R:4000`
- `room1/motor1` -> `SPEED:60`
- `room1/motor2` -> `OFF`

The `speed` field is clamped to `0..100`. The `direction` field uses `L` or
`R`. The optional `rampTime` field is a duration in milliseconds.

## Safety Behavior

- `room1/STOP` immediately disables both motor drivers through
  `turnOffHardware()`.
- Direction changes while running are completed through zero speed before the
  requested direction is applied.
- `OFF` cancels any pending direction change, decelerates to zero, then disables
  the motor driver's enable pin.
- Motors are de-energized when MQTT is unavailable.
- `NO_COMMAND_TIMEOUT` provides the inactivity safety timeout.

## Configuration

The hardware and timing configuration is in `config.cpp`:

- WiFi credentials.
- MQTT broker and base topic.
- Motor driver pin mapping.
- PWM frequency and resolution.
- Smooth speed step and update interval.
- WiFi/MQTT retry limits before a safety restart.
- OTA hostname and password.
