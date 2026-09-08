# Relay-to-motor ESP-NOW bridge

Implementation date: 2026-09-07. Hardware pairing and on-device acceptance are
still required. No devices were flashed during implementation.

Update 2026-09-08: relay LAN-to-WiFi fallback is now enabled by default. These
latest changes were reviewed statically but NOT compiled or flashed, per user
request. The previous four successful builds predate this fallback update.

## Projects and backups

Working ESP-NOW copies:

- `../devices/lan/ArduinoIDE/esp32_mqtt_controller_RELAY_ESPNOW`
- `../devices/wifi/ArduinoIDE/esp32_mqtt_controller_MOTORS_ESPNOW`

The original `esp32_mqtt_controller_RELAY` LAN sketch and
`esp32_mqtt_controller_MOTORS` WiFi sketch were kept byte-for-byte unchanged as
the source/rollback backups. The new copies preserve their board pins, relay
effects and motor PWM/ramp/direction-reversal implementation. Raspberry Pi
code, dashboard code, scene JSON and `devices.json` were not changed.

Runtime path:

```text
RPI MQTT -> relay W5500 LAN / WiFi fallback -> ESP-NOW unicast -> motor
RPI MQTT <- relay proxy    <- application ACK + motor state
```

Use the existing topics `room1/motor1`, `room1/motor2` and `room1/STOP`.
The proxy keeps `Room1_ESP_Motory` as the motor node ID and publishes the existing
`/feedback`, retained `/state` and retained `devices/<node_id>/status` topics.
`OK` means the motor firmware accepted the command, not that a ramp has finished
or a shaft sensor confirmed motion. Reported speed/direction follow the original
motor firmware's logical state, not measured RPM.

## First pairing

Both MAC addresses are currently UNKNOWN. Zero MAC defaults intentionally reject
ESP-NOW initialization. The motor stays OFF and does not fall back to MQTT.

1. Build/open the two `_ESPNOW` sketches. Keep the original projects for rollback.
2. At first boot, each sketch prints `ESP-NOW STA MAC ...` at 115200 baud, even
   when the peer MAC is still zero. The relay prints this after LAN startup.
3. In each sketch folder, create `espnow_local.h` from
   `espnow_local.example.h`. These local files are ignored by Git.
4. Set the relay's `ESPNOW_MOTOR_MAC` to the motor's printed STA MAC. Set the
   motor's `ESPNOW_MASTER_MAC` to the relay's printed STA MAC. Use six hexadecimal
   bytes, e.g. the format `{0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x02}`, but use the
   actual addresses, not that example.
5. Leave matching numeric IDs (`master=1`, `motor=2`) and channel `6`, or change
   them consistently in both local files. For relay WiFi fallback, pin the router's
   2.4 GHz network to this same channel (disable automatic channel selection).
   Use STA MACs, not Ethernet/Bluetooth
   MACs. Valid unicast addresses must be nonzero and distinct.
6. Rebuild and upload the motor first, then relay. Wait for the link's automatic
   STOP synchronization before sending movement commands.
7. Verify LAN, feedback, both motor states, STOP, disconnects and the existing
   `raspberry_pi/scenes/room1/motor_test.json` before normal operation.

Actual board/port selection must match the attached hardware. The supplied build
profiles use ESP32-S3 for the Waveshare W5500 relay and classic ESP32 for the
motor, based on the existing pin maps. No pin map was guessed or changed.

## Build

The shared local Arduino library is `../libraries/MuseumEspNow`. It is the only
copy of the protocol and link logic; the sketches do not carry mirrored copies.
It uses Espressif's native `esp_now` API, supplied by the ESP32 Arduino core.

PlatformIO, from this directory:

```powershell
pio run -e relay_bridge -e motor_bridge -e relay_legacy -e motor_legacy
```

`platformio.ini` pins pioarduino 55.03.37 / Arduino-ESP32 3.3.7 and PubSubClient
2.8. Output is under `.pio/build/<profile>/`. The `.ini` performs compilation
only; uploading requires a deliberate upload command and correct port.
`platformio.local.ini`, when present, is a machine-local build configuration and
is not part of the portable project.

Arduino IDE: install `MuseumEspNow` into the sketchbook's `libraries` folder and
install PubSubClient 2.8. Open the `.ino` whose name matches its `_ESPNOW` folder.
Use Arduino-ESP32 3.x (3.3.7 is the build target). The inherited `ledcAttach` and
W5500 `Network` APIs do not support Arduino-ESP32 2.x. The send callback adapter
handles the ESP-IDF 5.5 signature change.

## Configuration and another master

Mode flags are in each sketch's `espnow_config.h` and can be overridden by
`espnow_local.h` or compiler defines. Routing, timings and peer tables are in
`config.cpp`.

