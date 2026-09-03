# CEC Display Power Control Plan

Date: 2026-05-23

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short date or note if useful, and do not leave completed work only in chat or
git history.

Scope: Raspberry Pi runtime, HDMI monitor/TV power control via HDMI-CEC.

Goal: keep the monitor off when the current room experience does not need
video, turn it on early enough for scenes that do need video, and avoid
unnecessary on/off cycling during frequent scene starts.

## Implementation Status

- DONE 2026-09-03: Added `DisplayPowerManager` with script/noop backends,
  strict subprocess timeout, async command worker, active display reasons,
  idle standby timer, debouncing, manual force ON/STANDBY, startup power state,
  cleanup standby, and dashboard/API status snapshot.
- DONE 2026-09-03: Added `[Display]` config to `config.ini` and
  `config.ini.example`, using existing `tools/CEC/display_on.sh` and
  `tools/CEC/display_off.sh`.
- DONE 2026-09-03: Wired display power into `ServiceContainer`,
  `MuseumController`, `SceneParser`, `StateExecutor`, scene cleanup, global
  stop, MQTT `<room_id>/display`, and runtime status responses.
- DONE 2026-09-03: Added top-level scene `displayPolicy` validation with
  `auto`, `required`, and `never`.
- DONE 2026-09-03: Added tests for manager behavior, scene display policy,
  MQTT display routing, and schema validation.
- TODO: Add installer checks/package install for `cec-utils`.
- TODO: Validate on the target Raspberry Pi and final display hardware.

## Deployment Assumptions

- One Raspberry Pi controls one room.
- One room controller runs at most one active scene at a time.
- Multiple Raspberry Pis are independent room controllers, not one shared
  multi-room display control cluster.
- CEC state is local to the room/display connected to that Raspberry Pi.
- No cross-room display coordination is required for the first implementation.

## Executive Recommendation

Implement CEC as a separate `DisplayPowerManager`, not as direct CEC calls inside
scene JSON or `VideoHandler.play_video()`.

First-version backend decision:

- Implement only `cec` and `noop` backends.
- Do not implement an HDMI signal power-off backend in v1.
- For non-CEC displays, keep HDMI and `mpv` alive and rely on the configured
  black/idle image instead of turning the video signal off.
- This avoids risking console exposure, lost fullscreen state, EDID/DRM changes,
  or `mpv` output breakage after the display wakes again.

The best default behavior for this project is:

1. At scene load/start, scan the scene JSON for real video playback actions.
2. Allow a scene to explicitly require the display even if it only shows the
   idle image for hours.
3. If the scene contains `PLAY_VIDEO` or has `displayPolicy = required`,
   request display power on at scene start.
4. When a video command is executed, call `request_on("scene_video")` again.
   This is idempotent and should not spam CEC commands.
5. When the scene ends or video stops, release the scene display need but do not
   immediately power off the monitor.
6. Use an idle timer, for example 3-10 minutes, before sending CEC standby.
7. Add simple manual `ON` and `OFF` commands for testing and maintenance.

This keeps startup responsive, avoids repeated on/off cycling, and does not make
video playback depend on a slow or flaky CEC command.

## Why Not Put CEC Directly In Scene Actions

Direct scene actions such as:

```json
{ "action": "mqtt", "topic": "room1/display", "message": "ON" }
```

or a future:

```json
{ "action": "display", "message": "ON" }
```

are useful as an override, but they should not be the primary strategy.

Problems with manual scene-level CEC control:

- Every scene author must remember to add display on/off actions.
- A scene with a delayed video may turn the monitor on too late or too early.
- Scenes that run often can cause repeated power cycling.
- A forgotten `OFF` action can leave the display on indefinitely.
- A CEC command can block or fail independently of scene correctness.

The runtime already knows whether a scene contains video actions. That knowledge
should drive the default display behavior automatically.

## Current Code Context

Relevant existing components:

- `raspberry_pi/utils/video_handler.py`
  - Starts `mpv` at service startup.
  - Keeps a black idle image loaded when video is not playing.
  - Supports `PLAY_VIDEO:<file>`, `STOP_VIDEO`, `PAUSE`, `RESUME`, and `SEEK`.

- `raspberry_pi/utils/scene_parser.py`
  - Loads scene JSON into `StateMachine`.
  - Already scans scene data for audio preloading.
  - Owns scene start/stop lifecycle for parser internals.

