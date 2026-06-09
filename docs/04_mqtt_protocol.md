# MQTT protocol and scene command reference

This is the main MQTT contract for the museum system. It documents what the
Raspberry Pi backend subscribes to, what a scene can publish, what ESP32 nodes
understand, and which feedback/status topics are expected.

The system is room-scoped. In examples, replace `roomX` with the configured
room id, for example `room1`.

Related implementation files:

- `raspberry_pi/utils/mqtt/topic_rules.py`
- `raspberry_pi/utils/mqtt/mqtt_message_handler.py`
- `raspberry_pi/utils/mqtt/mqtt_feedback_tracker.py`
- `raspberry_pi/utils/mqtt/mqtt_actuator_state_store.py`
- `raspberry_pi/utils/runtime/scene_stop_coordinator.py`
- `raspberry_pi/utils/state_executor.py`
- `raspberry_pi/utils/schema_validator.py`
- `raspberry_pi/Web/routes/commands.py`
- `raspberry_pi/Web/routes/scenes.py`
- `raspberry_pi/config/rooms/room1/devices.json`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_button/`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_RELAY/`
- `esp32/devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS/`
- `esp32/devices/wifi/EspHome/`

---

## 1. Topic model

The backend subscribes to these topic patterns after MQTT connects:

| Pattern | Meaning |
|---|---|
| `devices/+/status` | ESP32 online/offline status |
| `roomX/+/feedback` | One-level command feedback, for example `room1/motor1/feedback` |
| `roomX/scene` | Default scene trigger |
| `roomX/#` | All room events, used for scene transitions and device commands |

Important routing order in the backend:

1. `devices/<device_id>/status` goes to the device registry.
2. Any topic ending in `/feedback` goes to the feedback tracker.
3. `roomX/scene` with payload `START` starts the default scene.
4. `roomX/start_scene` with a scene filename starts a named scene.
5. Everything else is registered as an MQTT event for `mqttMessage` transitions.

---

## 2. Backend scene control topics

### 2.1 Start default scene

| Field | Value |
|---|---|
| Topic | `roomX/scene` |
| Payload | `START` |
| Effect | Calls the same backend path as the physical button. Starts the default scene from config. |

Example:

```bash
mosquitto_pub -h <broker> -t room1/scene -m START
```

### 2.2 Start named scene

| Field | Value |
|---|---|
| Topic | `roomX/start_scene` |
| Payload | `<scene_file_name>` |
| Effect | Starts a specific scene file from `raspberry_pi/scenes/<room_id>/`. |

Examples:

```bash
mosquitto_pub -h <broker> -t room1/start_scene -m SceneV01.json
mosquitto_pub -h <broker> -t room1/start_scene -m motor_test.json
```

### 2.3 Stop scene and room devices

There are two related stop paths:

| Path | What it does |
|---|---|
| Dashboard/API `stop_scene` | Stops scene runtime, local audio, local video, forces UI actuator states OFF, then publishes `roomX/STOP = STOP`. |
| MQTT command `roomX/STOP = STOP` | ESP32 devices receive it and shut down outputs. The backend treats it as a normal MQTT event unless stop is requested through the backend API. |

Backend scene end also publishes:

| Topic | Payload | Effect |
|---|---|---|
| `roomX/STOP` | `STOP` | Kill signal for room ESP32 devices. |

Example:

```bash
mosquitto_pub -h <broker> -t room1/STOP -m STOP
```

---

## 3. Scene JSON action format

Scene actions can run in `onEnter`, `onExit`, and `timeline`.

Supported action types:

| Action | Required fields | Runtime target |
|---|---|---|
| `mqtt` | `topic`, `message` | Publishes to MQTT broker |
| `audio` | `message` | Local Raspberry Pi audio handler |
| `video` | `message` | Local Raspberry Pi mpv video handler |
| `image` | `message` | Local Raspberry Pi mpv static image display |

MQTT action example:

```json
{
  "action": "mqtt",
  "topic": "room1/light/1",
  "message": "ON"
}
```

Audio action example:

```json
{
  "action": "audio",
  "message": "PLAY:sfx_boom.wav:0.8"
}
```

