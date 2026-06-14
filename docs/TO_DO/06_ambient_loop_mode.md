# Ambient Loop Mode Plan

Date: 2026-06-14

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short date or note if useful, and do not leave completed work only in chat or
git history.

Scope: Raspberry Pi runtime startup policy and 24/7 scene looping.

Goal: add a production-safe ambient mode where a configured scene starts
automatically after service boot and keeps running or restarting without a
visitor pressing the start button, while preserving the existing classic
button-triggered scene behavior.

## Executive Recommendation

Implement ambient mode as a small runtime policy layer around the existing
scene lifecycle services, not as ad-hoc `if startup_mode == "ambient"` blocks
inside `main.py`.

Best first implementation:

1. Add `[Startup]` config keys.
2. Add a small `AmbientLoopService` under `raspberry_pi/utils/runtime/`.
3. Keep scene loading/execution inside the existing `SceneRuntimeService`.
4. Let ambient policy decide when a scene should auto-start or restart.
5. Keep explicit operator STOP and service cleanup as full safety cleanup paths.
6. Do not change `StateMachine`, `TransitionManager`, MQTT routing, audio
   handler, or video handler for v1.

Why this shape:

- The current code already extracted scene lifecycle into runtime helper
  modules.
- Ambient mode is not a new scene action and not a new transition type.
- The risky part is lifecycle cleanup: audio/video stop, actuator force-off,
  `room/STOP`, watchdog state, dashboard status, and stats.
- Keeping the policy in runtime code preserves compatibility with future state
  machine refactors and with the CEC/display and cover plans.

## Operating Modes

| Mode | Behavior |
| --- | --- |
| `classic` | Current behavior. A scene starts from GPIO button, MQTT `scene START`, dashboard, or named scene command. It runs once and ends. |
| `ambient` | A configured scene starts automatically after boot and restarts after normal completion. Default start commands do not create duplicate starts. |

Ambient mode is for exhibits where the Raspberry Pi behaves like a persistent
background controller: video wall, ambient audio, rotating light sequence,
waiting screen, or a room that should always have a scene context active.

## Two Different Loop Types

Do not mix these two concepts:

| Loop type | Best place | Use case |
| --- | --- | --- |
| Scene lifecycle loop | `AmbientLoopService` + `SceneRuntimeService` | Run a full scene from beginning to end, then start it again. |
| Seamless media/state loop | Scene JSON transitions, or a future explicit media loop command | Continuous video/audio/state cycle with no visible restart gap. |

Ambient mode is a lifecycle feature. It is not meant to make a video frame-loop
perfectly seamless.

If a video must loop with no idle-image flash and no scene stats increment on
each cycle, prefer one of these:

- make the scene transition from the last state back to the first state,
- keep the scene in a long-running state with timeline/MQTT transitions,
- later add an explicit video command such as `LOOP_VIDEO:<file>` if real
  hardware testing proves it is needed.

Do not implement seamless media looping by repeatedly ending and restarting the
whole scene every few seconds.

## Current Code Context

Relevant current files:

- `raspberry_pi/main.py`
  - Owns `MuseumController`.
  - Delegates scene start/run/stop to runtime helper services.
  - Wires MQTT, button handler, scene parser, dashboard, and services.

- `raspberry_pi/utils/runtime/scene_runtime_service.py`
  - Owns scene thread creation and scene execution flow.
  - Starts scenes through `_set_scene_running(True, ...)`.
  - On scene completion currently stops audio/video, marks lifecycle idle,
    force-turns actuators off, broadcasts `room/STOP`, clears current scene, and
    broadcasts dashboard status.
  - This is the most important integration point.

- `raspberry_pi/utils/runtime/scene_lifecycle.py`
  - Owns synchronized `scene_running` transitions.
  - Writes `/tmp/museum_scene_state`.
  - Starts/stops heartbeat for watchdog freshness.

- `raspberry_pi/utils/runtime/scene_stop_coordinator.py`
  - Owns explicit stop ordering for parser, audio, video, actuator force-off,
    and MQTT STOP broadcast.

- `raspberry_pi/utils/scene_parser.py`
  - Loads and executes scene JSON through current state machine stack.
  - Should not know about startup mode.

- `raspberry_pi/utils/mqtt/mqtt_message_handler.py`
  - Routes scene start commands and transition events.
  - Should not contain ambient loop policy.

- `raspberry_pi/watchdog.py`
  - Reads `/tmp/museum_scene_state`.
  - Treats fresh `running` as an active scene and waits up to
    `scene_wait_max_seconds` before forcing a restart.

Important current behavior:

- `SceneRuntimeService.run_scene_logic(...)` is the real scene finally path.
- Putting ambient restart code only in `main.py._run_scene_logic()` would miss
  the actual cleanup responsibilities.
- A naive restart from inside `finally` can fail because `_initiate_scene_start`
  expects `scene_running == False`.
- A naive ambient loop can accidentally send `room/STOP` between every cycle.

## Design Principles

1. Classic mode must remain unchanged by default.
2. Ambient mode must use the same scene JSON format as classic mode.
3. Ambient mode must keep one active scene at a time.
4. Explicit operator STOP must still be a real safety stop.
5. Service shutdown and crash/error paths must still clean up media and devices.
6. Ambient normal-cycle cleanup must be configurable and conservative.
7. MQTT messages used by running scenes must continue to reach
   `mqttMessage` transitions.
8. The implementation must fit the current `SceneParser` / `StateMachine` /
   `TransitionManager` runtime boundaries.
9. The implementation must be observable through dashboard/API status.
10. Missing or invalid ambient scenes must not create a tight restart loop.