- `raspberry_pi/utils/state_executor.py`
  - Dispatches `mqtt`, `audio`, and `video` actions.
- Is the right place to request display-on demand when a video action runs.

- `raspberry_pi/main.py`
  - Owns scene start/end cleanup.
  - Is the right place to release scene-level display reasons when a scene ends.

- `raspberry_pi/utils/service_container.py`
  - Initializes Audio, Video, MQTT, SystemMonitor, ButtonHandler.
  - Should initialize the future `DisplayPowerManager`.

- `raspberry_pi/config/config.ini.example`
  - Should gain a dedicated `[Display]` or `[CEC]` section.

Important current behavior:

- `mpv` runs even while the display is visually idle.
- Powering the monitor off via CEC should not kill `mpv`.
- Some displays may drop HDMI state or behave differently in standby, so this
  must be configurable and tested on the real monitor.

## Proposed Architecture

Add:

- `raspberry_pi/utils/display_power_manager.py`
- `raspberry_pi/tests/test_display_power_manager.py`
- `raspberry_pi/tests/test_scene_display_policy.py`

Wire it into:

- `utils/service_container.py`
- `utils/config_manager.py`
- `utils/scene_parser.py`
- `utils/state_executor.py`
- `main.py`
- optional `utils/mqtt/mqtt_message_handler.py`
- optional dashboard API/routes

## Modular Implementation Shape

The ideal implementation should keep almost all CEC logic in one new module.
The existing runtime files should only get small integration hooks.

This keeps display power policy separate from video playback, scene execution,
MQTT routing, and controller lifecycle code.

For the first implementation, keep the real CEC backend and the no-op testing
backend inside `display_power_manager.py`. Do not create a separate backend
module in v1. Do not add an HDMI signal power backend in v1. Extract a separate
backend module only later if the file becomes too large or if more safe hardware
backends are added.

### New Files

#### `raspberry_pi/utils/display_power_manager.py`

Purpose:

- Own the display power policy.
- Decide when the monitor should be on.
- Decide when the monitor can go to standby.
- Keep idle timer state.
- Debounce repeated ON/OFF requests.
- Track a small set of active display reasons:
  - scene contains video
  - scene has `displayPolicy = required`
  - manual ON was requested
  - video playback just started
- Expose simple public methods for the rest of the system.
- Contain the small CEC backend and no-op backend classes for the first version.
- Treat non-CEC displays as `noop`: the display remains connected and `mpv`
  continues showing the black/idle image.

Suggested public API:

```python
class DisplayPowerManager:
    def request_on(self, reason: str) -> None: ...
    def release(self, reason: str) -> None: ...
    def force_on(self, reason: str = "manual") -> None: ...
    def force_standby(self, reason: str = "manual") -> None: ...
    def get_status(self) -> dict: ...
    def cleanup(self) -> None: ...
```

Notes:

- `request_on()` should never block scene execution on a slow monitor.
- `release()` should only schedule standby; it should not immediately power off
  unless forced.
- `force_on()` and `force_standby()` are for manual ON/OFF commands.
- `cleanup()` should cancel timers and optionally send standby depending on
  config.

Suggested helper classes in the same file:

```python
class DisplayPowerBackend:
    def power_on(self) -> bool: ...
    def standby(self) -> bool: ...
    def power_status(self) -> str | None: ...

class CecClientDisplayBackend(DisplayPowerBackend):
    ...

class NoopDisplayBackend(DisplayPowerBackend):
    ...
```

CEC backend responsibilities:

- Run `cec-client` commands with strict subprocess timeouts.
- Return success/failure instead of raising into runtime code.
- Parse power status best-effort only.
- Log command failures clearly.

No-op backend responsibilities:

- Pretend ON/OFF succeeded.
- Make tests deterministic.
- Allow development on Windows or on a Pi without CEC hardware.

Extraction rule:

- Keep these backend classes in `display_power_manager.py` for v1.
- Keep them in this file while they are only small wrappers.
- Extract a separate backend module only if another hardware backend is
  introduced or the CEC wrapper grows enough to make the manager hard to read.

#### `raspberry_pi/tests/test_display_power_manager.py`

Purpose:

- Test policy without real CEC hardware.

Core tests:

- `request_on()` sends ON once and records a reason.
- repeated `request_on()` does not spam ON commands.
- `release()` of the last reason schedules standby after idle timeout.
- new `request_on()` before idle timeout cancels standby.
- `force_standby()` sends standby immediately.
- backend failure is recorded but does not raise.

#### `raspberry_pi/tests/test_scene_display_policy.py`

Purpose:

- Test scene JSON detection rules.

Core tests:

- scene with `PLAY_VIDEO` requires display in `auto` mode.
- scene with only `STOP_VIDEO` does not require display.
- scene with `displayPolicy = required` requires display even without video.
- scene with `displayPolicy = never` does not auto-request display even if a
  video action exists.

### Minimal Changes To Existing Files

#### `raspberry_pi/utils/config_manager.py`

Add only config loading for `[Display]`.

Suggested output keys:

```python
display_enabled
display_backend
display_mode
display_cec_target
display_cec_client_path
display_idle_timeout_seconds
display_power_command_timeout_seconds
display_power_status_timeout_seconds
display_min_seconds_between_power_commands
display_wait_for_power_on_before_video
display_max_video_start_wait_seconds
display_standby_on_service_stop
display_startup_power_state
```

No CEC logic should live here.

#### `raspberry_pi/config/config.ini.example`

Add a `[Display]` section with conservative defaults.

This file should only document configuration values. It should not imply that
every monitor supports CEC.

#### `raspberry_pi/utils/service_container.py`

Add initialization only:

- Build the backend.
- Build `DisplayPowerManager`.
- Store it as `self.display_power_manager`.
- Include it in cleanup if present.

No scene policy logic should live here.

#### `raspberry_pi/utils/scene_parser.py`

Add only scene inspection helpers:

```python
def get_display_policy(self) -> str: ...
def scene_requires_display(self) -> bool: ...
```

Rules:

- `displayPolicy = required` -> true.
- `displayPolicy = never` -> false.
- default `auto` -> true if scene contains `PLAY_VIDEO`.

Do not send CEC commands from `SceneParser`.

#### `raspberry_pi/utils/state_executor.py`

Add one optional dependency:

```python
display_power_manager=None
```

Before executing a video playback action:

```python
if is_play_video_action(message):
    self.display_power_manager.request_on("scene_video")
```

Then call `video_handler.handle_command(message)` as today.

Do not put idle timers, CEC subprocess calls, or policy decisions here.

#### `raspberry_pi/main.py`

Add only lifecycle hooks:

- After a scene loads and before it runs:
  - if `scene_parser.scene_requires_display()` is true, call
    `display_power_manager.request_on("scene_video")` or
    `display_power_manager.request_on("scene_required")`, depending on whether
    the need comes from detected video playback or `displayPolicy = required`.
- In scene `finally` and `stop_scene()`:
  - release `scene_video` and `scene_required`.
- During service cleanup:
  - call `display_power_manager.cleanup()`.

Do not duplicate display policy in `main.py`.

#### `raspberry_pi/utils/mqtt/mqtt_message_handler.py`

Optional first-version manual control:

- Add handler for `<room_id>/display`.
- Support only:
  - `ON`
  - `OFF`
  - optional `STATUS`

This handler should call `DisplayPowerManager.force_on()` or
`force_standby()`. It should not run `cec-client` directly.

### What Must Not Happen

- Do not put CEC subprocess calls inside `VideoHandler`.
- Do not put idle timer logic inside `StateExecutor`.
- Do not require every scene to manually add display ON/OFF actions.
- Do not make `mpv` lifecycle depend on monitor power state.
- Do not add cross-room/global display coordination.
- Do not block scene playback for a long CEC wake confirmation.

### DisplayPowerManager Responsibilities

The manager should own all display power decisions:

- Send CEC `on` and `standby` commands.
- Query CEC power status when useful.
- Run commands with strict timeouts.
- Avoid blocking scene execution.
- Track active reasons that require the monitor to stay on.
- Debounce repeated `ON` commands.
- Delay `OFF` with an idle timer.
- Support simple manual `ON` and `OFF` override commands.
- Expose status for logs and dashboard.

It should not own video playback. `VideoHandler` should still own `mpv`.

### Active Reasons Model

Use a simple `set` of active reasons instead of a single boolean.

This is not meant to solve multiple scenes running at once. The current runtime
already prevents that. The active-reasons model is useful because one active room can
still have several independent reasons to keep the display on, for example:

- the loaded scene contains video
- a video is actively starting or playing
- the loaded scene explicitly requires the idle image to stay visible
- manual ON was requested

Examples:

- `scene_video`: active while the running scene contains or starts video
  playback.
- `scene_required`: active while the running scene has
  `displayPolicy = required`.
- `manual`: active after manual `ON`, cleared by manual `OFF` or service
  cleanup.

Public API sketch:

```python
display_power.request_on(reason="scene_video")
display_power.release(reason="scene_video")
display_power.force_on(reason="manual")
display_power.force_standby(reason="manual")
display_power.get_status()
```

Rules:

- Any active reason keeps the display on or requested-on.
- Releasing the last reason does not power off immediately.
- The idle timer starts only after the last reason is released.
- A new reason cancels the pending standby timer.
- Manual `ON` adds the `manual` reason and wakes the display.
- Manual `OFF` clears the `manual` reason and sends standby immediately.
- If a required scene/video action happens after manual `OFF`, automatic logic
  may wake the display again.

With the one-RPi-per-room architecture, each Raspberry Pi keeps its own
`active_reasons` only for its own monitor. There is no shared global display
state.

## Power-On Strategy

### Recommended Default

Turn the display on at scene start if the scene contains any `PLAY_VIDEO` action.

Reason:

- It is simple and reliable.
- It avoids delaying the actual video action.
- It handles scenes where the first video action is immediate.
- It also handles scenes where transitions decide later whether the video path
  is reached.

Potential downside:

- A scene that contains a video branch that is rarely reached can wake the
  display even if the visitor never enters that branch.

For this project, reliability is more important than perfect power minimization.
The idle timer prevents the monitor from staying on forever.

### Persistent Idle/Image Scenes

Some scenes intentionally need the monitor even when no video is actively
playing. Example: a room waits for external MQTT buttons while showing a static
idle image for hours, then switches to different videos depending on which
button is pressed.

That should be represented explicitly in the scene, not inferred from
`PLAY_VIDEO`.

Recommended scene-level field:

```json
{
  "sceneId": "waiting_room_menu",
  "displayPolicy": "required",
  "initialState": "WAITING",
  "states": {}
}
```

Policy meanings:

- `auto`: default. Turn the display on if the scene contains `PLAY_VIDEO`.
- `required`: keep the display on for the entire scene, even if it only shows
  the idle image.
- `never`: do not turn the display on automatically for this scene.

For the long idle-image use case:

- Set `displayPolicy` to `required`.
- Configure `iddle_image` to the image that should be visible while waiting.
- Keep the scene running while MQTT button transitions decide which video state
  to enter.
- When the video ends and the scene returns to the waiting state, the display
  stays on because the scene itself still requires it.

If the desired behavior is different, use `auto`:

- The display can stay off during waiting.
- A video branch wakes it when the scene starts or when the video action is
  reached, depending on implementation mode.
- The idle timer later turns it off again.

### Optional Future Optimization

Later, if power use matters more, add a scene-level hint:

```json
{
  "displayPolicy": "auto",
  "displayWarmupSeconds": 8
}
```

or per-state hints. Do not start with this because it adds schema/editor work
and still cannot perfectly predict transition paths.

## Power-Off Strategy

Do not power off immediately after `STOP_VIDEO` or scene end.

Use:

- `display_idle_timeout_seconds = 300` as a starting default.
- Configurable range, for example 30-3600 seconds.

Why:

- If a visitor restarts the scene soon, the monitor is already warm.
- It avoids CEC wear/cycling and visible input wake delays.
- It avoids repeated power-on delay during demos and testing.

Suggested defaults:

```ini
[Display]
enabled = true
backend = cec
mode = auto
idle_timeout_seconds = 300
power_on_lead_seconds = 8
power_command_timeout_seconds = 3
power_status_timeout_seconds = 2
min_seconds_between_power_commands = 15
wait_for_power_on_before_video = false
max_video_start_wait_seconds = 1.0
startup_power_state = standby
```

Notes:

- `wait_for_power_on_before_video = false` should be the default.
- If enabled, the wait must be short and bounded. A slow CEC device must never
  block scene playback for a long time.

## CEC Backend

Recommended implementation:

- Use `cec-client` from the `cec-utils` package.
- Call it through `subprocess.run(...)` with `timeout=...`.
- Never run it in the scene thread directly.
- Use a background worker or bounded command queue.