Video/image action example:

```json
{
  "action": "video",
  "message": "PLAY_VIDEO:intro.mp4"
}
```

Dedicated static image action examples:

```json
{ "action": "image", "message": "SHOW:wallpaper.png" }
{ "action": "image", "message": "CLEAR" }
```

Timeline example:

```json
{
  "timeline": [
    { "at": 0.0, "action": "audio", "message": "PLAY:intro.mp3:0.7" },
    { "at": 1.5, "action": "mqtt", "topic": "room1/light/1", "message": "ON" },
    { "at": 5.0, "action": "mqtt", "topic": "room1/light/1", "message": "OFF" }
  ]
}
```

Multiple actions at the same timeline time:

```json
{
  "at": 3.0,
  "actions": [
    { "action": "mqtt", "topic": "room1/light/4", "message": "ON" },
    { "action": "mqtt", "topic": "room1/light/5", "message": "ON" }
  ]
}
```

Notes:

- Scene MQTT publishes always use `retain=False`.
- `message` may be string, number, or boolean in JSON schema, but firmware command parsers generally expect strings.
- `mqttMessage` transitions compare exact topic and exact payload. There are no wildcards in transition matching.

---

## 4. Scene transition MQTT format

Incoming MQTT messages that are not status, feedback, scene start, or named
scene start are forwarded into the scene parser. They can trigger transitions:

```json
{
  "type": "mqttMessage",
  "topic": "room1/custom/input",
  "message": "PRESSED",
  "goto": "next_state"
}
```

Transition types supported by the backend:

| Type | Required fields | Meaning |
|---|---|---|
| `timeout` | `delay`, `goto` | Fires after seconds spent in current state |
| `audioEnd` | `target`, `goto` | Fires when the named audio file ends |
| `videoEnd` | `target`, `goto` | Fires when the named video file ends |
| `mqttMessage` | `topic`, `message`, `goto` | Fires on exact topic/payload match |
| `always` | `goto` | Fires immediately |

`globalEvents` use the same transition format, but are evaluated against the
whole scene runtime before local state transitions.

---

## 5. Local audio commands

Audio commands are not MQTT topics by themselves. In scenes they are sent with:

```json
{ "action": "audio", "message": "<command>" }
```

Supported audio payloads:

| Payload | Meaning |
|---|---|
| `PLAY:<filename>` | Play an audio file |
| `PLAY:<filename>:<volume>` | Play with volume `0.0` to `1.0` |
| `<filename>` | Shorthand for play file |
| `STOP` | Stop all audio |
| `STOP:<filename>` | Stop a specific playing file |
| `PAUSE` | Pause music and SFX |
| `RESUME` | Resume music and SFX |
| `VOLUME:<value>` | Set music stream volume, `0.0` to `1.0` |

Examples:

```json
{ "action": "audio", "message": "PLAY:sfx_door.wav:1.0" }
{ "action": "audio", "message": "PLAY:music_loop.mp3:0.45" }
{ "action": "audio", "message": "STOP:music_loop.mp3" }
{ "action": "audio", "message": "STOP" }
```

Audio file lookup:

- Files live under the configured `[Audio] directory`.
- If no extension is given, the handler tries `.mp3`, `.wav`, `.ogg`.
- Files starting with `sfx_` are preloaded to RAM before a scene starts.

---

## 6. Local video and image commands

Video commands are also local Raspberry Pi commands, used in scenes with:

```json
{ "action": "video", "message": "<command>" }
```

Supported video/image payloads:

| Payload | Meaning |
|---|---|
| `PLAY_VIDEO:<filename>` | Play a video or display an image |
| `<filename>` | Shorthand for `PLAY_VIDEO:<filename>` |
| `STOP_VIDEO` | Return to the configured idle image, usually `black.png` |
| `PAUSE` | Pause mpv playback |
| `RESUME` | Resume mpv playback |
| `SEEK:<seconds>` | Seek to an absolute video position |

Supported video extensions:

- `.mp4`
- `.avi`
- `.mkv`
- `.mov`
- `.webm`

