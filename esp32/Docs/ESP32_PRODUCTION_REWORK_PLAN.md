# ESP32 Production Rework Plan

This document is a handoff brief for a future full rework of the ESP32
ArduinoIDE firmware modules. It is intentionally written as implementation
guidance, not as a copy of any coding standard.

## Required AI Context

When a new AI session or external reviewer works on this rework, provide the
standards documents again. Do not assume the AI already has access to them.

Required references:

- `esp32/Docs/barr_c_coding_standard_2018.pdf`
- `esp32/Docs/Google_C++_Style_Guide.pdf`

Use the PDFs as style and safety guidance. Do not claim full MISRA, Barr-C, or
Google C++ compliance unless the work also includes static analysis, a rule
checklist, and a documented deviation report for Arduino/ESP32 APIs.

## General Production Goals

- Keep the firmware modular, configurable, and easy to extend.
- Keep existing behavior as the default migration target.
- Avoid hard-coded room names, MQTT broker addresses, device counts, and topic
  names outside configuration modules.
- Make every external command pass through a parser and validator before it can
  affect hardware.
- Return truthful MQTT feedback. Publish `OK` only after the requested command
  has been accepted and the relevant software/hardware operation has succeeded.
- Prefer fixed-size buffers, explicit bounds, and deterministic state machines
  over dynamic allocation in runtime paths.
- Use clear enums and result codes instead of magic strings, magic chars, or
  bare booleans where invalid states are possible.
- Keep safety behavior centralized and documented.

## Recommended Module Layout

Each firmware should be split into small modules with clear ownership:

- `app_controller`: setup order, loop orchestration, and system state.
- `config`: room, MQTT, transport, device, timing, watchdog, and OTA settings.
- `mqtt_transport`: MQTT connection, subscriptions, publish helpers, and LWT.
- `command_parser`: payload parsing and validation only.
- `command_router`: map validated commands to device operations.
- `motor_driver` or `relay_driver`: hardware writes and hardware state.
- `safety_manager`: MQTT loss, inactivity timeout, STOP, and OTA-safe state.
- `ota_manager`: OTA lifecycle and OTA-safe output handling.
- `watchdog_manager`: watchdog init and service.
- `diagnostics`: debug output, status publish data, and error counters.

The parser should not directly manipulate hardware. Hardware modules should not
parse MQTT payloads. This separation makes the firmware testable and easier to
extend.

## Motors Rework Scope

Target module:

- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS`

This rework applies to the DC motor firmware only.

### Motors Configuration Goals

The motor firmware should be fully configuration-driven:

- Room namespace can be changed in one place, for example from `room1/` to
  another room prefix.
- MQTT broker host or IP can be changed in config.
- MQTT client ID can be changed in config.
- Any motor name can be changed in config.
- More motors can be added by appending configuration entries.
- Motor pins, enable pins, default direction, speed limits, and ramp limits are
  per-motor config values.

Recommended configuration shape:

```cpp
struct MotorConfig {
  const char* name;
  uint8_t pwmLeftPin;
  uint8_t pwmRightPin;
  uint8_t enablePin;
  uint8_t minSpeedPercent;
  uint8_t maxSpeedPercent;
  unsigned long maxRampMs;
};

extern const char* ROOM_TOPIC_PREFIX;
extern const char* MQTT_BROKER_HOST;
extern const MotorConfig MOTOR_CONFIGS[];
extern const size_t MOTOR_COUNT;
```

The default configuration should preserve the current topics:

- `room1/motor1`
- `room1/motor2`
- `room1/STOP`

Adding `motor3` should not require copy-pasting `controlMotor3()`. The control
path should operate on a motor index or motor handle resolved from the
configuration table.

### Motors Command Interface

Supported payloads should remain compatible by default:

- `ON:<speed>:<direction>`
- `ON:<speed>:<direction>:<rampTime>`
- `OFF`
- `SPEED:<value>`
- `DIR:<value>`

The command parser must validate:

- Payload length.
- Command name.
- Speed range.
- Direction value, allowing only the configured direction values such as `L`
  and `R`.
- Ramp time range.
- Extra separators or malformed fields.

Invalid commands must return `ERROR` and must not alter motor state.

### Motors Safety Goals

- Direction reversal must always pass through zero speed before applying the
  requested direction.
- `OFF` should result in a deterministic off or idle state after the smooth
  stop completes.
- `STOP` should immediately disable all motor drivers.
- MQTT loss should de-energize all motors.
- Inactivity timeout should de-energize all motors.
- OTA start should de-energize all motors before flash writes.

### Motors Test Targets

At minimum, test the command parser independently from Arduino hardware:

- Valid `ON`, `OFF`, `SPEED`, and `DIR` payloads.
- Missing fields.
- Non-numeric speed.
- Out-of-range speed.
- Invalid direction.
- Negative or oversized ramp time.
- Oversized MQTT payload.
- Topic prefix mismatch.
- Unknown motor name.

## LAN Relay Rework Scope

Target module:

- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY`

This rework applies to the Waveshare LAN relay firmware. LAN remains the
primary transport. WiFi fallback may remain as a backup transport if desired.

