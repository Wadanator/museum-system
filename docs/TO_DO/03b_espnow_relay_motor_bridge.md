# TODO: ESP-NOW relay-to-motor bridge

Date: 2026-09-04

## Latest update - 2026-09-08: relay WiFi fallback

DONE (source): user requested LAN-to-WiFi fallback on the relay. The relay copy
now defaults to `RELAY_WIFI_FALLBACK_ENABLED=1`; the earlier LAN-only rollout
restriction below is SUPERSEDED. Motor runtime authority remains ESP-NOW only.

DONE (source): initialize ESP-NOW before AP connection; bounded 8 s WiFi attempts
with backoff; validate AP channel before accepting fallback MQTT; disconnect a
wrong-channel AP; keep STA/ESP-NOW enabled when LAN returns; restore the configured
channel after disconnect. Relay bridge health recovers after temporary association
or channel disruption, with STOP synchronization before new movement.

The router's 2.4 GHz channel and both ESP-NOW configs must match (default 6).
Switching transports can stop movement; uninterrupted motor motion is not an
acceptance promise. Set the fallback flag to 0 to disable it.

OPEN: compile and run the updated tests/firmware, then verify no-LAN boot, LAN
loss/return, AP loss, wrong-channel rejection, bounded retries and recovery.
No compilation or uploads were performed for this update, per user instruction.
Previous successful builds are historical and predate these changes.

## Implementation update - 2026-09-07

DONE: implementation in separate `_ESPNOW` copies, preserving both original
Arduino sketches as unchanged source/rollback backups. Source, configuration,
build profiles and the deployment procedure are in
[`esp32/espnow/README.md`](../../esp32/espnow/README.md).

DONE: shared `esp32/libraries/MuseumEspNow` library; fixed-size serialization,
CRC/validation, application ACK/retries, ordered per-peer queues, STOP barrier,
master boot sessions and motor lease epochs, bidirectional health checks,
rate-limited proxy state/status and transport-aware motor safety. Existing motor
PWM/ramp/reversal source and Raspberry Pi/dashboard/scene files are unchanged.

DONE: portable C++ tests for the actual protocol/parser/link implementation.
Firmware build results are recorded in the bridge guide after compilation.

OPEN: real board identification, actual STA MACs, uploads, RF/LAN/OTA/motor
acceptance and measured end-to-end latency. The user confirmed that neither STA
MAC is currently known. Defaults reject zero peer MACs and keep motors OFF.
This file must not be renamed `_DONE` until on-device acceptance is completed.

SUPERSEDED design suggestions in the original plan below:

- Use an Arduino library instead of mirrored shared files. Its real wire format
  is manually serialized and carries 32-bit session/epoch/sequence numbers and
  16-bit logical node IDs. The illustrative `EspNowPacket` is not the wire ABI.
- State travels inside both ACK and heartbeat reply, with a monotonic snapshot
  revision. No separate unconfirmed state packet or allocating TX queue is needed.
- Use eight queued commands plus one ordered in-flight command per peer (up to
  four peers). The 450 ms ACK budget includes queue time. There is a reserved
  four-entry radio STOP queue beside the eight-entry ordinary receive queue.
- A restored lease requires STOP before motion. ACK timeout cancels outstanding
  movement and requests STOP. A one-way return-link failure disables the motor
  through the next probe, even when it still receives master traffic.
- Historical 2026-09-07 rollout used LAN-only MQTT on relay. SUPERSEDED on
  2026-09-08 by same-channel relay WiFi fallback described above. Motor bridge
  maintenance remains USB; relay OTA uses the active LAN or WiFi transport.
- The new copies default to bridge mode with invalid zero peer MACs; the original
  sketches remain the unchanged legacy defaults. Local peer/key settings belong
  in ignored `espnow_local.h` files, not committed credentials.
- Documentation changes for sketch `info.md` apply to the new copies so that the
  source/rollback backups remain untouched. Optional RPI/UI transport labels are
  SKIPPED for v1.

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short completion note with date, changed files, and key tests when it helps
future work.

Whole-file completion rule: when every active item in this file is either
`DONE`, `SKIPPED`, or `SUPERSEDED`, rename the file with `_DONE` before `.md`.

## Goal

Make the LAN relay controller act as the reliable runtime bridge for the motor
controller:

```text
Raspberry Pi backend -> MQTT broker -> LAN relay ESP32
LAN relay ESP32      -> ESP-NOW    -> motor ESP32
motor ESP32          -> ESP-NOW    -> LAN relay ESP32
LAN relay ESP32      -> MQTT       -> Raspberry Pi backend
```

The Raspberry Pi backend should keep using the existing MQTT topic contract.
Scenes, manual dashboard buttons, feedback tracking, retained `/state` topics,
and `devices/<node_id>/status` should continue to work without scene rewrites.

The target production behavior is:

- Raspberry Pi talks only to the relay controller for motor runtime commands.
- Relay controller receives motor MQTT topics over LAN and forwards them to the
  motor controller over ESP-NOW.
- Motor controller can run without usable WiFi/MQTT during the show.
- Relay controller publishes motor feedback, motor state, and motor online/offline
  status back to MQTT as a proxy.
- ESP-NOW can be disabled from firmware config for rollback or direct MQTT mode.
- The motor controller can be moved to another master by changing config, not by
  rewriting command logic.

## Feasibility verdict

This is feasible with very little or no Raspberry Pi backend code change.

Why:

- Backend scene actions already publish plain MQTT commands through
  `StateExecutor._execute_mqtt()`.
- Dashboard manual control already publishes the same MQTT command topics through
  `/api/mqtt/send`.