Supported image extensions:

- `.png`
- `.jpg`
- `.jpeg`

Behavior:

- Videos append the idle image after playback, so the screen returns to black/default when the video ends.
- Static images stay on screen indefinitely until another image/video is loaded or `STOP_VIDEO` is sent.
- Static images do not trigger `videoEnd`.
- `videoEnd` only fires for real video files and requires exact filename match.

Examples:

```json
{ "action": "video", "message": "PLAY_VIDEO:intro.mp4" }
{ "action": "video", "message": "wallpaper.png" }
{ "action": "video", "message": "SEEK:10" }
{ "action": "video", "message": "STOP_VIDEO" }
```

Dedicated static image commands are local Raspberry Pi commands too, used in
scenes with:

```json
{ "action": "image", "message": "<command>" }
```

Supported image action payloads:

| Payload | Meaning |
|---|---|
| `SHOW:<filename>` | Display a static image indefinitely |
| `CLEAR` | Return to the configured idle/default image |
| `DEFAULT` | Alias for `CLEAR` |

Image action filenames must be simple basenames such as `wallpaper.png`, not
paths. The active room and media folder come from `[Room] room_id`,
`[Scenes] directory`, and `[Video] directory` in `config.ini`.

Examples:

```json
{ "action": "image", "message": "SHOW:wallpaper.png" }
{ "action": "image", "message": "CLEAR" }
```

---

## 7. Feedback and actuator state

For room-scoped command topics, the backend expects feedback on:

```text
<original_command_topic>/feedback
```

Examples:

| Command topic | Expected feedback topic |
|---|---|
| `room1/light/1` | `room1/light/1/feedback` |
| `room1/effects/group1` | `room1/effects/group1/feedback` |
| `room1/motor1` | `room1/motor1/feedback` |

Control topics do not normally wait for feedback in backend tracking:

- `roomX/STOP`
- topics ending in `RESET`
- topics ending in `GLOBAL`

Successful feedback payloads:

| Payload | Meaning |
|---|---|
| `OK` | Command succeeded; backend confirms state from the original command |
| `ACTIVE` | Effect/group became active |
| `INACTIVE` | Effect/group became inactive |

Failed feedback payload:

| Payload | Meaning |
|---|---|
| `ERROR` | Device rejected or failed the command |

The dashboard runtime state store infers ON/OFF from outgoing and confirmed
commands. It understands prefixes such as:

- ON-like: `ON`, `1`, `TRUE`, `START`, `ACTIVE`
- OFF-like: `OFF`, `0`, `FALSE`, `STOP`, `INACTIVE`

For motor commands, it also parses:

- `ON:<speed>:<direction>`
- `ON:<speed>:<direction>:<rampTimeMs>`
- `SPEED:<value>`
- `DIR:<direction>`

---

## 8. Device status topics

ESP32 devices publish status to:

```text
devices/<client_id>/status
```

Typical retained payloads:

| Payload | Meaning |
|---|---|
| `online` | Device is connected/alive |
| `offline` | Broker LWT or shutdown message |

Current known client ids:

| Device | Client id |
|---|---|
| Trigger button | `Room1_ESP_Trigger` |
| Motor controller | `Room1_ESP_Motory` |
| Relay controller | `Room1_Relays_Ctrl` |

Examples:

```text
devices/Room1_ESP_Trigger/status
devices/Room1_ESP_Motory/status
devices/Room1_Relays_Ctrl/status
```

The Raspberry Pi device registry marks a device offline if it does not receive
a fresh status within the configured timeout.

---

## 9. ESP32 button trigger

The button node is a publish-only trigger node.

| Direction | Topic | Payload |
|---|---|---|
| Publish | `roomX/scene` | `START` |
| Publish retained status | `devices/<client_id>/status` | `online` |
| Broker/client shutdown | `devices/<client_id>/status` | `offline` |

The Arduino firmware uses:

```text
BASE_TOPIC_PREFIX = "room1/"
SCENE_TOPIC_SUFFIX = "scene"
SCENE_PAYLOAD = "START"
```

So the final trigger is:

```text
room1/scene -> START
```

