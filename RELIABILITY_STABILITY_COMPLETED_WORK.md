# Museum System - Completed Reliability And Stability Work

Updated: 2026-05-23

Source documents that this file replaces:

- `RELIABILITY_CODE_REVIEW.md`
- `STABILITY_ANALYSIS.md`
- `STABILITY_ANALYSIS2.md`

This file collects items that were previously listed as risks or problems but
now look implemented, closed, or at least reduced to a lower practical risk in
the current repository state.

## Scene Lifecycle And Watchdog

### Centralized Scene State Transitions

Status: done

Where:

- `raspberry_pi/main.py`
- `raspberry_pi/tests/test_main_scene_state.py`

What changed:

- A central `_set_scene_running(...)` method was added.
- Start, stop, error paths, and cleanup no longer change `scene_running`
  ad-hoc.
- The `running`/`idle` state is written through one synchronized path.
- Repeated start/stop calls are idempotent.

Practical effect:

- Lower race-condition risk between the scene thread, dashboard, and watchdog.
- Easier testing of start/stop semantics.

### Heartbeat For Long Scenes

Status: done

Where:

- `raspberry_pi/main.py`
- `raspberry_pi/watchdog.py`
- `raspberry_pi/config/config.ini.example`
- `raspberry_pi/tests/test_heartbeat.py`

What changed:

- A heartbeat thread was added (`_heartbeat_loop`, `_start_heartbeat`,
  `_stop_heartbeat`).
- While a scene is running, `/tmp/museum_scene_state` is refreshed
  periodically.
- `scene_heartbeat_interval` is configurable.
- The watchdog no longer has to treat a long active scene as stale only because
  the state file was written once at scene start.

Practical effect:

- A long scene should not be interrupted by a watchdog restart only because the
  state-file timestamp got old.

### Watchdog Waits For Scene Completion

Status: done / practically strengthened

Where:

- `raspberry_pi/watchdog.py`
- `raspberry_pi/config/config.ini.example`

What changed:

- The watchdog reads scene state from `/tmp/museum_scene_state`.
- If a scene is running, it waits up to `scene_wait_max_seconds`.
- Poll interval is configurable through `scene_wait_poll_interval`.

Note:

- The old JSON lifecycle lease proposal is superseded by the current text-file
  heartbeat approach for the main practical risk: avoiding interruption of a
  long active scene.

### STOP Cleanup On Scene Exception Path

Status: done

Where:

- `raspberry_pi/main.py`

What changed:

- `_run_scene_logic(...).finally` calls `audio_handler.stop_audio()`.
- Video is also stopped on the cleanup path.
- At scene end, `force_all_off(...)` and `broadcast_stop()` are enforced when a
  real lifecycle transition happened.

Practical effect:

- If a scene crashes before normal `END.onEnter`, audio should not keep playing.

### Duplicate STOP Broadcast Is Reduced

Status: done

Where:

- `raspberry_pi/main.py`

What changed:

- STOP broadcast is tied to a real transition in `_run_scene_logic.finally` or
  explicit `stop_scene()`.
- Idempotent stop paths do not send unnecessary repeated STOP signals.

## Audio And Video Reliability

### Audio Fadeout Click Fix

Status: done

Where:

- `raspberry_pi/utils/audio_handler.py`

What changed:

- After `pygame.mixer.music.fadeout(500)`, the code now waits
  `time.sleep(0.5)` instead of using a too-short wait.

Practical effect:

- Fadeout has time to finish before a hard `stop()`, so the end of a scene
  should produce fewer audible clicks.

### Video End Detection No Longer Treats IPC Unknown As Confirmed End

Status: done

Where:

- `raspberry_pi/utils/video_handler.py`
- `raspberry_pi/tests/test_video_handler_end_detection.py`

What changed:

- `is_playing()` can return `None` when IPC state is unknown.
- `check_if_ended()` does not fire the end callback when state is `None`.
- A `videoEnd` transition should not trigger only because mpv IPC temporarily
  did not answer.

Practical effect:

- A scene should not jump forward during a transient IPC problem.

## MQTT And Feedback

### Falsey MQTT Payload Validation

Status: done

Where:

- `raspberry_pi/utils/state_executor.py`

What changed:

- The MQTT action guard no longer rejects valid values such as `0` or `False`.
- Missing payloads are still rejected when they are `None` or an empty string.

Practical effect:

- Scenes can correctly send zero or boolean payloads.

### Manual MQTT API Checks Publish Result

Status: done

Where:

- `raspberry_pi/Web/routes/commands.py`

What changed:

- `/api/mqtt/send` checks the return value of
  `controller.mqtt_client.publish`.
- On failure it returns HTTP `503`.
- The command execution path for actions has the same check.

Practical effect:

- The dashboard should not report success when local MQTT publish failed.

### Feedback Timeout Is Separated From Command ACK Timeout

Status: done, but production values still need alignment in the future-work
file

Where:

- `raspberry_pi/utils/service_container.py`
- `raspberry_pi/utils/config_manager.py`
- `raspberry_pi/config/config.ini.example`

What changed:

- The feedback tracker receives the ACK budget from `command_ack_timeout_ms`.
- This separates fast command ACK timing from device presence timing.

Note:

- The remaining config ambiguity around `device_timeout = 15` versus the
  180-second fallback is tracked in
  `RELIABILITY_STABILITY_FUTURE_WORK.md`.

### Feedback State Store Confirmations

Status: done

Where:

- `raspberry_pi/utils/mqtt/mqtt_feedback_tracker.py`
- `raspberry_pi/tests/test_mqtt_feedback_state.py`

What changed:

- `OK` confirms the original command.
- `ACTIVE` / `INACTIVE` feedback can confirm real effect state.
- Error feedback does not confirm state.

Practical effect:

- Dashboard/device state has a better distinction between desired and confirmed
  state.

## Web Dashboard And Frontend

### Main Scene Button Uses Auth API Helper

Status: done

Where:

- `museum-dashboard/src/services/api.js`
- frontend scene/action flows using the API service

What changed:

- Main scene config is read through `authFetch`.
- The Basic Auth header from `localStorage` is sent to protected endpoints.

Practical effect:

- The "Run Scene" flow should not fail on a 401/plain-text response without a
  fallback.

### `authFetch` Throws For Non-2xx Responses

Status: done

Where:

- `museum-dashboard/src/services/api.js`

What changed:

- `401` throws `Unauthorized`.
- All non-OK HTTP responses become errors.
- If the backend returns a JSON error, the frontend tries to use its message.

Practical effect:

- The frontend should not show a success state after backend `400/500/503`.

### Vite Output Path Points To Flask `dist`

Status: partly done

Where:

- `museum-dashboard/vite.config.js`
- `raspberry_pi/Web/routes/main.py`

What changed:

- Vite build output now goes to `../raspberry_pi/Web/dist`.
- Flask serves `raspberry_pi/Web/dist`.

What remains:

- Install/release flow still does not guarantee that a build was run after
  frontend source changes. That is tracked in the future-work file.

### Web Log Handler Isolates Exceptions

Status: partly done

Where:

- `raspberry_pi/Web/handlers/log_handler.py`

What changed:

- `WebLogHandler.emit()` wraps `dashboard.add_log_entry(...)` in
  `try/except`.
- Dashboard log fanout errors go through the standard
  `logging.Handler.handleError` path.

What remains:

- The websocket fanout itself is still synchronous. The async queue improvement
  is tracked as open work in the future-work file.

### Dashboard Log History Prefers SQLite

Status: done

Where:

- `raspberry_pi/Web/dashboard.py`

What changed:

- On startup, the dashboard reads `logs/museum_logs.db` first.
- If the DB does not exist, it falls back to legacy `logs/museum.log`.
- The in-memory log buffer is limited by `Config.MAX_LOG_ENTRIES`.

Practical effect:

- Dashboard startup is no longer dependent only on parsing a large text log.

## Service / Install Work

### Watchdog systemd Ordering

Status: done

Where:

- `raspberry_pi/services/museum-watchdog.service.template`

What changed:

- `After=museum-system.service` now matches the real installed main service.

Practical effect:

- Watchdog ordering during boot is less surprising.

## Tests And Validation

### Old Claim That "No Tests Exist" Is Outdated

Status: done / improved

Where:

- `raspberry_pi/tests/test_heartbeat.py`
- `raspberry_pi/tests/test_main_scene_state.py`
- `raspberry_pi/tests/test_mqtt_feedback_state.py`
- `raspberry_pi/tests/test_video_handler_end_detection.py`
- `raspberry_pi/tests/test_device_status_broadcast.py`
- `raspberry_pi/tests/test_ws_museum.py`

What changed:

- Targeted tests now exist for scene heartbeat, scene state transitions, MQTT
  feedback state, video end detection, and dashboard/websocket behavior.

Note:

- This does not mean coverage targets are complete. It only closes the old
  claim that these areas had no test foundation.

## Closed Items From The Old Reviews

These items should not be reopened without new evidence:

- P0-1 scene activity freshness contract: solved by heartbeat.
- P0-2 scene state transitions centralized: solved by `_set_scene_running`.
- P0-4 MQTT timeout refactor: command ACK timeout is separated, although
  production `device_timeout` still needs final config alignment.
- Audio not stopped on scene exception path: solved by cleanup.
- Pygame fadeout click: improved with a longer wait.
- Duplicate scene STOP broadcast: reduced by idempotent lifecycle transitions.
- MQTT falsey payload validation: fixed.
- False video-end callback on IPC unknown: fixed.
- Manual MQTT API reports success when publish fails: fixed.
- Frontend non-2xx handling: fixed.
- Main scene button auth fetch: fixed.
- Watchdog service `After=` ordering: fixed.