Example command forms to validate on the Raspberry Pi:

```bash
echo "on 0" | cec-client -s -d 1
echo "standby 0" | cec-client -s -d 1
echo "pow 0" | cec-client -s -d 1
```

The exact target address can vary by display and topology. Use config for the
logical target address, defaulting to `0`.

Suggested config:

```ini
[Display]
cec_target = 0
cec_client_path = cec-client
cec_adapter = auto
```

Implementation detail:

- `cec-client` can occasionally hang or return unclear output.
- Treat CEC as best-effort unless a scene explicitly requires display readiness.
- Log failures, but do not crash the museum runtime.

## Installer Changes

Online installer:

- Add `cec-utils` to `raspberry_pi/install.sh`.
- Keep the existing `video` group assignment.
- Optionally run `cec-client -l` after install as an informational check.

Offline installer:

- Add `need_cmd cec-client` to `raspberry_pi/install_offline.sh` if
  `[Display] enabled = true` is expected for the offline image.
- If CEC is optional, warn instead of failing and let config use
  `enabled = false` or `backend = noop`.

Documentation:

- Document that many TVs support HDMI-CEC, but some computer monitors do not.
- Document that CEC must be enabled in the display's own settings menu.
- Document which HDMI port/cable was validated in the final installation.

## Scene Integration

### SceneParser

Add scene scanning similar to audio preload scanning:

```python
def scene_requires_display(self) -> bool:
    return self._scene_has_video_playback(self.state_machine.scene_data)
```

Detection should count:

- `{"action": "video", "message": "PLAY_VIDEO:file.mp4"}`
- plain video filenames if the current command convention treats them as play
  commands

Detection should not count:

- `STOP_VIDEO`
- `PAUSE`
- `RESUME`
- `SEEK`

At scene start:

- If scene requires display because it contains video, request `scene_video`.
- If scene requires display because `displayPolicy = required`, request
  `scene_required`.
- If not, do nothing.

At scene stop/end:

- Release `scene_video` and `scene_required`.

### StateExecutor

When executing a video action:

- If it is a playback action, call
  `display_power.request_on("scene_video")` before sending the command to
  `VideoHandler`.
- Then execute the video command normally.
- Do not wait long for CEC by default.

When executing `STOP_VIDEO`:

- Do not force display standby.
- The scene-level release at scene end should decide when the idle timer can
  start.
- This avoids turning the display off too early in long scenes that may return
  to a waiting state or play another video later.

### Main Cleanup

In `_run_scene_logic(...).finally` and `stop_scene()`:

- Release scene-level display reasons.
- Let the manager schedule standby after the idle timeout.

During service cleanup:

- If `standby_on_service_stop = true`, send standby best-effort.
- Otherwise leave the display in its current state. This should be configurable.

## Manual Control

Manual control is useful, but should layer on top of auto mode.

Recommended first-version commands:

- `ON`: wake display now.
- `OFF`: send standby now.

Optional later command:

- `STATUS`: report/log current manager status.

Do not add generic timed hold commands in the first version unless a real
maintenance workflow needs them. Scene-level `displayPolicy = required` covers
long-running display-on use cases more cleanly than ad-hoc manual timers.

### MQTT Topic Option

Add a local control topic:

```text
<room_id>/display
```

Payload examples:

```text
ON
OFF
STATUS
```

Where to implement:

- `raspberry_pi/utils/mqtt/mqtt_message_handler.py`

Routing priority:

1. device status
2. feedback
3. scene start
4. named scene start
5. display control topic
6. scene parser transition events

This prevents display control messages from being accidentally consumed as scene
transition events unless the scene explicitly listens for them elsewhere.

### Dashboard/API Option

Add API endpoints later:

- `GET /api/display`
- `POST /api/display/on`
- `POST /api/display/off`

The dashboard can show:

- mode: `auto`
- last command result
- active display reasons
- next standby time
- last known CEC power status

## Reliability Rules

The implementation should follow these rules:

1. CEC commands must never block scene execution for long.
2. Repeated `ON` commands should be debounced.
3. Repeated `OFF` commands should be debounced.
4. CEC failures should degrade display control, not crash the room runtime.
5. Video playback should still start even if CEC power status is unknown.
6. The manager should expose clear logs for every state change.
7. Idle standby must be cancelled when a new scene requiring video starts.
8. Manual override must be visible in status so it is not mistaken for auto
   behavior.