## Proposed Architecture

Add:

- `raspberry_pi/utils/runtime/ambient_loop_service.py`
- `raspberry_pi/tests/test_ambient_loop_service.py`
- focused additions to existing runtime tests

Wire into:

- `raspberry_pi/utils/config_manager.py`
- `raspberry_pi/config/config.ini.example`
- `raspberry_pi/main.py`
- `raspberry_pi/utils/runtime/__init__.py`
- `raspberry_pi/utils/runtime/scene_runtime_service.py`
- `raspberry_pi/Web/routes/status.py`
- `raspberry_pi/Web/dashboard.py`

Do not wire into:

- `StateMachine`
- `TransitionManager`
- `StateExecutor`
- `SceneParser`, except maybe read-only status/debug helpers later
- `AudioHandler`
- `VideoHandler`
- ESP32 firmware

## New Runtime Helper

### `raspberry_pi/utils/runtime/ambient_loop_service.py`

Purpose:

- Own startup/ambient policy.
- Decide if ambient mode is enabled.
- Resolve the configured ambient scene name.
- Decide when to auto-start after boot.
- Decide whether a completed scene should restart.
- Hold operator suspension state after explicit STOP.
- Provide status data for dashboard/API.
- Keep timing/retry decisions out of `main.py` and out of scene execution code.

Suggested public API:

```python
class AmbientLoopService:
    def is_enabled(self) -> bool: ...
    def scene_name(self) -> str: ...
    def startup_mode(self) -> str: ...
    def get_status(self) -> dict: ...

    def should_ignore_default_start(self) -> bool: ...
    def should_allow_named_scene_start(self) -> bool: ...

    def start_after_boot_if_needed(self) -> bool: ...
    def start_after_mqtt_restore_if_needed(self) -> bool: ...

    def should_restart_after_scene(self, scene_filename: str, *, normal_end: bool) -> bool: ...
    def restart_delay_seconds(self, *, normal_end: bool) -> float: ...
    def wait_for_restart_delay(self, delay_seconds: float) -> bool: ...

    def suspend_by_operator_stop(self) -> None: ...
    def resume(self) -> None: ...
    def request_shutdown(self) -> None: ...
```

Notes:

- The helper should not create scene threads directly.
- It can call the controller's existing `_initiate_scene_start(...)` only from
  boot/reconnect/manual resume paths where no scene is already running.
- For restart after normal scene end, prefer integration inside
  `SceneRuntimeService` so lifecycle state and cleanup stay coherent.
- Keep the helper small. If it grows too much, split only after real complexity
  appears.
- `wait_for_restart_delay(...)` must be interruptible. Do not use a bare
  `time.sleep(delay)` for ambient restart waits.
- The current controller has `shutdown_requested`, not a shared shutdown event.
  The ambient helper should either own a small `threading.Event` that is set on
  shutdown/stop/suspend, or poll `owner.shutdown_requested` in short bounded
  intervals. Do not reuse `_heartbeat_stop_event`; that event belongs only to
  scene-state heartbeat.
- `start_after_boot_if_needed(...)` and
  `start_after_mqtt_restore_if_needed(...)` must be idempotent. MQTT restore can
  happen more than once during one process lifetime.

## Config Design

### `raspberry_pi/config/config.ini.example`

Add:

```ini
[Startup]
# Runtime startup mode: classic | ambient
mode = classic

# Scene file used in ambient mode. If empty, [Json] json_file_name is used.
ambient_scene =

# Policy for the first ambient start:
# - after_initial_connection_attempt: default; try MQTT first, then start even
#   in existing offline mode if the broker is unavailable.
# - wait_for_mqtt: do not start until MQTT is connected/restored.
ambient_start_policy = after_initial_connection_attempt

# Delay between normal ambient scene cycles.
ambient_restart_delay_seconds = 2

# Delay before retrying when the ambient scene is missing or fails to load.
ambient_error_retry_seconds = 30

# Normal ambient cycle cleanup:
# - scene_only: do not broadcast global room STOP between normal cycles.
# - full_stop: use the same force-off/STOP cleanup as classic scene end.
ambient_cycle_cleanup = scene_only

# Default START commands are GPIO button and MQTT <room_id>/scene START.
# In ambient mode these should not create duplicate starts.
ambient_ignore_default_start = true

# Operator/dashboard/named scene starts are explicit actions. Keep them allowed
# unless a final installation wants a locked 24/7 player.
ambient_allow_named_scene_start = true

# When an operator presses Stop in ambient mode:
# - suspend_until_restart: stop now and do not auto-restart until service restart
#   or explicit future resume action.
# - resume_after_delay: treat the stop like a normal ambient cycle and restart
#   after ambient_restart_delay_seconds, not ambient_error_retry_seconds.
ambient_stop_behavior = suspend_until_restart
```

Recommended first defaults:

```ini
[Startup]
mode = classic
ambient_scene =
ambient_start_policy = after_initial_connection_attempt
ambient_restart_delay_seconds = 2
ambient_error_retry_seconds = 30
ambient_cycle_cleanup = scene_only
ambient_ignore_default_start = true
ambient_allow_named_scene_start = true
ambient_stop_behavior = suspend_until_restart
```

Why `scene_only` cleanup by default:

- Ambient scenes are expected to be authored as persistent/background scenes.
- Sending `room/STOP` between every normal cycle can flicker lights, reset
  covers, interrupt display/audio behavior, and hide real scene bugs.
- Explicit STOP, shutdown, missing scene, load failure, parser crash, and service
  cleanup still use full safety cleanup.

If a specific ambient scene relies on the runtime safety STOP between cycles,
either:

- set `ambient_cycle_cleanup = full_stop`, or
- add explicit cleanup actions to the scene's `END` state.

## Config Manager Changes

### `raspberry_pi/utils/config_manager.py`

Read the new `[Startup]` section and return flat config keys from
`get_all_config()`.

Suggested output keys:

```python
startup_mode
ambient_scene
ambient_start_policy
ambient_restart_delay_seconds
ambient_error_retry_seconds
ambient_cycle_cleanup
ambient_ignore_default_start
ambient_allow_named_scene_start
ambient_stop_behavior
```

Validation rules:

- Unknown `mode` should log a warning and fall back to `classic`.
- Negative delay values should be clamped to `0`.
- Empty `ambient_scene` means use `json_file_name`.
- Unknown enum values should fall back to the documented default.
- If `ambient_restart_delay_seconds` is greater than
  `[System] scene_wait_max_seconds`, log a warning. With Option A lifecycle
  gaps, an oversized restart delay can make watchdog restart the service during
  normal ambient waiting.

Do not put scene start logic in `ConfigManager`.

## MuseumController Integration

### `raspberry_pi/main.py`

Add one lazy accessor, matching the existing style:

```python
def _ambient_loop_service(self):
    ...
```

Initialize the helper alongside:

- `DashboardNotifier`
- `SceneLifecycle`
- `SceneRuntimeService`
- `SceneStopCoordinator`
- `SystemActions`

Boot startup:

- After services are initialized and callbacks are wired, the system should know
  the ambient config.
- In `run()`, after the initial MQTT connection attempt, call the ambient helper
  if configured.
- If `ambient_start_policy = wait_for_mqtt`, do not start on failed initial
  connection; let `_on_mqtt_connection_restored()` trigger it later.

MQTT restore:

- `_on_mqtt_connection_restored()` should call the ambient helper only when the
  policy is `wait_for_mqtt` and the scene has not already been started or
  suspended.
- The helper must internally guard against repeated restore callbacks. It should
  not start the same ambient scene twice after broker reconnects or network
  flapping.

Button/default start:

```python
def on_button_press(self):
    if self._ambient_loop_service().should_ignore_default_start():
        log.info("Ignoring default scene start in ambient mode")
        return False
    return self._initiate_scene_start(...)
```

Named scene start:

- Do not blindly ignore named scene starts in ambient mode.
- Treat dashboard/manual named starts as operator intent.
- If `ambient_allow_named_scene_start = false`, reject with a clear log.
- Existing `SceneRuntimeService.initiate_scene_start(...)` already rejects a
  start while another scene is running.

Explicit stop:

- `stop_scene()` should remain a full safety stop.
- In ambient mode, if `ambient_stop_behavior = suspend_until_restart`, mark the
  ambient helper suspended before or during stop.
- Stop/suspend/shutdown must wake any pending ambient restart wait.
- Later a dashboard "Resume Ambient" button can clear suspension and start the
  ambient scene again.

### Runtime service dependency access

Use the same owner/lazy-accessor style that the current runtime helpers already
use.

Recommended:

```python
ambient = owner._ambient_loop_service()
```

from inside `SceneRuntimeService`.

Avoid adding a setter such as `scene_runtime.set_ambient_loop_service(...)`
unless a later refactor makes it necessary. `SceneRuntimeService` already has
the controller owner, and the current codebase consistently uses owner-backed
lazy service accessors for this layer.

## SceneRuntimeService Integration

### `raspberry_pi/utils/runtime/scene_runtime_service.py`

This is the key file.

The current `run_scene_logic(...)` should be reshaped so that it can distinguish
these end reasons:

- normal scene completion,
- missing scene file,
- scene load failure,
- scene parser unavailable,
- exception during scene execution,
- external stop,
- service shutdown.

Ambient normal restart should happen only for normal scene completion and only
when:

- ambient mode is enabled,
- the finished scene is the configured ambient scene,
- shutdown was not requested,
- ambient is not suspended by operator stop,
- no explicit external stop changed `scene_running` to false mid-run,
- the helper says restart is allowed.

Ambient error retry is separate from normal restart:

- Missing scene file, scene load failure, parser unavailable, or state-machine
  start failure may retry after `ambient_error_retry_seconds`.
- Runtime execution exceptions should use full safety cleanup and stop ambient
  in v1. Add a separate future retry-on-exception policy only if a real exhibit
  needs it.

Recommended shape:

```python
def run_scene_logic(self, scene_filename):
    while True:
        outcome = self._run_scene_once(scene_filename)
        if not self._should_ambient_restart(scene_filename, outcome):
            break
        self._cleanup_after_ambient_cycle(scene_filename, outcome)
        if not self._wait_for_ambient_restart_delay(outcome):
            break
```

Or keep one public method and private helpers. The important part is that the
ambient loop remains inside the scene runner thread, where lifecycle and cleanup
state are already owned.

### Normal ambient cycle cleanup

For `ambient_cycle_cleanup = scene_only`:

- Let scene `onExit`, `END.onEnter`, audio/video end handling, and normal media
  stop happen as they do today.
- Do not call `force_actuators_off(source='scene_end')`.
- Do not call `owner.broadcast_stop()` between normal cycles.
- Clear state needed for the next load/run.
- Broadcast dashboard status or scene progress in a way that does not flicker
  misleading "stopped" state if the next cycle starts immediately.

For `ambient_cycle_cleanup = full_stop`:

- Use the current classic scene-end safety cleanup between cycles.

For all non-normal paths:

- Keep current safety cleanup behavior.
- Force actuators off.
- Broadcast `room/STOP` where current code does so.
- Mark lifecycle idle.
- Broadcast status.

Cleanup matrix:

| Action | `scene_only` normal ambient cycle | `full_stop` normal ambient cycle | Error/explicit stop/shutdown |
| --- | --- | --- | --- |
| scene `onExit` / `END.onEnter` | yes, via normal scene flow | yes, via normal scene flow | best effort, depending on where failure happened |
| `stop_audio_for_scene_finally()` | yes | yes | yes |
| `video_handler.stop_video()` | yes | yes | yes |
| `_set_scene_running(False, ...)` | yes | yes | yes |
| clear current scene/status fields | yes | yes | yes |
| dashboard status broadcast | yes | yes | yes |
| `force_actuators_off(source='scene_end')` | no | yes | yes |
| `broadcast_stop()` / `room/STOP` | no | yes | yes where current safety paths already do so |

The matrix is intentionally conservative: local media cleanup still happens
between scene cycles, but global external-device STOP is avoided in the normal
ambient loop by default.

### Restart delay waiting

Ambient restart delay must be interruptible.

Do not implement this:

```python
time.sleep(delay)
```

Prefer an event-backed wait owned by `AmbientLoopService`, or a short polling
loop:

```python
deadline = time.monotonic() + delay
while time.monotonic() < deadline:
    if owner.shutdown_requested or ambient.is_suspended():
        return False
    time.sleep(min(0.2, deadline - time.monotonic()))
return True
```

Tests should not need to sleep for real production delays. Keep the wait helper
small enough to test with `delay_seconds = 0`, a fake event, or a very short
timeout.

### Lifecycle state between cycles

Two acceptable first-version options:

Option A - brief idle gap:

- Mark scene `idle` after each normal cycle.
- Wait `ambient_restart_delay_seconds`.
- Start the next cycle through the normal lifecycle start path.
- Simpler and easier to reason about.
- Dashboard may show a short idle gap.

Option B - continuous ambient running:

- Keep lifecycle `running` across cycle boundaries.
- Internally reset/reload the scene without exposing an idle gap.
- Better dashboard/watchdog semantics for 24/7 player use.
- More delicate because `_set_scene_running(...)` currently treats duplicate
  transitions as idempotent no-ops.

Recommended first implementation: Option A.

Reason:

- It uses the existing lifecycle transition contract.
- It keeps watchdog state truthful: no scene is actually executing during the
  restart delay.
- The delay can be set to `0` or a low value for near-continuous behavior.

If dashboard flicker becomes a problem, improve presentation later with an
`ambient_active` status field instead of hiding lifecycle transitions.

## MQTT Behavior

Ambient mode should not change general MQTT routing.

Keep this behavior:

- Device status messages still go to device registry.
- Feedback messages still go to feedback tracker.
- State reports still go to actuator state store.
- Custom scene input topics still go to `scene_parser.register_mqtt_event(...)`
  so `mqttMessage` transitions work normally.

Default start commands:

| Source | Current route | Ambient default |
| --- | --- | --- |
| GPIO start button | `on_button_press()` | Ignore when `ambient_ignore_default_start = true` |
| MQTT `<room_id>/scene` + `START` | `button_callback()` | Ignore through `on_button_press()` |
| Dashboard Run Scene / named scene | `start_scene_by_name(...)` | Allow as operator intent unless disabled |
| MQTT `<room_id>/start_scene` | `named_scene_callback()` | Allow as explicit named scene request unless disabled |
| Other MQTT topics | `scene_parser.register_mqtt_event(...)` | Unchanged |

Do not modify `MQTTMessageHandler` for the basic ambient implementation.

If later security/control policy needs stricter behavior, add that as a
separate MQTT command authorization topic or operator mode, not as hidden
routing behavior.

## Dashboard/API Status

### `raspberry_pi/Web/routes/status.py`

Add ambient fields to `_get_current_status_data(controller)`:

```python
'startup_mode': controller.config.get('startup_mode', 'classic'),
'ambient': controller._ambient_loop_service().get_status(),
```

The exact shape can be:

```json
{
  "enabled": true,
  "scene": "AmbientLoop.json",
  "suspended": false,
  "start_policy": "after_initial_connection_attempt",
  "cycle_cleanup": "scene_only",
  "next_restart_at": null,
  "last_outcome": "normal_end"
}
```

Field contract:

- `next_restart_at`: ISO 8601 UTC string such as
  `2026-06-14T13:18:42Z`, or `null` when no restart is scheduled. Do not expose
  `time.monotonic()` values through the API.
- `last_outcome`: one of `never_started`, `normal_end`, `missing_scene`,
  `load_failure`, `parser_unavailable`, `start_failure`, `error`,
  `explicit_stop`, `shutdown`.

### `raspberry_pi/Web/dashboard.py`

Also include these fields in `_get_status_data()` and therefore in
`runtime_snapshot`.

Frontend display can come later, but the backend API should expose enough state
from the first implementation so operators can diagnose why a scene did or did
not restart.

Useful future dashboard controls:

- badge: `AMBIENT`
- suspended indicator
- `Resume Ambient`
- `Suspend Ambient`
- next restart countdown

Do not add frontend controls before the backend semantics are stable.

## Watchdog Compatibility

No mandatory watchdog code change is required for the first implementation, but
the old assumption "watchdog will never restart because ambient is always
running" is not accurate for the current watchdog.

Current watchdog behavior:

- If `/tmp/museum_scene_state` is fresh and says `running`, watchdog waits up to
  `scene_wait_max_seconds`.
- After that hard timeout, watchdog may force a restart.
- Scene heartbeat keeps the state file fresh while `scene_running` is true.