### Relay Configuration Goals

The relay firmware should be fully configuration-driven:

- Room namespace can be changed in one place.
- MQTT broker host or IP can be changed in config.
- MQTT client ID can be changed in config.
- Relay names can be changed in config.
- More relays can be added if the target hardware supports them.
- Relay inversion and auto-off time are per-relay config values.
- Effect groups are configured without hard-coded topic handling.

Recommended configuration shape:

```cpp
struct RelayConfig {
  const char* name;
  uint8_t expanderBit;
  bool inverted;
  unsigned long autoOffMs;
};

struct EffectGroupConfig {
  const char* name;
  const char* relayNames[MAX_RELAYS_PER_EFFECT];
  unsigned long minOnMs;
  unsigned long maxOnMs;
  unsigned long minOffMs;
  unsigned long maxOffMs;
};
```

The default configuration should preserve the current topics:

- `room1/<relay_name>`
- `room1/effects/<effect_group>`
- `room1/STOP`

### Relay ACK And Hardware Result Goals

The relay firmware should publish truthful feedback:

- I2C writes to the expander should return a result code.
- MQTT `OK` should be published only after the expander write succeeds.
- MQTT `ERROR` should be published when command parsing, device lookup, or I2C
  communication fails.
- Optional readback may be added if the expander and library support it.

This does not prove the mechanical relay contact moved, but it does prove the
firmware successfully completed its software-side hardware write.

### Relay Safety Goals

- `STOP` should immediately clear all relay outputs and stop effects.
- MQTT loss should de-energize relay outputs after the configured grace period.
- Inactivity timeout should de-energize relay outputs.
- OTA start should de-energize all relay outputs before flash writes.
- Effect timing should enforce relay-safe minimum pulse and pause times.
- I2C errors should be counted and surfaced in diagnostics.

### Relay Test Targets

At minimum, test relay command parsing, safety behavior, and I2C result
handling:

- Valid relay `ON`, `OFF`, `1`, and `0` payloads.
- Invalid relay payloads.
- Unknown relay name.
- Valid effect group start and stop commands.
- Unknown effect group name.
- Invalid effect payload.
- Oversized MQTT payload.
- Topic prefix mismatch.
- `room1/STOP` clears all relays and stops all effects.
- I2C expander write success returns MQTT `OK`.
- I2C expander write failure returns MQTT `ERROR`.
- Auto-off with `autoOffMs = 0` never auto-disables the relay.
- Auto-off with a configured timeout disables the relay after the timeout.
- Effect-controlled relays are not disabled by the normal auto-off path.
- MQTT loss reaches the configured safe output state.
- OTA start reaches the configured safe output state before flash writes.

## Style And Compliance Checklist

For both firmware modules:

- Use clear module boundaries and header interfaces.
- Keep config data in config files, not scattered in logic.
- Use explicit constants for buffer sizes, timing values, limits, and retry
  counts.
- Use enums for command types, device states, direction states, and result
  codes.
- Avoid `String` in hot runtime paths where fixed buffers are practical.
- Check return values from hardware and communication APIs.
- Avoid silent truncation in `snprintf`.
- Keep comments useful: describe intent, safety behavior, constraints, or
  non-obvious hardware details.
- Avoid comments that describe obvious syntax or development history.
- Keep all user-visible and diagnostic text in English.
- Keep a deviation log for Arduino/ESP32 APIs that cannot satisfy stricter
  coding-standard rules.

## Deviation Log Template

Use a deviation log whenever the rework intentionally keeps code that does not
fully match the selected style or safety guidance. This is expected for some
Arduino/ESP32 APIs.

Recommended entry format:

```text
Deviation ID: DEV-001
Module: wifi_manager
Reference: Barr-C:2018 / Google C++ Style Guide / local rule
Rule or guidance: Avoid dynamic allocation in runtime paths.
Deviation: WiFi.begin() and the Arduino WiFi stack may allocate internally.
Reason: The firmware depends on the Arduino WiFi API and no practical static
        alternative is available in this project.
Risk: Heap use may occur during connection setup or reconnect.
Mitigation: Call during setup/reconnect only, avoid repeated allocation in
            command hot paths, monitor reconnect behavior during soak testing.
Verification: Long-duration WiFi reconnect test and status monitoring.
Approval: Reviewer name and date.
```

Every deviation should explain the rule, the reason, the risk, the mitigation,
and the verification method. A deviation is not a workaround note; it is a
controlled engineering decision.

## Suggested Acceptance Criteria

- Existing MQTT topics work with the default configuration.
- Room prefix can be changed without editing parser or driver code.
- MQTT broker can be changed without editing parser or driver code.
- Motors can be added by extending `MOTOR_CONFIGS[]`.
- Relay names can be changed by editing `RELAY_CONFIGS[]`.
- Invalid commands return `ERROR` and do not affect hardware state.
- Hardware write failures return `ERROR`.
- STOP, MQTT loss, inactivity timeout, and OTA start always reach a safe output
  state.
- Parser tests pass on a desktop build or host-side test harness.
- Static analysis warnings are reviewed and either fixed or documented.