- Feedback tracker already expects `<command_topic>/feedback`, for example
  `room1/motor1/feedback`.
- Actuator state store already understands retained `<command_topic>/state` and
  `node_id`.
- `devices.json` already maps `room1/motor1` and `room1/motor2` to
  `Room1_ESP_Motory`, while relay topics map to `Room1_Relays_Ctrl`.

The main implementation belongs in ESP32 firmware:

- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS`
- a new shared ESP-NOW helper module under `esp32/common/` or copied into both
  firmware folders if Arduino IDE include paths make sharing impractical.

Backend code should only change if optional diagnostics are added later.

## Current code anchors

Use these existing files as the source of truth before implementing:

- `raspberry_pi/utils/state_executor.py`
  - MQTT scene actions call `mqtt_client.publish(topic, message, retain=False)`.
- `raspberry_pi/utils/mqtt/mqtt_client.py`
  - `publish()` records desired state and starts feedback tracking.
- `raspberry_pi/utils/mqtt/mqtt_feedback_tracker.py`
  - feedback is keyed by original command topic.
- `raspberry_pi/utils/mqtt/mqtt_actuator_state_store.py`
  - `/state` and `node_id` behavior already exists.
- `raspberry_pi/config/rooms/room1/devices.json`
  - motors use `node_id = Room1_ESP_Motory`.
  - relays use `node_id = Room1_Relays_Ctrl`.
- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/mqtt_manager.cpp`
  - relay MQTT callback currently handles relay/effect/STOP commands.
- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/wifi_manager.cpp`
  - LAN is primary, WiFi fallback is optional.
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS/mqtt_manager.cpp`
  - motor command parsing and state publishing are already implemented.
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS/hardware.cpp`
  - keep existing motor smoothing, ramp, direction reversal, and hard stop logic.

## External ESP-NOW facts checked

Reference checked 2026-09-04:

- Espressif ESP-NOW guide for ESP32-S3:
  `https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/network/esp_now.html`

Design implications:

- ESP-NOW send callback confirms MAC-layer send status, not application-level
  command execution. Therefore this project needs its own ACK packet from the
  motor firmware.
- Use sequence numbers so duplicate packets from retries can be detected and
  ignored safely.
- Keep packet payloads under 250 bytes for compatibility with ESP-NOW v1 style
  limits, even if newer stacks can support larger v2 packets.
- Peers must use a compatible WiFi channel. If WiFi fallback or OTA connects to
  an AP, the AP channel must match the configured ESP-NOW channel.

## Non-goals

Do not do these in the first implementation:

- Do not change scene JSON syntax.
- Do not change existing MQTT command topics.
- Do not introduce `/set` or `/ack` topic names.
- Do not require the Raspberry Pi backend to know about ESP-NOW routing.
- Do not make the motor ESP and relay ESP both active subscribers to the same
  motor MQTT command topics in production bridge mode.
- Do not use dynamic discovery/pairing for the first production version.
  Static configured MAC addresses are safer and easier to debug.
- Do not implement this in ESPHome YAML variants before the ArduinoIDE firmware
  path is stable.

## Target MQTT contract

Keep the public MQTT contract unchanged.

Commands published by backend/dashboard:

```text
room1/motor1 = ON:50:L:0
room1/motor1 = SPEED:30
room1/motor1 = DIR:R
room1/motor1 = OFF
room1/motor2 = ON:80:R:5000
room1/STOP   = STOP
```

Feedback published by relay proxy:

```text
room1/motor1/feedback = OK
room1/motor1/feedback = ERROR
room1/motor2/feedback = OK
room1/motor2/feedback = ERROR
```

Retained state published by relay proxy, using state data returned by motor
slave:

```text
room1/motor1/state = {"state":"ON","direction":"LEFT","speed":50,"node_id":"Room1_ESP_Motory","source":"espnow_proxy","ts_ms":12345}
room1/motor2/state = {"state":"OFF","direction":"STOP","speed":0,"node_id":"Room1_ESP_Motory","source":"espnow_proxy","ts_ms":12346}
```

Motor availability published by relay proxy:

```text
devices/Room1_ESP_Motory/status = online
devices/Room1_ESP_Motory/status = offline
```

Relay availability stays owned by relay MQTT LWT:

```text
devices/Room1_Relays_Ctrl/status = online
devices/Room1_Relays_Ctrl/status = offline
```

Important:

- Keep motor `node_id` as `Room1_ESP_Motory`.
- Relay is only a proxy for motor status/state; it should not rename motors to
  `Room1_Relays_Ctrl`.
- Command and feedback topics remain non-retained.
- State topics remain retained.
- Proxy status should be retained, matching current device status behavior.

## Required runtime modes

Add explicit firmware config modes so rollback is simple.

### Mode A - Legacy direct MQTT motor control

Purpose: current behavior and rollback path.

```cpp
const bool ESPNOW_ENABLED = false;
const bool MOTOR_DIRECT_MQTT_COMMANDS_ENABLED = true;
const bool RELAY_MOTOR_BRIDGE_ENABLED = false;
```

Behavior:

- Motor ESP connects to WiFi/MQTT.
- Motor ESP subscribes `room1/motor1`, `room1/motor2`, `room1/STOP`.
- Relay ESP does not subscribe motor topics.
- This mode should behave exactly like today's system.

### Mode B - Production ESP-NOW bridge

Purpose: Raspberry Pi talks only to relay, relay controls motors through ESP-NOW.

Relay:

```cpp
const bool ESPNOW_ENABLED = true;
const bool RELAY_MOTOR_BRIDGE_ENABLED = true;
```

Motor:

```cpp
const bool ESPNOW_ENABLED = true;
const bool MOTOR_DIRECT_MQTT_COMMANDS_ENABLED = false;
```

Behavior:

- Relay ESP subscribes `room1/motor1`, `room1/motor2`, and `room1/STOP`.
- Motor ESP does not subscribe runtime motor MQTT topics.
- Motor ESP accepts runtime commands only from the configured ESP-NOW master.
- Relay ESP publishes MQTT feedback/state/status for the motor node.

### Mode C - Service/OTA direct WiFi

Purpose: maintenance only, not normal show runtime.

Options:

- Temporarily compile/upload legacy direct MQTT mode.
- Or keep WiFi OTA enabled on the motor ESP, but do not connect MQTT or subscribe
  motor command topics while bridge mode is active.

This mode exists so the motor ESP can still be maintained, but it must not create
two active runtime command paths.

## Hard rule: one active command authority

There must be exactly one active runtime authority for motor MQTT topics.

Valid:

```text
Relay subscribes room1/motor1 and room1/motor2.
Motor does not subscribe those MQTT topics.
```

Valid rollback:

```text
Motor subscribes room1/motor1 and room1/motor2.
Relay does not subscribe those motor topics.
```

Invalid production state:

```text
Relay and motor both subscribe room1/motor1 and room1/motor2.
```

Reason:

- Both devices would receive the same backend command.
- Motor might execute directly and through bridge.
- Feedback/state could race and make diagnostics misleading.
- A weak WiFi link could sometimes process a direct command and sometimes miss
  it, creating non-deterministic behavior.

## ESP-NOW packet protocol

Use a small fixed binary packet. Avoid JSON inside ESP-NOW runtime packets.
MQTT payload strings can remain strings inside bounded fields.

Recommended maximum total packet size: under 200 bytes.

Suggested structure:

```cpp
enum EspNowMessageType : uint8_t {
  ESPNOW_MSG_COMMAND = 1,
  ESPNOW_MSG_ACK = 2,
  ESPNOW_MSG_STATE = 3,
  ESPNOW_MSG_HEARTBEAT = 4,
  ESPNOW_MSG_STATUS_REQUEST = 5
};