Recommended ambient guidance:

- Keep `scene_heartbeat_interval` enabled as today.
- Set `scene_wait_max_seconds` higher than the longest expected classic or
  ambient scene cycle.
- Also keep `ambient_restart_delay_seconds < scene_wait_max_seconds` when using
  Option A. Otherwise watchdog can interpret the intentional idle gap as a
  service that is safe to restart before the next ambient cycle starts.
- For truly endless scenes, decide deliberately whether watchdog should be
  allowed to force restart after the hard timeout.
- Do not make ambient mode silently disable watchdog safety.

If future installations need a stronger policy, add explicit config later:

```ini
[Watchdog]
ambient_scene_wait_policy = force_after_timeout
```

or:

```ini
[Watchdog]
ambient_scene_wait_policy = never_force_while_heartbeat_fresh
```

Do not add this until the real operational need is clear.

## Compatibility With Other TODO Plans

### CEC Display Power Control

Compatible with `docs/TO_DO/05_cec_display_power_control.md`.

Rules:

- Ambient mode should not send display power commands itself.
- Display decisions belong to the future `DisplayPowerManager`.
- If an ambient scene contains `PLAY_VIDEO` or `displayPolicy = required`, the
  display plan should keep the monitor on through its own active reasons.
- Avoid `room/STOP` between normal ambient cycles by default, because it can
  interfere with display/media continuity.

### Cover/Roleta Support

Compatible with `docs/TO_DO/07_cover_roleta_support.md`.

Rules:

- `room/STOP` remains an explicit safety stop.
- Do not broadcast `room/STOP` on every normal ambient cycle unless
  `ambient_cycle_cleanup = full_stop`.
- If an ambient scene controls covers, the scene should contain explicit
  safe end-state actions or use `full_stop` cleanup deliberately.
- Future system heartbeat for covers should run independently of scene mode.

### MQTT State Reporting Rework

Compatible with `docs/TO_DO/03_mqtt_state_reporting_rework_DONE.md`.

Rules:

- Ambient restarts should not spam false device state transitions.
- `scene_only` cycle cleanup avoids publishing global STOP/OFF between every
  normal loop.
- If `full_stop` is configured, the resulting state updates are intentional.

### Current State Machine Boundary

This plan is designed for the current system:

- `SceneParser`
- `StateMachine`
- `TransitionManager`
- `StateExecutor`

Rules:

- Ambient mode must depend only on high-level scene lifecycle outcomes from
  `SceneRuntimeService`.
- Do not inspect `TransitionManager` queues or state machine internals.
- Do not implement ambient mode according to the proposed future
  Pydantic/`transitions` refactor. That refactor is not a prerequisite and
  should not shape this feature.
- If the state machine is ever refactored later, ambient mode should continue to
  work because it only cares whether the scene completed normally, failed, was
  stopped, or the service is shutting down.

### Reliability/Stability Completed Work

Compatible with `docs/TO_DO/99_reference_reliability_stability_completed_work.md`.

Rules:

- Keep centralized `_set_scene_running(...)` semantics.
- Keep heartbeat freshness behavior.
- Keep idempotent stop behavior.
- Do not reintroduce duplicate STOP broadcasts.
- Preserve audio/video cleanup on exceptions and explicit stop.

## Edge Cases

| Situation | Recommended behavior |
| --- | --- |
| Ambient scene file missing | Log error, use full safety cleanup once for that failed attempt, wait `ambient_error_retry_seconds`, retry only if ambient is not suspended and service is not shutting down. |
| Scene load validation fails | Treat like missing scene; use full safety cleanup and do not tight-loop. |
| Scene fails to start state machine | Mark `start_failure`, use full safety cleanup, retry after `ambient_error_retry_seconds`. |
| Scene crashes during execution | Mark `error`, use full safety cleanup, and stop ambient in v1. Add retry-on-exception only as a later explicit policy. |
| Scene ends normally | Restart after `ambient_restart_delay_seconds` if it is the configured ambient scene. |
| Operator presses Stop | Full safety stop; suspend ambient until service restart by default. |
| Service shutdown signal during restart delay | Cancel restart and run cleanup. |
| MQTT unavailable at boot | Follow `ambient_start_policy`. Default starts after initial connection attempt, matching existing offline mode. |
| MQTT reconnects later | If policy is `wait_for_mqtt` and ambient has not started/suspended, start ambient then. |
| Named scene command while ambient is running | Existing start guard rejects because a scene is already running. Log clearly. |
| Named scene command while ambient is suspended/idle | Allow if `ambient_allow_named_scene_start = true`. |
| Ambient scene is also default scene | Supported. Empty `ambient_scene` resolves to `[Json] json_file_name`. |
| Dashboard reconnects | Runtime snapshot includes ambient status. |

## Testing Plan

Add focused tests rather than broad hardware tests.

Recommended files:

- `raspberry_pi/tests/test_ambient_loop_service.py`
- extend `raspberry_pi/tests/test_main_scene_state.py`
- extend `raspberry_pi/tests/test_runtime_smoke.py`

Core tests:

- config defaults to `classic`,
- unknown startup mode falls back to `classic`,
- empty `ambient_scene` resolves to `json_file_name`,
- default start is ignored in ambient mode when configured,
- named scene start remains allowed when configured,
- ambient autostart happens after initial connection attempt,
- `wait_for_mqtt` policy delays autostart until MQTT restore callback,
- MQTT restore autostart is idempotent across repeated reconnects,
- normal ambient scene completion schedules a restart,
- explicit stop suspends ambient by default,
- shutdown during restart delay cancels restart,
- restart delay wait is interruptible and does not require real long sleeps in
  tests,
