# ESP32 WiFi MQTT Motor Controller

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

- `room1/motor1` -> `ON:150:L`
- `room1/motor2` -> `ON:90:R:4000`
- `room1/motor1` -> `SPEED:200`
- `room1/motor2` -> `OFF`

The `direction` field uses `L` or `R`. The optional `rampTime` field is a
duration in milliseconds.

## Safety Behavior

- `room1/STOP` immediately disables both motor drivers through
  `turnOffHardware()`.
- Direction changes while running are completed through zero speed before the
  requested direction is applied.
- Motors are de-energized when MQTT is unavailable.
- `NO_COMMAND_TIMEOUT` provides the inactivity safety timeout.

## Configuration

The hardware and timing configuration is in `config.cpp`:

- WiFi credentials.
- MQTT broker and base topic.
- Motor driver pin mapping.
- PWM frequency and resolution.
- Smooth speed step and update interval.
- OTA hostname and password.