enum EspNowTarget : uint8_t {
  ESPNOW_TARGET_NONE = 0,
  ESPNOW_TARGET_MOTOR1 = 1,
  ESPNOW_TARGET_MOTOR2 = 2,
  ESPNOW_TARGET_ALL_MOTORS = 3
};

enum EspNowResult : uint8_t {
  ESPNOW_RESULT_NONE = 0,
  ESPNOW_RESULT_OK = 1,
  ESPNOW_RESULT_ERROR = 2,
  ESPNOW_RESULT_DUPLICATE = 3
};

struct EspNowPacket {
  uint16_t magic;          // fixed value, for example 0x4D53 ("MS")
  uint8_t version;         // protocol version, start with 1
  uint8_t messageType;     // EspNowMessageType
  uint16_t seq;            // incremented by sender
  uint8_t sourceNode;      // configured enum/id
  uint8_t targetNode;      // configured enum/id
  uint8_t target;          // EspNowTarget
  uint8_t result;          // EspNowResult
  uint8_t payloadLen;      // length of payload bytes
  char payload[64];        // MQTT-compatible command or compact state payload
  uint16_t crc16;          // over all previous fields
};
```

Alternative:

- If Arduino struct padding becomes annoying, serialize manually into a byte
  buffer with explicit offsets.
- Manual serialization is preferable for a production version because it avoids
  compiler packing surprises.

Validation rules:

- Reject wrong `magic`.
- Reject unsupported `version`.
- Reject packets from unknown MAC.
- Reject payload length above buffer size.
- Reject invalid CRC.
- Reject unknown message type.
- Reject unknown target.
- Reject commands that fail existing motor parser validation.

## Relay bridge behavior

Create a new module in the relay firmware, for example:

```text
espnow_bridge.h
espnow_bridge.cpp
```

Responsibilities:

- Initialize WiFi radio for ESP-NOW without breaking W5500 LAN MQTT.
- Register motor slave peer by configured STA MAC address.
- Subscribe to motor command topics only when `RELAY_MOTOR_BRIDGE_ENABLED`.
- Translate incoming MQTT topic to `EspNowTarget`.
- Enqueue commands from MQTT callback into a fixed-size bridge queue.
- Send ESP-NOW command packets from the normal `loop()`, not from MQTT callback.
- Track one or more pending commands by `seq`.
- Retry if app-level ACK does not arrive.
- Publish MQTT feedback after ACK/result or after bridge timeout.
- Publish retained MQTT motor `/state` after state data is received.
- Publish proxy `devices/Room1_ESP_Motory/status` from ESP-NOW heartbeat health.
- Send periodic heartbeat/status requests to the motor slave.
- Send STOP over ESP-NOW whenever relay receives `room1/STOP` or enters safety
  network-loss cleanup.

### Relay MQTT subscription changes

Current relay firmware subscribes:

```text
room1/<relay_device>
room1/effects/#
room1/STOP
```

In bridge mode add exact motor subscriptions:

```text
room1/motor1
room1/motor2
```

Do not subscribe relay to broad `room1/#`; it increases loop/backpressure risk
and may route topics that are not meant for relay firmware.

### Relay MQTT callback changes

Current relay callback should keep this early ignore behavior:

```cpp
if topic contains /feedback, /status, or /state:
    return
```

Then route:

```text
if topic == room1/motor1 or room1/motor2:
    if bridge enabled:
        enqueue ESP-NOW command
        return
    else:
        ignore without feedback

else if topic == room1/STOP:
    stop local relays/effects
    send ESP-NOW STOP if bridge enabled
    publish local state snapshots
    return

else:
    existing relay/effect handling
```