## Failure Modes

### Monitor Does Not Support CEC

Behavior:

- Manager logs `CEC unavailable`.
- Display control status becomes degraded.
- Video playback continues.
- For PC monitors such as the currently tested MSI display, use `backend = noop`
  and keep the configured black/idle image on screen instead of trying to power
  the HDMI signal off.

Mitigation:

- Set `enabled = false` or `backend = noop`.
- Do not use `vcgencmd display_power 0/1` or an HDMI signal power-off backend in
  v1. It can expose the console, disturb fullscreen/DRM state, or require `mpv`
  recovery after wake.
- Optionally evaluate a smart plug or relay-based display power path later, but
  that is a different safety discussion.

### CEC Wake Is Slow

Behavior:

- Scene start requests display on early.
- Video action does not block for the full wake time.

Mitigation:

- Increase `power_on_lead_seconds` or `idle_timeout_seconds`.
- Keep `wait_for_power_on_before_video = false` unless a specific exhibit needs
  strict visual readiness.

### Scene Starts Often

Behavior:

- Idle standby timer is cancelled by the next scene.
- Display stays on during frequent use.

Mitigation:

- Tune `idle_timeout_seconds`.

### Scene Contains Video Branch That Is Not Reached

Behavior:

- Display may turn on anyway at scene start.

Mitigation:

- Accept this for reliability.
- Later add explicit display hints if this becomes wasteful.

### Scene Needs Only The Idle Image For Hours

Behavior:

- With `displayPolicy = required`, the display turns on at scene start and stays
  on while the scene is active.
- The idle timer does not send standby while that scene-level requirement is
  active.

Mitigation:

- Use this only for scenes where the visible idle image is part of the
  experience.
- Use `displayPolicy = auto` for scenes where the monitor can stay off until a
  real video branch is needed.

### CEC Command Hangs

Behavior:

- Subprocess timeout kills the command.
- Manager logs failure and marks last command failed.
- Scene continues.

Mitigation:

- Strict command timeout.
- Background worker.
- Rate-limited retries.

### Monitor Standby Breaks HDMI/mpv State

Behavior:

- Some displays may cause HDMI/EDID changes when put into standby.
- `mpv` may keep working, or may need restart depending on hardware.

Mitigation:

- Validate on target monitor.
- If standby breaks `mpv`, keep `mpv` alive and add display wake warmup.
- If needed, call `video_handler._restart_mpv()` after wake, but only as a
  later hardware-specific fallback, not the default.

## Implementation Phases

### Phase 0 - Hardware Proof

On the target Raspberry Pi:

1. Install/check `cec-utils`.
2. Run `cec-client -l`.
3. Test `on`, `standby`, and `pow` commands.
4. Measure typical wake time.
5. Confirm whether standby affects `mpv` playback after wake.

Acceptance:

- We know whether the actual monitor supports CEC reliably.
- We know a realistic wake lead time.

### Phase 1 - Core Manager - DONE 2026-09-03

Add `raspberry_pi/utils/display_power_manager.py` with:

- `DisplayPowerManager`
- small `DisplayPowerBackend` interface
- `CecClientDisplayBackend`
- `NoopDisplayBackend`
- config parsing
- background command execution
- on/standby/status commands
- idle timer
- active display reasons
- debouncing
- no-op backend for development/tests

Acceptance:

- Unit tests can verify active-reason behavior without real CEC hardware.
- CEC command execution is timeout-bounded.
- No existing runtime module contains direct `cec-client` subprocess calls.

### Phase 2 - Runtime Wiring - DONE 2026-09-03

Wire manager into existing files with small hooks only:

- `ConfigManager`
- `ServiceContainer`
- `MuseumController`
- `SceneParser`
- `StateExecutor`

Acceptance:

- A scene with video requests display on at scene start.
- A scene with `displayPolicy = required` requests display on even without
  video.
- A scene without video does not request display on.
- Scene end schedules standby after idle timeout.
- Frequent scene restarts do not power-cycle the display.
- `VideoHandler` still only owns mpv/video playback.

### Phase 3 - Manual Control - DONE 2026-09-03

Add at least one control surface:

- MQTT topic `<room_id>/display`.

Recommended first:

- MQTT topic, because it is simple and useful for field testing.
- Support only `ON`, `OFF`, and optionally `STATUS` in the first version.

Acceptance:

- `ON` and `OFF` can be sent remotely.
- Optional `STATUS` can report the current display manager state.

### Phase 4 - Dashboard Status - PARTIAL DONE 2026-09-03

Optional but useful:

- Show display state in dashboard status.
- Add buttons for ON/OFF.

Acceptance:

- DONE 2026-09-03: Operator status payload shows whether monitor is on because of auto video need,
  `displayPolicy = required`, or a recent manual command.
- TODO: Add dashboard ON/OFF buttons if an operator-facing UI control is needed.

### Phase 5 - Target Validation

Run on the Pi with real display:

1. Boot system with no scene running.
2. Confirm display eventually enters standby.
3. Start scene without video.
4. Confirm display remains off.
5. Start scene with immediate video.
6. Confirm wake request happens before playback and video still starts quickly.
7. Start scene repeatedly within idle timeout.
8. Confirm display does not power-cycle.
9. Let idle timeout elapse.
10. Confirm standby command is sent.
11. Simulate CEC failure.
12. Confirm scene runtime continues.

## Testing Plan

Unit tests should use a fake backend.

Recommended test files:

- `raspberry_pi/tests/test_display_power_manager.py`
- `raspberry_pi/tests/test_scene_display_policy.py`

Core tests:

- scene with `PLAY_VIDEO` requires display
- scene with `displayPolicy = required` requires display without `PLAY_VIDEO`
- scene with only `STOP_VIDEO` does not require display
- `request_on` cancels pending standby
- release of last active reason schedules standby
- new active reason before idle timeout prevents standby
- frequent `PLAY_VIDEO` calls keep the `scene_video` reason active without
  repeated CEC commands
- CEC timeout marks command failure but does not raise
- manual `ON` sends a wake command
- manual `OFF` sends standby

## Minimal First Implementation

The smallest useful version:

1. Add `[Display]` config.
2. Add `DisplayPowerManager` with CEC/noop backend, `request_on`, `release`,
   and idle standby.
3. Scan scene JSON for `PLAY_VIDEO`.
4. Add top-level `displayPolicy` support with `auto`, `required`, and `never`.
5. Request display on at scene start if video exists or display policy is
   `required`.
6. Release on scene end.
7. Call `request_on("scene_video")` in `StateExecutor._execute_video()` when
   `PLAY_VIDEO` runs.
8. Add MQTT `<room_id>/display` commands `ON` and `OFF` for manual testing.

This version gives most of the value without changing scene JSON format or the
React editor.

## Not Recommended For First Version

Avoid these in the first implementation:

- Requiring every scene to manually add display on/off actions.
- Blocking video playback until CEC reports confirmed-on.
- Killing/restarting `mpv` every time the monitor powers off.
- Adding an HDMI signal power-off backend (`vcgencmd display_power 0/1`) in v1.
- Turning off HDMI for non-CEC monitors instead of showing the black/idle image.
- Adding per-state display schema/editor controls before hardware behavior is
  validated.
- Treating CEC power status as perfectly reliable.
- Adding generic timed hold commands before there is a real operator workflow
  for them.

## Open Decisions

Before implementation, decide:

1. What monitor/TV model will be used in the final installation?
2. What is the measured CEC wake time on that device?
3. Is it acceptable for the first second of video to play while the monitor is
   still waking, or must playback wait briefly?
4. What default idle timeout is best for the museum flow: 3, 5, or 10 minutes?
5. Should service shutdown send monitor standby, or leave the monitor state
   unchanged?
6. Which scenes should use `displayPolicy = required` because the idle image is
   part of the visitor experience?

## Recommended Defaults

Initial values to test:

```ini
[Display]
enabled = true
backend = cec
mode = auto
cec_target = 0
cec_client_path = cec-client
idle_timeout_seconds = 300
power_on_lead_seconds = 8
power_command_timeout_seconds = 3
power_status_timeout_seconds = 2
min_seconds_between_power_commands = 15
wait_for_power_on_before_video = false
max_video_start_wait_seconds = 1.0
standby_on_service_stop = true
startup_power_state = standby
```

These defaults prioritize reliability and visitor experience over maximum power
saving. After measuring the actual monitor, tune `idle_timeout_seconds` and
`power_on_lead_seconds`.