The current button cooldown is 4 seconds.

---

## 10. ESP32 relay controller

Relay topics are derived from the firmware `DEVICES[]` list:

```text
roomX/<device_name>
```

Supported individual relay payloads:

| Payload | Meaning |
|---|---|
| `ON` | Turn output on |
| `OFF` | Turn output off |
| `1` | Alias for ON |
| `0` | Alias for OFF |

Known current relay device names:

| Device name | Topic example | Notes |
|---|---|---|
| `power/smoke_ON` | `room1/power/smoke_ON` | Smoke machine power |
| `light/fire` | `room1/light/fire` | Fire light |
| `light/1` | `room1/light/1` | Relay/light 1 |
| `effect/smoke` | `room1/effect/smoke` | Auto-off after 12000 ms |
| `light/2` | `room1/light/2` | Relay/light 2 |
| `light/3` | `room1/light/3` | Relay/light 3 |
| `light/4` | `room1/light/4` | Relay/light 4 |
| `light/5` | `room1/light/5` | Relay/light 5 |

Examples:

```bash
mosquitto_pub -h <broker> -t room1/light/1 -m ON
mosquitto_pub -h <broker> -t room1/light/1 -m OFF
mosquitto_pub -h <broker> -t room1/effect/smoke -m ON
```

Relay STOP:

| Topic | Payload | Effect |
|---|---|---|
| `roomX/STOP` | `STOP` | Turns off all relay outputs and stops all effects |

### 10.1 Relay effect groups

Effect groups use:

```text
roomX/effects/<group_name>
```

Supported effect payloads:

| Payload | Meaning |
|---|---|
| `ON` | Start effect |
| `START` | Alias for start |
| `1` | Alias for start |
| `OFF` | Stop effect |
| `STOP` | Alias for stop |
| `0` | Alias for stop |

Known current groups:

| Group | Topic | Devices | Timing |
|---|---|---|---|
| `group1` | `room1/effects/group1` | `light/4`, `light/5` | ON random 75-500 ms, OFF random 150-1500 ms |
| `alone` | `room1/effects/alone` | `light/1` | ON random 60-100 ms, OFF random 2000-5000 ms |

Feedback:

| Command | Feedback |
|---|---|
| Start effect | `ACTIVE` |
| Stop effect | `INACTIVE` |

Examples:

```bash
mosquitto_pub -h <broker> -t room1/effects/group1 -m ON
mosquitto_pub -h <broker> -t room1/effects/group1 -m OFF
mosquitto_pub -h <broker> -t room1/effects/alone -m START
mosquitto_pub -h <broker> -t room1/effects/alone -m STOP
```

---

## 11. ESP32 motor controller

Motor topics:

```text
roomX/motor1
roomX/motor2
roomX/STOP
```

Supported ArduinoIDE motor payloads:

| Payload | Meaning |
|---|---|
| `ON:<speed>:<direction>` | Enable motor and ramp toward target speed using default smoothing |
| `ON:<speed>:<direction>:<rampTimeMs>` | Enable motor and use command-defined ramp time |
| `OFF` | Smoothly stop that motor |
| `SPEED:<value>` | Change speed while motor is enabled |
| `DIR:<direction>` | Change direction while motor is enabled |

Supported direction values in firmware:

| Value | Meaning |
|---|---|
| `L` | Left direction output |
| `R` | Right direction output |

Speed:

- ArduinoIDE firmware maps speed `0-100` to PWM `0-255`.
- Current dashboard config uses default speed `50`.

Ramp time:

- The optional fourth `ON` field is milliseconds.
- Example `ON:80:R:5000` ramps to speed 80 in direction R over 5 seconds.
- If direction changes while motor is already running, the ArduinoIDE firmware first decelerates to zero, flips direction, then accelerates again.

Examples:

```bash
mosquitto_pub -h <broker> -t room1/motor1 -m ON:50:L
mosquitto_pub -h <broker> -t room1/motor2 -m ON:80:R:5000
mosquitto_pub -h <broker> -t room1/motor1 -m SPEED:30
mosquitto_pub -h <broker> -t room1/motor1 -m DIR:R
mosquitto_pub -h <broker> -t room1/motor1 -m OFF
mosquitto_pub -h <broker> -t room1/STOP -m STOP
```