Important:

- Do not block inside `mqttCallback()` waiting for ESP-NOW ACK.
- Do not call MQTT publish from ESP-NOW receive callback.
- Keep MQTT and ESP-NOW callbacks short; copy data into fixed queues and process
  in `loop()`.

### Relay feedback timing

Current backend `command_ack_timeout_ms` is 700 ms in `config.ini.example`.

Therefore the relay bridge should normally publish motor feedback within this
budget:

```text
ESP-NOW command ACK timeout: 450-500 ms
Retry interval: 60-100 ms
Retry attempts: 3-4
MQTT feedback publish: immediately after final result
```

If field tests show that 700 ms is too aggressive, change
`command_ack_timeout_ms` deliberately and document why. Do not silently let the
backend log timeouts while the motor still eventually moves.

### Relay proxy status

Relay should publish motor proxy status based on ESP-NOW link health:

```text
online  = valid heartbeat/state/ack seen recently
offline = no valid packet for ESPNOW_SLAVE_OFFLINE_TIMEOUT_MS
```

Recommended defaults:

```cpp
const unsigned long ESPNOW_HEARTBEAT_INTERVAL_MS = 1000;
const unsigned long ESPNOW_SLAVE_OFFLINE_TIMEOUT_MS = 3500;
const unsigned long ESPNOW_PROXY_STATUS_PUBLISH_INTERVAL_MS = 5000;
```

Publish:

```text
devices/Room1_ESP_Motory/status = online/offline
```

Caveat:

- MQTT has only one LWT for the relay client. If the relay loses power, it can
  only publish its own relay LWT. The proxied motor status will go stale by
  backend `device_timeout`, which is acceptable because the backend already
  ignores retained online status at startup and cleans stale devices.

## Motor client behavior

Create a new module in the motor firmware, for example:

```text
espnow_client.h
espnow_client.cpp
```

Responsibilities:

- Initialize WiFi radio for ESP-NOW.
- Register the configured master peer MAC.
- Accept packets only from configured master MAC.
- Validate packet header, version, CRC, payload length, and target.
- Deduplicate command packets by `(master_mac, seq)`.
- Execute commands by calling the existing motor control functions.
- Send app-level ACK for every valid command packet.
- Send state packet after successful command execution.
- Send periodic heartbeat packet to master.
- Stop motors if master heartbeat/control link is lost.

### Reuse existing motor logic

Do not rewrite motor movement logic in the ESP-NOW change.

Keep:

- `controlMotor1(...)`
- `controlMotor2(...)`
- `turnOffHardware()`
- `updateMotorSmoothly()`
- direction reversal through zero speed
- command-defined ramp time
- hard STOP behavior
- inactivity timeout
- OTA safe stop

Change only the input transport and safety health source.

### Motor MQTT behavior in bridge mode

In production bridge mode:

- Motor may initialize WiFi radio for ESP-NOW.
- Motor should not connect to MQTT for runtime control.
- Motor should not subscribe `room1/motor1`, `room1/motor2`, or `room1/STOP`.
- Motor should not publish the same `devices/Room1_ESP_Motory/status` while
  relay proxy is publishing it, unless direct MQTT mode is explicitly enabled.

Reason:

- Avoid duplicate command execution.
- Avoid duplicate and conflicting status/state ownership.
- Keep Raspberry Pi topology clean: RPI -> relay -> motor.

### Motor safety in bridge mode

The current motor `.ino` has this safety behavior:

```cpp
if (!isMqttConnected() && !hardwareOff) {
  turnOffHardware();
}
```

This must become transport-aware.

In bridge mode, MQTT is not the runtime control link, so lack of MQTT must not
turn motors off. Instead:

```text
if direct MQTT mode:
    stop when MQTT unavailable

if ESP-NOW bridge mode:
    stop when ESP-NOW master link timeout expires

always:
    stop on STOP command
    stop on no-command timeout
    stop before OTA
    stop on watchdog/reset/startup safe-off
```

Recommended defaults:

```cpp
const unsigned long ESPNOW_MASTER_TIMEOUT_MS = 3000;
const unsigned long NO_COMMAND_TIMEOUT = 180000;
```

The master timeout should be short because active motors are movement hardware.
It should not depend on Raspberry Pi, broker, or WiFi/MQTT health.

## WiFi channel and LAN interaction

This is the most important hardware/firmware trap.

The relay LAN firmware currently stops WiFi fallback when LAN is active. In
bridge mode, that must not shut down the WiFi radio used by ESP-NOW.

Production recommendation:

- Relay MQTT uses W5500 LAN.
- Relay WiFi fallback for MQTT is optional and preferably disabled during the
  first ESP-NOW bridge rollout.
- Relay WiFi radio remains enabled as `WIFI_STA` for ESP-NOW.
- Motor WiFi radio remains enabled as `WIFI_STA` for ESP-NOW.
- Both peers use a fixed `ESPNOW_CHANNEL`.

Config:

```cpp
const bool RELAY_WIFI_FALLBACK_ENABLED = false; // recommended for first bridge rollout
const int ESPNOW_CHANNEL = 6;
```

If WiFi fallback or OTA connects either ESP to an AP:

- The AP must be fixed to the same 2.4 GHz channel as `ESPNOW_CHANNEL`.
- Do not use auto-channel AP mode.
- If the AP moves channels, ESP-NOW can become unreliable or fail.

Implementation detail:

- Use the station MAC address for peer config.
- Print the STA MAC on boot in Serial Monitor so pairing is easy.
- Document the exact relay STA MAC and motor STA MAC in deployment notes.