- missing scene uses error retry delay, not a tight loop,
- `scene_only` cleanup does not call `broadcast_stop()` for a normal ambient
  cycle,
- exception path still calls full safety cleanup,
- status snapshot includes ambient state.

Manual Pi validation:

1. Boot in `classic`; confirm no scene starts automatically.
2. Boot in `ambient`; confirm configured scene starts.
3. Let the scene end; confirm it restarts.
4. Press dashboard Stop; confirm scene stops and does not restart by default.
5. Restart service; confirm ambient starts again.
6. Disconnect MQTT broker before boot; test selected `ambient_start_policy`.
7. Rename ambient scene file; confirm retry logging and no tight loop.
8. Verify watchdog state file transitions and heartbeat behavior.

## Implementation Phases

### Phase 1 - Config And Status

- Add `[Startup]` config keys.
- Parse keys in `ConfigManager`.
- Expose startup/ambient status through backend status APIs.
- Add config/unit tests.

Acceptance:

- Classic mode remains the default.
- Dashboard/runtime status can show mode and ambient scene.

### Phase 2 - AmbientLoopService

- Add `AmbientLoopService`.
- Add helper/accessor in `MuseumController`.
- Implement boot and MQTT-restore start decisions.
- Make boot and MQTT-restore starts idempotent.
- Implement default-start ignore logic.
- Implement operator suspension state.
- Add interruptible restart-delay waiting.
- Add tests with fake controller.

Acceptance:

- Ambient autostart works without changing scene parser/state machine code.
- GPIO/default START does not duplicate ambient starts.
- Explicit stop can suspend ambient.

### Phase 3 - Runtime Loop Integration

- Modify `SceneRuntimeService` to recognize normal scene completion.
- Add ambient restart loop inside scene runtime service.
- Add `scene_only` and `full_stop` cycle cleanup behavior.
- Keep exception/shutdown/explicit stop safety cleanup unchanged.

Acceptance:

- Normal ambient scene completion restarts.
- Normal ambient cycle does not broadcast global STOP by default.
- Error paths still force off and broadcast STOP.

### Phase 4 - Dashboard Controls

Optional after backend behavior is stable:

- Add `AMBIENT` badge.
- Add suspended/active/next restart display.
- Add `Resume Ambient` and possibly `Suspend Ambient` controls.

Acceptance:

- Operator can tell why ambient is running, waiting, or suspended.

### Phase 5 - Production Validation

On the target Raspberry Pi:

- Run overnight in ambient mode.
- Check logs for duplicate starts, STOP spam, MQTT reconnect behavior, and
  watchdog interactions.
- Confirm device states do not drift after many cycles.
- Confirm stop/shutdown always leaves media and devices safe.

## Step-By-Step Implementation Sequence

Implement this feature in small steps. After each step, the implementing AI
must tell the user:

- which files changed,
- which automated tests were run,
- whether any tests were skipped and why,
- exactly what the user should manually test next.

After implementing any concrete step from this section, mark that exact step
`DONE` in this file with a short date/note. After every `.py` file change, also
follow the repository habit and run `/python-review` before finishing the
session.

Do not continue into the next step if the current step changes runtime behavior
and the requested manual test has not been confirmed, unless the user explicitly
asks to continue anyway.

### Step 1 - Startup Config Only - DONE (2026-06-14 config parser/template/tests)

Goal:

- Add config values without changing runtime behavior.

Files:

- `raspberry_pi/config/config.ini.example`
- `raspberry_pi/utils/config_manager.py`
- `docs/14_config_reference.md`
- test file, preferably `raspberry_pi/tests/test_ambient_loop_service.py` or a
  focused config test

Implementation:

- Add `[Startup]` section to `config.ini.example`.
- Parse and validate startup keys in `ConfigManager.get_all_config()`.
- Move `[Startup]` from planned to current implemented keys in
  `docs/14_config_reference.md`.
- Default must remain `classic`.
- Clamp negative delays to `0`.
- Warn when `ambient_restart_delay_seconds > scene_wait_max_seconds`.

Automated verification:

```bash
cd raspberry_pi
pytest tests/test_ambient_loop_service.py tests/test_runtime_smoke.py
```

Manual test to tell the user:

1. Start the service/app with default config.
2. Confirm no scene starts automatically.
3. Open dashboard status or logs and confirm startup mode is still effectively
   classic.

### Step 2 - AmbientLoopService Policy Unit - DONE (2026-06-14 policy helper/tests)

Goal:

- Add policy/state helper without wiring it into live runtime yet.

Files:

- `raspberry_pi/utils/runtime/ambient_loop_service.py`
- `raspberry_pi/utils/runtime/__init__.py`
- `raspberry_pi/tests/test_ambient_loop_service.py`

Implementation:

- Implement mode detection, scene resolution, status payload, default-start
  ignore decision, named-scene allow decision, suspension/resume, idempotent
  boot/restore flags, and interruptible restart-delay wait.
- Do not start scenes from this helper except through owner callbacks in later
  wiring steps.
- Do not create scene threads in this helper.

Automated verification:

```bash
cd raspberry_pi
pytest tests/test_ambient_loop_service.py tests/test_runtime_smoke.py
```

Manual test to tell the user:

- No Pi/manual test is expected yet. This step should be behavior-neutral.

### Step 3 - Status/API Wiring - DONE (2026-06-14 backend status fields/tests)

Goal:

- Expose ambient status without starting or stopping scenes automatically.

Files:

- `raspberry_pi/main.py`
- `raspberry_pi/Web/routes/status.py`
- `raspberry_pi/Web/dashboard.py`
- tests for status payload if practical

Implementation:

- Import/export `AmbientLoopService` through `utils/runtime/__init__.py`.
- Extend `_initialize_runtime()` globals/imports and add a lazy accessor in
  `main.py` matching existing helper style.
- Add `startup_mode` and `ambient` fields to `/status`, dashboard status, and
  runtime snapshot.
- Ensure `next_restart_at` is ISO 8601 UTC string or `null`.
- Ensure `last_outcome` uses the documented enum values.

Automated verification:

```bash
cd raspberry_pi
pytest tests/test_ambient_loop_service.py tests/test_ambient_status_wiring.py tests/test_runtime_smoke.py
```

Manual test to tell the user:

1. Start the app in default classic config.
2. Open dashboard or call `/status`.
3. Confirm status contains `startup_mode: classic` and ambient status shows
   disabled/no scheduled restart.

### Step 4 - Boot And Start-Command Policy - DONE (2026-06-14 boot/default-start policy/tests)

Validation setup note (2026-06-14):

- Added `raspberry_pi/scenes/room1/ambient_mode_smoke_test.json` as a safe
  no-output ambient test scene.
- Set local `raspberry_pi/config/config.ini` to `[Startup] mode = ambient` with
  `ambient_scene = ambient_mode_smoke_test.json` for Pi validation.
- After validation, return `[Startup] mode = classic` unless continuing
  directly into the next ambient runtime step.

Goal:

- Make ambient mode start on boot and prevent duplicate default starts.

Files:

- `raspberry_pi/main.py`
- `raspberry_pi/tests/test_main_scene_state.py`
- `raspberry_pi/tests/test_ambient_loop_service.py`

Implementation:

- In `run()`, call ambient autostart after the initial MQTT connection attempt
  for `after_initial_connection_attempt`.
- In `_on_mqtt_connection_restored()`, call the helper only for
  `wait_for_mqtt`, and keep it idempotent.
- In `on_button_press()`, ignore default start when configured.
- In `start_scene_by_name()`, allow named starts unless
  `ambient_allow_named_scene_start = false`.
- Do not modify `MQTTMessageHandler`; default MQTT start already routes through
  `on_button_press()`.

Automated verification:

```bash
cd raspberry_pi
pytest tests/test_ambient_loop_service.py tests/test_main_scene_state.py tests/test_runtime_smoke.py
```

Manual test to tell the user:

1. Set `[Startup] mode = ambient` and choose a short harmless scene.
2. Restart the service.
3. Confirm the scene starts automatically.
4. Send MQTT `<room_id>/scene` payload `START` or press the GPIO start button.
5. Confirm no duplicate scene starts and logs say default start was ignored.

### Step 5 - Stop, Suspend, And Shutdown Wakeup

Goal:

- Preserve STOP as safety behavior and prevent ambient restart after operator
  stop by default.

Files:

- `raspberry_pi/main.py`
- `raspberry_pi/utils/runtime/scene_stop_coordinator.py` if needed
- tests for stop/suspend behavior

Implementation:

- Before or during `stop_scene()`, call
  `ambient.suspend_by_operator_stop()` when `ambient_stop_behavior` is
  `suspend_until_restart`.
- Ensure suspend/stop/shutdown wakes any pending ambient restart wait.
- In `_signal_handler()` and cleanup paths, call `ambient.request_shutdown()`
  if the helper exists.
- Keep `stop_scene()` full cleanup behavior: parser stop, audio stop, video
  stop, force actuators off, and `room/STOP`.

Automated verification:

```bash
cd raspberry_pi
pytest tests/test_ambient_loop_service.py tests/test_main_scene_state.py tests/test_runtime_smoke.py
```

Manual test to tell the user:

1. Run ambient mode with a looping short scene.
2. Press Stop in dashboard.
3. Confirm audio/video/devices stop and `room/STOP` is sent.
4. Wait longer than `ambient_restart_delay_seconds`.
5. Confirm the scene does not restart until service restart or future explicit
   resume behavior.

### Step 6 - SceneRuntimeService Outcome Refactor

Goal:

- Teach `SceneRuntimeService` to return clear outcomes without changing classic
  behavior yet.

Files:

- `raspberry_pi/utils/runtime/scene_runtime_service.py`
- `raspberry_pi/tests/test_main_scene_state.py`
- `raspberry_pi/tests/test_runtime_smoke.py`

Implementation:

- Split `run_scene_logic(...)` into small private helpers if useful.
- Track outcomes: `normal_end`, `missing_scene`, `load_failure`,
  `parser_unavailable`, `start_failure`, `error`, `explicit_stop`, `shutdown`.
- Preserve current classic cleanup behavior exactly.
- Preserve dashboard status broadcasts and scene stats.

Automated verification:

```bash
cd raspberry_pi
pytest tests/test_main_scene_state.py tests/test_runtime_smoke.py
```

Manual test to tell the user:

1. Return config to `classic`.
2. Start a normal scene from dashboard.
3. Confirm it runs once and stops as before.
4. Press Stop during a scene and confirm the existing full stop behavior still
   works.

### Step 7 - Ambient Normal Loop

Goal:

- Restart the configured ambient scene after normal completion.

Files:

- `raspberry_pi/utils/runtime/scene_runtime_service.py`
- `raspberry_pi/tests/test_ambient_loop_service.py`
- `raspberry_pi/tests/test_main_scene_state.py`

Implementation:

- Add the ambient loop around one-scene execution inside
  `SceneRuntimeService`.