Feedback:

| Command result | Feedback topic | Payload |
|---|---|---|
| Success | `roomX/motor1/feedback` or `roomX/motor2/feedback` | `OK` |
| Failure | `roomX/motor1/feedback` or `roomX/motor2/feedback` | `ERROR` |

STOP behavior:

| Topic | Payload | Effect |
|---|---|---|
| `roomX/STOP` | `STOP` | Immediately disables both motor drivers |

---

## 12. Dashboard/manual MQTT API

The web dashboard can publish direct MQTT commands through:

```text
POST /api/mqtt/send
```

JSON body:

```json
{
  "topic": "room1/light/1",
  "message": "ON"
}
```

Behavior:

- The backend publishes immediately.
- It uses `force_feedback=True`, so feedback is tracked even outside scene execution.
- If the command is `roomX/STOP` with payload `STOP`, the dashboard state store is forced to OFF.

Saved command files are lists of MQTT actions:

```json
[
  { "topic": "room1/light/1", "message": "ON" },
  { "topic": "room1/motor1", "message": "ON:50:L" }
]
```

They can be executed from the dashboard command API and use the same publish
and feedback behavior as direct manual MQTT.

---

## 13. Design rules for new modular devices

Use this pattern for future rooms and devices:

```text
roomX/<category>/<name>
roomX/<device_type><number>
roomX/effects/<group_name>
devices/<client_id>/status
<command_topic>/feedback
```

Recommended examples:

| Device type | Topic pattern | Payload pattern |
|---|---|---|
| Relay/light | `roomX/light/<id>` | `ON`, `OFF`, `1`, `0` |
| Smoke/power | `roomX/power/<name>` | `ON`, `OFF` |
| Timed effect output | `roomX/effect/<name>` | `ON`, `OFF` |
| Effect group | `roomX/effects/<group>` | `ON`, `OFF`, `START`, `STOP` |
| Motor | `roomX/motor<n>` | `ON:<speed>:<dir>[:<rampMs>]`, `OFF`, `SPEED:<value>`, `DIR:<dir>` |
| Scene trigger | `roomX/scene` | `START` |
| Named scene trigger | `roomX/start_scene` | `<scene_file_name>.json` |
| Room kill signal | `roomX/STOP` | `STOP` |

Guidelines:

- Keep every physical room under one `roomX` prefix.
- Publish device status as retained `online` and LWT/shutdown `offline`.
- Publish command acknowledgements to `<command_topic>/feedback`.
- Use `OK`/`ERROR` for one-shot commands.
- Use `ACTIVE`/`INACTIVE` for long-running effect groups.
- Avoid retained command messages for actuators.
- Keep payload strings short; current Arduino firmware uses small stack buffers.
- Update this file whenever a new topic or payload is added.

---

## 14. Quick reference

| Intent | Topic | Payload |
|---|---|---|
| Start default scene | `roomX/scene` | `START` |
| Start named scene | `roomX/start_scene` | `<scene>.json` |
| Stop all room devices | `roomX/STOP` | `STOP` |
| Relay ON | `roomX/light/1` | `ON` |
| Relay OFF | `roomX/light/1` | `OFF` |
| Start relay effect group | `roomX/effects/group1` | `ON` or `START` |
| Stop relay effect group | `roomX/effects/group1` | `OFF` or `STOP` |
| Start motor | `roomX/motor1` | `ON:50:L` |
| Start motor with ramp | `roomX/motor1` | `ON:80:R:5000` |
| Change motor speed | `roomX/motor1` | `SPEED:30` |
| Change motor direction | `roomX/motor1` | `DIR:R` |
| Stop one motor | `roomX/motor1` | `OFF` |
| Device online status | `devices/<client_id>/status` | `online` |
| Device offline status | `devices/<client_id>/status` | `offline` |
| Command feedback | `<command_topic>/feedback` | `OK`, `ERROR`, `ACTIVE`, `INACTIVE` |