## Configuration model

Add bridge config in both firmware `config.h` and `config.cpp`.

Relay config:

```cpp
extern bool ESPNOW_ENABLED;
extern bool RELAY_MOTOR_BRIDGE_ENABLED;
extern bool RELAY_WIFI_FALLBACK_ENABLED;
extern int ESPNOW_CHANNEL;
extern unsigned long ESPNOW_COMMAND_ACK_TIMEOUT_MS;
extern unsigned long ESPNOW_RETRY_INTERVAL_MS;
extern int ESPNOW_MAX_RETRIES;
extern unsigned long ESPNOW_HEARTBEAT_INTERVAL_MS;
extern unsigned long ESPNOW_SLAVE_OFFLINE_TIMEOUT_MS;
extern const char* ESPNOW_MOTOR_NODE_ID;
extern const uint8_t ESPNOW_MOTOR_STA_MAC[6];
```

Motor config:

```cpp
extern bool ESPNOW_ENABLED;
extern bool MOTOR_DIRECT_MQTT_COMMANDS_ENABLED;
extern int ESPNOW_CHANNEL;
extern unsigned long ESPNOW_HEARTBEAT_INTERVAL_MS;
extern unsigned long ESPNOW_MASTER_TIMEOUT_MS;
extern const char* ESPNOW_MASTER_NODE_ID;
extern const uint8_t ESPNOW_MASTER_STA_MAC[6];
```

Optional security config:

```cpp
extern bool ESPNOW_ENCRYPTION_ENABLED;
extern const uint8_t ESPNOW_PMK[16];
extern const uint8_t ESPNOW_LMK[16];
```

Security note:

- Do not commit real ESP-NOW keys if encryption is enabled.
- For first hardware bring-up, unencrypted ESP-NOW with strict allowed MACs is
  acceptable.
- For production, prefer encrypted unicast peer traffic if the Arduino/ESP-IDF
  stack on the target boards supports it reliably.

Modularity rule:

- The motor slave should not contain hard-coded relay-specific behavior.
- It should accept one configured master peer.
- Moving the motor to another master should require changing
  `ESPNOW_MASTER_STA_MAC`, `ESPNOW_MASTER_NODE_ID`, and maybe channel only.

## Queueing and backpressure

Use fixed queues. Avoid unbounded allocation.

Relay bridge queues:

```text
incoming MQTT motor command queue: 8 entries
pending ACK slots: 2-4 entries
incoming ESP-NOW event queue: 8 entries
```

Motor client queues:

```text
incoming ESP-NOW command queue: 8 entries
outgoing ACK/state queue: 8 entries
```

Rules:

- STOP is high priority and may flush ordinary queued motor commands.
- If command queue is full, publish `ERROR` feedback for the rejected command.
- Do not retry forever.
- Do not send heartbeat faster than configured interval.
- Do not publish MQTT `/state` repeatedly if the logical state did not change,
  except on boot/reconnect/status snapshot.
- Do not publish per-loop telemetry into MQTT.

## Duplicate and retry behavior

Master behavior:

1. Assign `seq`.
2. Send command packet.
3. Wait for app-level ACK with matching `seq`.
4. Retry after interval if no ACK.
5. Publish MQTT feedback `OK` or `ERROR`.
6. Publish retained MQTT state when state packet is received.

Slave behavior:

1. Validate packet.
2. If `seq` was already executed, do not execute again.
3. Re-send ACK for duplicate valid command.
4. For new command, execute exactly once.
5. Send ACK with `OK` or `ERROR`.
6. Send state snapshot after successful command.

Why:

- If ACK is lost, master may retry.
- Without dedupe, a retried `DIR`/`SPEED`/`ON` packet could re-trigger logic.
- `STOP` may be safely repeated, but still dedupe for consistent protocol.

## STOP and fail-safe behavior

STOP must be the most reliable path.

When relay receives `room1/STOP`:

- Stop relay outputs and effects as today.
- Flush pending motor bridge commands.
- Send ESP-NOW STOP to motor slave immediately.
- Retry STOP a small number of times.
- Publish relay state snapshots as today.
- Publish motor proxy state `OFF` only after motor ACK/state if available.
- If motor does not ACK, publish motor feedback `ERROR` if a command-specific
  feedback is relevant, and mark proxy motor status offline/degraded.

When relay loses MQTT/broker/network:

- Current relay safety already turns local relay outputs off after grace.
- Add bridge safety: send ESP-NOW STOP before or during local safety cleanup.
- Continue ESP-NOW heartbeat if relay itself is alive.

When motor loses ESP-NOW master:

- Motor must call `turnOffHardware()` after `ESPNOW_MASTER_TIMEOUT_MS`.
- Motor should keep trying to receive/recover link.
- When link returns, motor should send heartbeat and current state snapshot.

When motor reboots:

- Startup safe-off runs before network/ESP-NOW setup.
- Motor sends heartbeat and OFF state snapshot after ESP-NOW init.
- Relay publishes proxy motor status/state to MQTT on next loop.

## State and status ownership

In bridge mode:

```text
Motor ESP owns physical motor state.
Relay ESP owns MQTT proxy publication for that state.
Backend owns UI aggregation and stale/offline interpretation.
```

Motor ESP should return state to relay in a compact ESP-NOW state packet.
Relay converts it to the current retained MQTT `/state` JSON payload.

Do not make relay infer motor state only from commands. It can temporarily show
desired/pending internally, but MQTT retained state should come from motor ACK or
state snapshot.

Recommended state fields:

```json
{
  "state": "ON",
  "direction": "LEFT",
  "speed": 50,
  "node_id": "Room1_ESP_Motory",
  "source": "espnow_proxy",
  "ts_ms": 12345
}
```