| Profile | Relay | Motor |
| --- | --- | --- |
| Bridge | `ESPNOW_ENABLED=1`, LAN MQTT with WiFi fallback | `ESPNOW_ENABLED=1`, direct MQTT disabled |
| Legacy | `ESPNOW_ENABLED=0`, bridge disabled, LAN/WiFi fallback | `ESPNOW_ENABLED=0`, direct MQTT enabled |

Invalid local mode combinations fail compilation. Configuration cannot detect
another physical device running a conflicting old firmware: deploy the pair
together and keep exactly one owner of motor command topics and proxy status.

To use another master, change only the motor's configured master STA MAC,
`ESPNOW_MASTER_NODE`, and channel if necessary. That master must run the shared
protocol. Add the motor to its `ESPNOW_PEERS` / `ESPNOW_ROUTES` table. Each peer
has its own ordered queue, sequence, lease, status and two full MQTT topics.
Up to four configured peers are supported. Topics and node IDs must be unique;
relay/effect/STOP topic collisions are rejected at startup. No discovery,
broadcast pairing or automatic roaming is performed.

For encrypted unicast, set `ESPNOW_ENCRYPTION_ENABLED=1` and real matching
16-byte PMK/LMK values using `ESPNOW_PMK_BYTES` / `ESPNOW_LMK_BYTES` in the ignored
local headers. Zero keys are rejected when encryption is enabled. The PMK is
radio-wide and each peer can have its own LMK in the peer table. Unencrypted
mode is suitable for initial bring-up; a MAC allowlist by itself is not
authentication against spoofing.

## Relay WiFi fallback

`RELAY_WIFI_FALLBACK_ENABLED=1` is the default. Set it to `0` in the relay's local
config to return to LAN-only MQTT. Existing `WIFI_SSID` / `WIFI_PASSWORD` settings
are used. LAN has priority; WiFi is attempted when LAN is unavailable, including
a boot without Ethernet. A broker outage while LAN still has an IP does not by
itself switch transports.