- For `scene_only`, do not call `force_actuators_off(source='scene_end')` and
  do not call `broadcast_stop()` between normal ambient cycles.
- For `full_stop`, keep classic end cleanup between cycles.
- Use interruptible wait for `ambient_restart_delay_seconds`.
- Update `next_restart_at` and `last_outcome` status fields.

Automated verification:

```bash
cd raspberry_pi
pytest tests/test_ambient_loop_service.py tests/test_main_scene_state.py tests/test_runtime_smoke.py
```

Manual test to tell the user:

1. Use an ambient test scene that ends after a few seconds.
2. Set `ambient_cycle_cleanup = scene_only`.
3. Restart service and watch at least two cycles.
4. Confirm the scene restarts after the configured delay.
5. Subscribe to `<room_id>/STOP` and confirm no STOP is sent between normal
   cycles.

### Step 8 - Recoverable Startup Failure Retry

Goal:

- Handle missing/load/start failures without a tight loop.

Files:

- `raspberry_pi/utils/runtime/scene_runtime_service.py`
- `raspberry_pi/tests/test_ambient_loop_service.py`
- `raspberry_pi/tests/test_main_scene_state.py`

Implementation:

- For `missing_scene`, `load_failure`, `parser_unavailable`, and
  `start_failure`, mark lifecycle idle and retry after
  `ambient_error_retry_seconds` if ambient is enabled and not suspended.
- Use full safety cleanup once per failed attempt before waiting: stop local
  media, force actuators off, and broadcast `room/STOP` if MQTT is connected.
- Do not retry runtime execution `error` in v1.
- Keep retry wait interruptible.

Automated verification:

```bash
cd raspberry_pi
pytest tests/test_ambient_loop_service.py tests/test_main_scene_state.py tests/test_runtime_smoke.py
```

Manual test to tell the user:

1. Set `ambient_scene` to a missing filename.
2. Restart service.
3. Confirm logs show missing scene and retry delay, not a rapid loop.
4. Restore the scene filename.
5. Confirm the next retry starts the scene.

### Step 9 - Final Pi Validation And Optional Dashboard Controls

Goal:

- Validate the complete behavior on target hardware before adding UI controls.

Files:

- Frontend/dashboard files only if the user explicitly wants visible controls.

Implementation:

- Keep dashboard buttons optional until backend semantics are proven.
- If controls are added, show `AMBIENT`, suspended state, next restart, and
  optional Resume/Suspend actions.

Automated verification:

```bash
cd raspberry_pi
pytest tests/test_ambient_loop_service.py tests/test_main_scene_state.py tests/test_runtime_smoke.py
```

Manual test to tell the user:

1. Run ambient mode for an extended test period.
2. Confirm no duplicate starts after MQTT reconnect.
3. Confirm Stop suspends ambient.
4. Confirm service restart resumes ambient.
5. Confirm watchdog does not restart during normal ambient gaps.
6. Confirm device states do not drift across many cycles.

## Minimal First Implementation

The smallest useful version:

1. Add `[Startup]` config with:
   - `mode`
   - `ambient_scene`
   - `ambient_start_policy`
   - `ambient_restart_delay_seconds`
   - `ambient_error_retry_seconds`
   - `ambient_cycle_cleanup`
   - `ambient_ignore_default_start`
   - `ambient_allow_named_scene_start`
   - `ambient_stop_behavior`
2. Add `AmbientLoopService`.
3. Autostart the ambient scene after initial connection attempt by default.
4. Ignore GPIO/default START in ambient mode.
5. Allow named scene starts unless disabled.
6. Restart the ambient scene after normal completion.
7. Skip global `room/STOP` between normal ambient cycles by default.
8. Keep full safety cleanup for explicit stop, shutdown, missing scene, load
   failure, and exceptions.
9. Expose ambient status in API/dashboard runtime snapshot.
10. Use interruptible restart waiting; no bare `time.sleep(delay)` for ambient
    restart gaps.
11. Add tests for the policy and cleanup decisions.

This gives the operational value without touching scene JSON schema, the React
editor, ESP32 firmware, or media handlers.

## Not Recommended

Avoid these in the first implementation:

- Adding ambient behavior inside `StateMachine` or `TransitionManager`.
- Restarting scenes from `main.py._run_scene_logic()` without updating
  `SceneRuntimeService`.
- Calling `_initiate_scene_start(...)` from a finally block while
  `scene_running` is still true.
- Broadcasting `room/STOP` between every normal ambient cycle by default.
- Ignoring all named scene/dashboard starts in ambient mode.
- Treating ambient mode as a replacement for explicit video looping.
- Implementing ambient mode against the proposed future state machine refactor
  instead of the current runtime stack.
- Hiding watchdog hard timeout behavior.
- Adding frontend controls before backend suspension/resume semantics are
  clear.
- Adding new scene JSON schema fields unless a real ambient scene needs them.

## Open Decisions

Before implementation, decide:

1. For this installation, keep the default explicit dashboard Stop behavior
   `suspend_until_restart`, or override it to `resume_after_delay`?
2. Should the first production ambient scene use lifecycle restart or an
   internal scene loop?
3. Is `scene_only` cleanup safe for the target ambient scene, or should that
   scene use explicit END cleanup actions?
4. Should MQTT named scene commands be allowed as operator overrides in ambient
   installations?
5. Should `ambient_start_policy` be `after_initial_connection_attempt` or
   `wait_for_mqtt` for ESP-heavy rooms?
6. What should `scene_wait_max_seconds` be for a 24/7 ambient installation?
7. Should dashboard get a `Resume Ambient` button in the same implementation,
   or only expose status first?