If relay cannot get a fresh motor state:

- Keep last retained state as historical.
- Publish proxy status offline after timeout.
- Let backend mark the motor node stale/unknown through existing device registry
  behavior.

## Raspberry Pi backend impact

MVP should not require Python backend changes.

Keep:

- `room1/motor1` and `room1/motor2` in scene JSON.
- `room1/motor1` and `room1/motor2` in dashboard device config.
- `node_id = Room1_ESP_Motory` for both motors.
- `<topic>/feedback`.
- `<topic>/state`.
- `devices/Room1_ESP_Motory/status`.

Optional later backend/UI diagnostics:

- Add `"transport": "espnow_proxy"` to motor items in `devices.json`.
- Add `"master_node_id": "Room1_Relays_Ctrl"` to motor items.
- Display "via Relay / ESP-NOW" in Live view.
- Add a relay bridge health endpoint or status card.

These diagnostics are not needed for first functional bridge.

## Potential backend regression check

This bridge should not break Raspberry Pi behavior if the following stay true:

- Relay publishes exactly the same feedback topics the motor firmware used to
  publish.
- Relay publishes retained state under `room1/motor1/state` and
  `room1/motor2/state`, not under relay-specific topics.
- Relay publishes proxy status as `devices/Room1_ESP_Motory/status`.
- Motor topics in `devices.json` stay unchanged.
- Backend `command_ack_timeout_ms` stays compatible with bridge ACK timing.
- Relay does not publish fake `OK` before the motor accepted the command.

Known acceptable limitation:

- If relay loses power, proxied motor status has no MQTT LWT of its own.
  Backend will mark it offline after `device_timeout`. This is acceptable and
  consistent with current stale-device behavior.

## Implementation phases

### Phase 0 - Hardware inventory and MAC capture

Status: OPEN for physical board/MAC capture. DONE: first-rollout channel 6,
LAN-only relay MQTT and motor USB maintenance selected and documented (2026-09-07).

SUPERSEDED 2026-09-08: relay WiFi fallback is enabled, requiring a matching fixed
2.4 GHz AP channel. Actual MAC/board and on-device checks remain open.

No code changes yet.

SUPERSEDED: implementation proceeded in separate non-deployed copies; no physical
pairing or upload is claimed. Both firmware variants print their STA MAC on boot.

Tasks:

- Confirm exact relay board and motor ESP board.
- Confirm relay LAN works with W5500 as current production path.
- Confirm whether relay WiFi fallback is needed during show runtime.
- Confirm whether motor OTA is required during show runtime or only service mode.
- Capture relay STA MAC from Serial Monitor.
- Capture motor STA MAC from Serial Monitor.
- Confirm 2.4 GHz AP channel if any WiFi/OTA fallback will stay connected.

Output to record:

```text
Relay node_id:
Relay STA MAC:
Motor node_id:
Motor STA MAC:
ESP-NOW channel:
Relay WiFi fallback during show: yes/no
Motor WiFi OTA during show: yes/no
```

Acceptance:

- The master/slave MACs and channel are known.
- It is clear whether WiFi fallback/OTA must coexist with ESP-NOW.

### Phase 1 - Shared ESP-NOW protocol module

Status: DONE (2026-09-07). `esp32/libraries/MuseumEspNow` implements the portable
protocol/state machines and the ESP32 radio adapter. Native C++ fault tests pass.

Create shared protocol code:

- packet constants
- enums
- packet encode/decode
- CRC helper
- payload bounds checks
- MAC formatting helper for debug logs
- duplicate sequence helper

Preferred location:

```text
esp32/common/espnow_link/
```

Fallback if Arduino IDE cannot include shared folders cleanly:

- copy the same files into both firmware folders,
- keep comments saying they are mirrored files,
- update both copies together.

Acceptance:

- Packets encode/decode deterministically.
- Invalid magic/version/CRC/length is rejected.
- Payload size stays under 250 bytes.
- No dynamic allocation is needed in command hot paths.

### Phase 2 - Motor ESP-NOW client

Status: DONE for source implementation in `esp32_mqtt_controller_MOTORS_ESPNOW`
(2026-09-07). Physical motor acceptance below remains OPEN.

Add to motor firmware:

- `espnow_client.h/.cpp`
- config flags for ESP-NOW bridge mode
- ESP-NOW init in setup
- periodic heartbeat in loop
- incoming command queue
- ACK/state outgoing queue
- master timeout safety
- transport-aware safety check replacing direct `!isMqttConnected()` logic

Keep direct MQTT mode as default until relay bridge is tested.

Acceptance:

- With `ESPNOW_ENABLED=false`, motor firmware behaves like today's MQTT motor
  controller.
- With `ESPNOW_ENABLED=true` and direct MQTT disabled, motors do not turn off
  merely because MQTT is disconnected.
- Valid ESP-NOW `ON`, `OFF`, `SPEED`, `DIR`, and `STOP` commands execute through
  existing motor control functions.
- Invalid commands return `ERROR` and do not change motor state.
- Repeated packet `seq` does not execute twice.
- Master timeout stops motors.

### Phase 3 - Relay ESP-NOW master bridge

Status: DONE for source implementation in `esp32_mqtt_controller_RELAY_ESPNOW`
(2026-09-07). On-device MQTT/LAN/radio acceptance below remains OPEN.

Add to relay LAN firmware:

- `espnow_bridge.h/.cpp`
- config flags for relay motor bridge
- motor topic subscriptions in bridge mode
- MQTT callback routing for `room1/motor1` and `room1/motor2`
- fixed bridge command queue
- pending ACK tracking and retry
- proxy feedback publish
- proxy state publish
- proxy motor status publish from heartbeat health
- STOP forwarding and queue flush
- bridge health debug logs