The AP and both ESP radios must use the same 2.4 GHz channel, currently `6`.
The relay verifies the associated AP channel before allowing MQTT over it. An AP
on a different channel is disconnected with a serial diagnostic; the ESP-NOW
channel is restored. This is a hardware requirement documented by
[Espressif](https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html#can-wi-fi-be-used-with-esp-now-at-the-same-time).

ESP-NOW initializes before any WiFi association, so its startup cannot disconnect
a working fallback session. An association/DHCP attempt is bounded to 8 seconds
(`RELAY_WIFI_CONNECT_TIMEOUT_MS`). Failed attempts use the existing exponential
retry interval up to 30 seconds, with no reboot loop in bridge mode.

The WiFi channel argument is only a search hint. Association/reconnection may
temporarily interrupt radio delivery, so motor control is disabled during this
phase. Motors stop through the existing STOP/watchdog path and require a new
command after recovery. This is not an uninterrupted-motion failover guarantee.
When LAN returns, only the AP connection is stopped: the STA radio and ESP-NOW
peers remain initialized, and the fixed channel is restored after disconnect.
The bridge then automatically resynchronizes through STOP. The motor never
acquires a competing direct MQTT command path.

## Reliability and limits

- The motor radio is fixed-channel STA without AP association or power saving.
  Relay MQTT uses LAN primarily and can associate with an AP on the same channel
  for WiFi fallback. Motor command authority remains the relay bridge.
- The motor needs no WiFi AP or MQTT connection. ESP-NOW still uses the 2.4 GHz
  radio: interference or insufficient direct relay-to-motor range can also
  interrupt it. The behavior on that failure is a local hard stop.
- Each peer permits eight queued commands and one in flight, preserving order
  across its two motors. The 450 ms deadline includes queue residence. Retries
  use the same sequence, at 80 ms intervals, up to four transmissions.
- `ERROR` is returned for invalid/unready/offline/full queues, rejected commands
  and expired ACKs. A missing ACK is an uncertain execution result; the master
  cancels queued movement and requests STOP. Nothing is replayed on reconnection.
- STOP has a reserved receive queue, cancels queued commands and raises the
  sequence barrier. The motor rejects older commands even if they arrive after
  STOP. Relay room STOP feedback waits for all configured motors to acknowledge;
  an unreachable motor gives `ERROR`, while local relays/effects still stop.
- A random master boot session and motor lease epoch prevent old commands from
  becoming valid after reset/link timeout. Link restoration includes STOP before
  new movement is accepted. Duplicate commands re-ACK without re-execution.
- Probes and replies exchange current state every 1000 ms. Only replies matching
  the outstanding probe or command count as master-side link health. Snapshot
  revisions prevent late replies overwriting newer state.
- The motor hard-stops after 3000 ms without valid master contact. A one-way loss
  of motor-to-relay replies is detected by the relay at 3500 ms and its next
  disabled probe stops the motor (up to another 1000 ms). Complete relay power
  loss is stopped locally at the 3000 ms motor timeout.
- MQTT loss disables control and sends STOP, independently of the relay's
  existing local output grace period. A stalled relay loop also trips the motor
  contact timeout. The original 180000 ms no-command timeout remains; heartbeats
  and duplicate retries do not extend it.
- Callbacks only validate/copy bounded radio data or enqueue MQTT commands.
  Motor operations and MQTT proxy publication run in the main loop. Stale radio
  events older than 100 ms are discarded. Only one radio send is outstanding;
  a missing send callback for 250 ms or channel mismatch disables motor control.
  The relay recovers automatically when channel/association health is restored;
  a permanently stuck radio callback may still require a reboot.
- MQTT state is sent only when changed or after reconnect; proxy status refreshes
  every 5000 ms. Failed publication attempts are limited to once per 250 ms.
  Routine radio traffic is not logged per packet.

The existing MQTT contract has no command IDs. Consequently multiple external
publishers issuing simultaneous commands to the same topic cannot obtain
per-request feedback correlation from the RPI tracker. This is an existing
contract limitation; ESP-NOW itself correlates and deduplicates its commands.
Command topics must remain non-retained, as the backend already publishes them.
PubSubClient does not expose the retained bit to callbacks; clear any manually
retained old movement commands before deployment.

The relay has one MQTT LWT. If it loses power, motor proxy availability expires
via the existing backend device timeout (25 s in the example config), while
the motor's own 3 s stop remains independent of backend detection.

## OTA and rollback

Relay OTA uses the active LAN or fallback WiFi connection. Starting OTA clears relays/effects, suspends bridge
control and requests motor STOP. The motor timeout remains the fallback if the
STOP packet cannot be delivered or OTA blocks normal servicing. After a failed
relay OTA attempt the bridge remains suspended until restart.

Motor bridge v1 is maintained over USB, or by deliberately uploading legacy mode
for WiFi OTA. Concurrent motor WiFi OTA/ESP-NOW is not enabled in this version.
Do not enable AP association on the motor independently of the mode config.

Rollback: disable the relay bridge first (or power it down), then upload the
original motor sketch or `motor_legacy`. Upload the original relay sketch or
`relay_legacy`. Verify that only the motor owns its MQTT topics/status. Keep
the machinery stopped during the two-device switch. No backend/scene changes
are required in either direction.

## Verification

Historical result on 2026-09-07, before the WiFi fallback update: `relay_bridge`, `motor_bridge`, `relay_legacy` and
`motor_legacy` all compile successfully with Arduino-ESP32 3.3.7 and PubSubClient
2.8. The relay build retains pre-existing NeoPixel deprecation/unused-variable
warnings. No radio or physical motor test has been claimed from these builds.

Portable C++ tests, from the repository root:

```powershell
g++ -std=c++11 -Wall -Wextra -Werror -pedantic -I esp32/libraries/MuseumEspNow/src esp32/espnow/tests/link_tests.cpp esp32/libraries/MuseumEspNow/src/MuseumEspNow.cpp -o "$env:TEMP/museum_espnow_link_tests.exe"
& "$env:TEMP/museum_espnow_link_tests.exe"
```

These exercise actual shared encode/decode, parser and link state machines with
simulated radio delivery. They cover malformed frames/commands, ACK loss,
duplicates, queue budgets, STOP ordering, master/motor resets, expired leases,
one-way loss, broker loss and clock rollover. They do not emulate RF range,
W5500 behavior, GPIO wiring or real motor mechanics.

`tests/run_tests.ps1` runs the native tests and additionally preprocesses the
actual firmware config headers, including the now-valid relay bridge + WiFi
fallback combination and invalid channel/attempt-timeout settings. The updated
test cases have not been run because compilation was explicitly excluded.
Its preprocessing-only radio stub is not used by any firmware build.

On-device acceptance remains open in
`../../docs/TO_DO/03b_espnow_relay_motor_bridge.md`: pair actual MACs, compile for
actual boards, check both directions/ramps/STOP, disconnect LAN/master/motor,
verify no-AP operation, run the existing motor scene and measure ACK latency
against the backend's 700 ms budget. Keep the plan open until those tests pass.

Additional fallback acceptance: boot with no LAN and a same-channel AP, remove
and restore LAN, remove the AP, try a wrong AP channel, and confirm that reconnect
attempts are bounded, motor control recovers without reboot and old movement
commands are not replayed. Verify Arduino IDE discovers the shared library.

Protocol API references: [Espressif ESP-NOW](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/network/esp_now.html)
and [Arduino-ESP32 ESP-NOW](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/espnow.html).