Acceptance:

- With bridge disabled, relay firmware behaves like today's relay controller.
- With bridge enabled, relay subscribes exact motor topics and forwards them.
- Relay publishes `room1/motor1/feedback` and `room1/motor2/feedback`.
- Relay publishes retained `room1/motor1/state` and `room1/motor2/state`.
- Relay publishes `devices/Room1_ESP_Motory/status` based on ESP-NOW health.
- Relay does not block MQTT callback while waiting for motor ACK.

### Phase 4 - Integration mode switch

Status: OPEN. Separate source/build profiles exist, but no board has been flashed.
Actual MAC capture and the physical tests below must precede production use.

Enable bridge mode deliberately.

Steps:

1. Flash motor with ESP-NOW enabled and direct MQTT command handling disabled.
2. Flash relay with ESP-NOW enabled and motor bridge enabled.
3. Confirm motor is not directly connected to MQTT command topics.
4. Confirm relay is the only MQTT subscriber/handler for motor commands.
5. Keep a known-good legacy direct MQTT firmware build available for rollback.

Acceptance:

- RPI/dashboard can run motor commands while motor WiFi/MQTT is unavailable.
- Motor commands are not executed twice.
- Relay status and motor proxy status are independently visible in dashboard.

### Phase 5 - Documentation and optional diagnostics

Status: DONE (2026-09-07). Bridge README, build configuration, local pairing
examples, protocol/hardware/setup docs and new-copy `info.md` files are updated.
Optional backend/UI diagnostics are SKIPPED for v1.

Update:

- `docs/04_mqtt_protocol.md`
- `docs/05_esp32_hardware_reference.md`
- `docs/11_esp32_firmware_setup.md`
- `esp32/devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY/info.md`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS/info.md`

Optional:

- Add `transport` metadata to `devices.json`.
- Add dashboard UI label "via ESP-NOW bridge" if useful.

Acceptance:

- Future implementation sessions can see that motor runtime path is proxied
  through relay.
- Rollback path is documented.
- MAC/channel deployment notes are documented outside secrets.

## Test plan

### Desktop/static review

Before flashing:

- Inspect compile-time config combinations:
  - legacy direct MQTT,
  - relay bridge enabled,
  - motor ESP-NOW client enabled,
  - invalid combination where both direct MQTT and bridge are enabled.
- Confirm invalid production combination is rejected by compile-time `#error` or
  a clear boot-time fatal log.
- Check packet struct size with `sizeof(EspNowPacket)` in Serial output or a
  compile-time static assertion.

### Arduino IDE compile checks

For relay:

- Compile with bridge disabled.
- Compile with bridge enabled.

For motor:

- Compile with ESP-NOW disabled/direct MQTT enabled.
- Compile with ESP-NOW enabled/direct MQTT disabled.

Acceptance:

- All intended profiles compile.
- Profile names and config flags are obvious in Serial boot logs.

### Serial bring-up test

With both ESPs on desk:

1. Flash relay bridge mode.
2. Flash motor ESP-NOW client mode.
3. Open both Serial Monitors.
4. Verify both print STA MAC and `ESPNOW_CHANNEL`.
5. Verify relay sees motor heartbeat.
6. Verify motor sees relay heartbeat or status request.
7. Turn motor ESP off; relay marks motor proxy offline after timeout.
8. Turn motor ESP on; relay marks motor proxy online after heartbeat.

Acceptance:

- Heartbeat works without MQTT direct connection from motor.
- Link loss and recovery are visible without log spam.

### MQTT bridge smoke test

Monitor:

```bash
mosquitto_sub -h <broker_ip> -t 'room1/motor1/#' -t 'room1/motor2/#' -t 'devices/Room1_ESP_Motory/status' -v
```

Commands:

```bash
mosquitto_pub -h <broker_ip> -t 'room1/motor1' -m 'ON:50:L:0'
mosquitto_pub -h <broker_ip> -t 'room1/motor1' -m 'SPEED:30'
mosquitto_pub -h <broker_ip> -t 'room1/motor1' -m 'DIR:R'
mosquitto_pub -h <broker_ip> -t 'room1/motor1' -m 'OFF'
mosquitto_pub -h <broker_ip> -t 'room1/motor2' -m 'ON:50:R:1000'
mosquitto_pub -h <broker_ip> -t 'room1/STOP' -m 'STOP'
```

Expected:

- relay receives MQTT command,
- motor receives ESP-NOW command,
- motor executes,
- motor returns ACK/state,
- relay publishes feedback/state/status,
- no direct MQTT connection from motor is required.

### Weak/no WiFi test

Goal: prove the user's original requirement.

Test:

- Keep Raspberry Pi broker and relay LAN connected.
- Put motor ESP in bridge mode with direct MQTT disabled.
- Make motor unable to reach MQTT WiFi, or do not configure MQTT at all.
- Send dashboard motor commands.

Expected:

- Motors still run through ESP-NOW.
- Dashboard receives feedback/state via relay proxy.
- Backend does not require `Room1_ESP_Motory` to have direct MQTT connectivity.

### Duplicate command test

Force ACK loss or temporarily delay ACK handling if possible.

Expected:

- Relay retries same `seq`.
- Motor re-sends ACK for duplicate.
- Motor does not execute duplicate command twice.

### Queue overload test

Send quick command burst:

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  mosquitto_pub -h <broker_ip> -t 'room1/motor1' -m 'SPEED:30'
done
```

Expected:

- Firmware does not crash.
- Queue full produces controlled `ERROR` or dropped/coalesced diagnostic.
- STOP still has priority.

### STOP safety test

Test these cases:

- STOP during motor ramp.
- STOP while relay is waiting for motor ACK.
- STOP while motor link is down.
- Relay MQTT disconnect while motor is running.
- Motor ESP-NOW master timeout while motor is running.

Expected:

- Motors reach safe off state.
- Relay does not claim false `OK` if motor did not ACK.
- Backend state becomes `OFF` or `STALE/UNKNOWN` according to actual status.

### Scene test

Run existing scene:

```text
raspberry_pi/scenes/room1/motor_test.json
```

Expected:

- No scene JSON changes needed.
- Ramps, speed changes, direction changes, and OFF behave as before.
- Feedback timeout logs do not appear during normal bridge operation.

## Acceptance criteria for v1

V1 is done when:

- Existing MQTT motor topics are unchanged.
- RPI backend and dashboard code are unchanged or only diagnostics were added.
- Relay LAN firmware can bridge `room1/motor1`, `room1/motor2`, and `room1/STOP`
  to motor ESP over ESP-NOW.
- Motor ESP can execute all existing motor commands from ESP-NOW.
- Direct motor MQTT command handling is disabled in production bridge mode.
- Relay publishes motor feedback under existing feedback topics.
- Relay publishes motor retained state under existing state topics.
- Relay publishes proxy status for `Room1_ESP_Motory`.
- Link loss stops active motors locally on the motor ESP.
- STOP works even during retry or link degradation.
- No bridge loop spams MQTT or ESP-NOW.
- Legacy direct MQTT mode remains available for rollback.

## Rollback plan

If ESP-NOW bridge is unstable:

1. Flash motor firmware in legacy direct MQTT mode.
2. Flash relay firmware with `RELAY_MOTOR_BRIDGE_ENABLED=false`.
3. Confirm motor reconnects to WiFi/MQTT.
4. Confirm `devices/Room1_ESP_Motory/status = online` comes from motor again.
5. Confirm dashboard motor buttons work directly.

No Raspberry Pi scene changes should be needed for rollback because topic names
do not change.

## Critical review: what could break and how this plan avoids it

### Risk: WiFi radio shut down on relay when LAN is active

Current relay firmware stops WiFi fallback when LAN is active. ESP-NOW needs the
WiFi radio even when MQTT uses LAN.

Mitigation:

- Separate `RELAY_WIFI_FALLBACK_ENABLED` from `ESPNOW_ENABLED`.
- Do not call a radio-disabling WiFi cleanup path while ESP-NOW is active.
- Prefer LAN-only MQTT plus WiFi-radio-only ESP-NOW for first rollout.

### Risk: direct MQTT and bridge both execute motor commands

If motor direct MQTT stays active while relay bridge is also subscribed, commands
can execute twice or produce racing feedback.

Mitigation:

- Compile-time or boot-time guard against invalid config.
- In production bridge mode, motor direct MQTT command subscriptions are disabled.

### Risk: backend feedback timeout

Relay may need extra time to forward command and wait for ESP-NOW ACK.

Mitigation:

- Keep bridge ACK budget under current 700 ms backend ACK timeout.
- Publish `ERROR` quickly on bridge failure instead of waiting too long.
- Only increase `command_ack_timeout_ms` if measured hardware tests require it.

### Risk: relay publishes fake success

If relay publishes `OK` when ESP-NOW send callback succeeds, motor may not have
actually executed the command.

Mitigation:

- Publish MQTT `OK` only after app-level motor ACK says command was accepted.
- Publish MQTT `ERROR` after retry timeout or motor rejection.

### Risk: state lies after motor link loss

Retained `/state` may show last known ON/OFF even after the motor slave is gone.

Mitigation:

- Relay publishes proxy `devices/Room1_ESP_Motory/status`.
- Backend existing stale/offline behavior marks motor state unknown after offline.
- Relay does not overwrite state with guessed values unless confirmed by slave.

### Risk: ESP-NOW callbacks do too much work

Heavy work inside WiFi callbacks can destabilize firmware.

Mitigation:

- Callbacks only copy validated data to fixed queues.
- MQTT publishing, hardware actions, and retries happen in normal `loop()`.

### Risk: WiFi/OTA channel conflicts

ESP-NOW peers must be on compatible channels. AP auto-channel or OTA WiFi can
move the radio channel.

Mitigation:

- Use fixed `ESPNOW_CHANNEL`.
- Pin AP to same 2.4 GHz channel if WiFi/OTA must coexist.
- Prefer service-mode OTA rather than always-connected motor WiFi during first
  production bridge rollout.

### Risk: queue spam during scene timeline bursts

Multiple timeline commands can arrive close together.

Mitigation:

- Fixed command queue.
- STOP priority.
- Bounded retries.
- No per-loop state publishing.
- Controlled `ERROR` on full queue.

### Risk: implementation becomes relay-specific and not modular

Hard-coding the relay master into the motor logic would make future rooms harder.

Mitigation:

- Motor accepts one configured master MAC/node id.
- Relay master uses a peer config table.
- Moving to another master is a config change.

## Recommended first implementation batch

Start with the smallest safe proof:

1. Add shared ESP-NOW packet encode/decode.
2. Add motor ESP-NOW receive path for `STOP` and one motor command.
3. Add relay bridge send path for `room1/motor1`.
4. Verify ACK and feedback end-to-end.
5. Add `motor2`.
6. Add heartbeat/status/state proxy.
7. Add full safety timeout and overload handling.

Do not start by rewriting the whole motor firmware. The current motor control
logic is valuable and should be preserved.
