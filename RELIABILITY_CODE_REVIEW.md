# Museum System - Reliability Code Review

Date: 2026-04-25
Scope: Raspberry Pi backend and web dashboard/frontend

## Scope

Reviewed:

- `raspberry_pi/` backend runtime
- `raspberry_pi/Web/` Flask/SocketIO dashboard backend
- `museum-dashboard/src/` React/Vite dashboard source
- systemd service templates and install flow relevant to backend/frontend runtime

Ignored as requested:

- Login/security/auth hardening
- `SceneGen`
- ESP32 firmware/code

Note: This review was done statically on Windows. The RPi runtime was not started.

## Executive Summary

The system already has several good reliability foundations: centralized scene lifecycle state updates, separated MQTT routing, bounded dashboard log history, video process restart logic, and SocketIO status refresh on reconnect.

The biggest reliability risk is state mismatch: the dashboard or controller can believe that a command/scenario succeeded while physical devices did not actually receive or confirm it. This appears in manual MQTT control, scene MQTT actions, feedback tracking, and frontend success handling.

Highest-priority remaining fixes before long unattended operation:

1. Fix `useSceneActions.js` raw `fetch` — the main run scene button is broken for authenticated users.
2. Fix video end detection to use tri-state (`True`/`False`/`None`) so IPC failures cannot trigger spurious scene transitions.
3. Add a scene heartbeat so watchdog does not misclassify long-running scenes (>2h).
4. Bound or degrade the web dashboard restart loop.

Already fixed: manual MQTT API publish result check (✅), frontend non-2xx handling (✅), watchdog systemd ordering (✅), Vite output path (✅).

## Findings

### P2 - Watchdog Can Interrupt A Long Scene

File: `raspberry_pi/watchdog.py`

Lines: 90-96

`main.py` writes the scene state file only when a scene starts and when it ends. `watchdog.py` treats `/tmp/museum_scene_state` as stale after two hours based on file modification time:

```python
age = time.time() - _SCENE_STATE_FILE.stat().st_mtime
if age > 7200:
    log.debug('Scene state file is %.0fs old - treating as idle', age)
    return False

return _SCENE_STATE_FILE.read_text().strip() == 'running'
```

Impact:

- A valid long-running scene can be treated as idle.
- A restart can be allowed while the presentation is still active.
- After `scene_wait_max_seconds`, watchdog can force a restart anyway.

Note on limits of heartbeat alone:

Heartbeat fixes the `mtime > 7200` stale check. There is a second ceiling: `scene_wait_max_seconds = 3600`. If a restart reason occurs during a long scene, the watchdog will wait at most 1 hour and then force-restart regardless of the heartbeat. For truly ambient or multi-hour scenes, the `scene_wait_max_seconds` policy also needs to be reviewed (increase, make configurable, or remove the hard cap entirely).

Recommended fix:

- While a scene is running, periodically touch/rewrite the state file with the same `running` content every 5–10 seconds (e.g. from the `run_scene()` loop in `main.py`).
- Do not change the file format yet — watchdog already reads `running`/`idle` correctly. Switching to JSON requires updating both sides atomically; do that as a follow-up if structured state is needed later.
- Decide on `scene_wait_max_seconds` policy: increase it, make it configurable in `config.ini`, or remove the hard cap if the installation runs ambient scenes.

Acceptance check:

- During a multi-hour scene, watchdog always sees fresh `running` state.
- When the scene stops, heartbeat stops and state changes to `idle`.
- Watchdog never force-restarts mid-scene regardless of how long the scene runs.

### P2 - Web Dashboard Has An Infinite Crash Loop

File: `raspberry_pi/Web/app.py`

Lines: 53-65

The dashboard thread wraps `socketio.run(...)` in an unbounded `while True` loop with a fixed 10 second retry:

```python
while True:
    try:
        socketio.run(...)
    except Exception as e:
        logger.error(f"WEB crashed: {e}. Restarting in 10s...")
        time.sleep(10)
```

Impact:

- Persistent failures can flood logs forever.
- Operators get repeated crash noise instead of a clear degraded-web state.
- Core scene runtime may remain healthy, but the log signal becomes noisy and less useful.

Recommended fix:

- Use bounded fast retries with exponential backoff.
- After retry budget is exhausted, mark web dashboard as degraded.
- Continue low-frequency retry, but log at a controlled interval.

Acceptance check:

- Forced port bind failure produces bounded logs.
- Scene runtime continues normally while web is degraded.

### ✅ P1 - Manual MQTT API Reports Success When Publish Fails — FIXED 2026-04-26

File: `raspberry_pi/Web/routes/commands.py`

Lines: 87-90

`/api/mqtt/send` checks only whether `controller.mqtt_client` exists. It does not check connection state or the return value of `publish(...)`:

```python
if hasattr(controller, 'mqtt_client') and controller.mqtt_client:
    controller.mqtt_client.publish(topic, payload)
    dashboard.log.info(f"Manual MQTT: {topic} -> {payload}")
    return jsonify({'success': True})
```

Impact:

- If MQTT is disconnected, `MQTTClient.publish(...)` returns `False`.
- The API still returns `success: true`.
- The dashboard can tell the operator that a relay/motor command succeeded when it did not.

Recommended fix:

- Check `controller.mqtt_client.is_connected()`.
- Check the boolean return value from `publish(...)`.
- Return `503` or `502` when MQTT publish fails.

Acceptance check:

- With broker down, manual command endpoint returns an error and frontend shows failure.

### P2 - Scene Continues When MQTT Actions Fail

File: `raspberry_pi/utils/state_executor.py`

Lines: 234-248

Scene MQTT actions only log failures. A failed publish does not affect scene progression:

```python
success = self.mqtt_client.publish(topic, message, retain=False)
if success:
    self.logger.debug(f"MQTT: {topic} = {message}")
else:
    self.logger.error(f"MQTT publish failed: {topic}")
```

Impact:

- Audio/video timeline can continue while physical devices did not move.
- A room can end up in a state that does not match the intended scene.
- Operators may only notice through logs or visual inspection.

Recommended fix options:

- For non-critical actions, keep current behavior but report a visible dashboard warning.
- For critical actions, support scene-level policy such as `onMqttFailure: abort|retry|continue`.
- Add retry budget for transient broker hiccups.

Acceptance check:

- A scene with a critical MQTT action can fail fast or enter a known safe state.

### P2 - Feedback Tracking Is Not Correlated To A Specific Command

File: `raspberry_pi/utils/mqtt/mqtt_feedback_tracker.py`

Lines: 140-184

Pending feedbacks are keyed only by `original_topic`. A second command to the same topic replaces the first pending timer:

```python
if original_topic in self.pending_feedbacks:
    self.pending_feedbacks[original_topic]['timer'].cancel()

self.pending_feedbacks[original_topic] = {
    'command': message,
    ...
}
```

Impact:

- Fast consecutive commands to one device can overwrite each other.
- A late `OK` from the first command can confirm the second command.
- UI runtime state and timeout logs can become misleading.

Recommended fix:

- Add a command id/correlation id where possible.
- If ESP protocol cannot include ids yet, store a short per-topic command queue.
- At minimum, log when a pending command is replaced before feedback arrives.

Acceptance check:

- Two fast commands to one topic produce two distinguishable feedback outcomes.

### ✅ P2 - Frontend Does Not Treat Non-2xx HTTP Responses As Errors — FIXED 2026-04-26

File: `museum-dashboard/src/services/api.js`

Lines: 21-25

`authFetch` throws only for `401`:

```javascript
const res = await fetch(url, finalOptions);
if (res.status === 401) {
  throw new Error('Unauthorized');
}
return res;
```

Impact:

- API responses like `400 Scene already running` or `500 Failed to play video` resolve successfully.
- Hooks can show success toasts even when backend returned an error JSON.
- Operators can receive false positive UI feedback.

Recommended fix:

- Throw for every `!res.ok`.
- Parse JSON error payload when available and use its `error` or `message` field.

Acceptance check:

- When backend returns 400/500, toast shows an error and no success state is applied.

### ✅ P2 - Production Frontend Can Drift From Source Frontend — FIXED 2026-04-26

File: `raspberry_pi/Web/routes/main.py`

Lines: 7-21

Flask serves the production dashboard from `raspberry_pi/Web/dist`:

```python
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
```

But the Vite project builds to `museum-dashboard/dist`, and install scripts do not build or copy assets into `raspberry_pi/Web/dist`.

Observed state:

- `raspberry_pi/Web/dist/index.html` references `index-CzRWDGhc.js`.
- `museum-dashboard/dist/index.html` references `index-DJMFS_vi.js`.

Impact:

- Source frontend changes can be tested but not deployed.
- RPi can serve an older UI than the repo source suggests.
- Backend/frontend contract bugs can survive because the runtime UI is not clearly tied to the source build.

Recommended fix:

- Add a documented build/copy step, for example:
  - `cd museum-dashboard && npm run build`
  - copy `museum-dashboard/dist/*` to `raspberry_pi/Web/dist/`
- Or configure Vite `outDir` directly to `../raspberry_pi/Web/dist`.

Acceptance check:

- A clean build updates the exact assets served by Flask.

### ✅ P2 - Watchdog Service Uses Wrong systemd Ordering — FIXED 2026-04-26

File: `raspberry_pi/services/museum-watchdog.service.template`

Lines: 1-3

The watchdog service declares:

```ini
After=museum.service
```

The installer creates the main unit as:

```bash
museum-system.service
```

Impact:

- `After=museum.service` does not order against the real main service.
- Watchdog may start independently from the main service.
- Startup race behavior becomes less predictable.

Recommended fix:

- Change to `After=museum-system.service`.
- Consider `Wants=museum-system.service` if watchdog should pull the main service up.

Acceptance check:

- `systemctl list-dependencies museum-watchdog.service` shows the intended relationship.

### P2 - False Video-End Callback When mpv IPC Fails During Playback

File: `raspberry_pi/utils/video_handler.py`

Lines: 554-575 (`check_if_ended`), 351-407 (`_send_ipc_command`)

When mpv IPC times out or fails during video playback, `_send_ipc_command` calls `_restart_mpv()` before returning. `_restart_mpv()` calls `_stop_current_process()` which sets `currently_playing = None`, then `_start_mpv()` sets `currently_playing = os.path.basename(iddle_image)` (e.g. `"black.png"`). `_send_ipc_command` then returns `False`/`None`. Back in `is_playing()`, this returns `False`. Back in `check_if_ended()`:

```python
is_playing_now = self.is_playing()           # False — IPC failed, mpv restarted
if self.was_playing and not is_playing_now:  # True — we were playing before
    finished_file = self.currently_playing   # "black.png" — set by _restart_mpv
    self.stop_video()
    if self.end_callback and finished_file:
        self.end_callback(finished_file)     # fires with "black.png"
```

There are two distinct failure paths depending on whether `_restart_mpv()` succeeds or is blocked.

**Path A — restart succeeds:** `_stop_current_process()` sets `currently_playing = None`, then `_start_mpv()` sets `currently_playing = os.path.basename(iddle_image)` (e.g. `"black.png"`). The callback fires with `"black.png"`. TransitionManager compares this against the scene's `target` field via exact match (`event == target`), so a transition defined as `{"type": "videoEnd", "target": "ghost2.mp4"}` will **not** fire. The event sits unconsumed in the queue and is cleared on the next state change.

**Path B — restart blocked (cooldown or `max_restart_attempts` exceeded):** `_restart_mpv()` returns early without calling `_stop_current_process()`, so `currently_playing` stays as the original video filename (e.g. `"ghost2.mp4"`). `_send_ipc_command` still returns `None`. `is_playing()` returns `False`. The callback fires with `"ghost2.mp4"` — which **matches the scene's `videoEnd` target exactly** — and triggers an unintended scene state transition mid-video.

Path B is the more dangerous case: it produces a genuine false transition that the state machine will execute.

Impact:

- **Path A (restart succeeds):** spurious `"black.png"` event sits in the queue; no transition fires unless the scene explicitly listens for `"black.png"`.
- **Path B (restart blocked):** the real video filename is registered as ended; the scene jumps to the next state mid-playback as if the video had finished normally.
- In both paths, `stop_video()` is called inside `check_if_ended()` after the callback, sending further IPC commands to a potentially unstable mpv instance.

Why a simple flag does not work:

`_restart_mpv()` is called synchronously inside `_send_ipc_command()` → `is_playing()`. By the time execution returns to `check_if_ended()`, the restart has already completed and any flag set inside `_restart_mpv()` has been cleared. The flag would never be visible at the check point.

A snapshot of `currently_playing` before calling `is_playing()` is better — it catches the common case where restart changed `currently_playing` from the real video to `"black.png"` — but it still misses cases where `_send_ipc_command(..., get_response=True)` returns `None` for an empty response without triggering a restart, or where restart fails due to cooldown/max attempts and `currently_playing` is left as the original video.

Recommended fix:

Change `is_playing()` to return three distinct values instead of `bool`:

- `True` — mpv confirms a real video path via IPC.
- `False` — mpv confirms the idle image is showing or EOF was reached.
- `None` (UNKNOWN) — IPC timed out, returned an empty response, threw an exception, or the restart path was entered for any reason.

Change `check_if_ended()` to only fire the end callback on a confirmed `False` transition:

```python
def check_if_ended(self) -> None:
    result = self.is_playing()   # True | False | None

    if result is None:           # IPC error — do not interpret as video end
        self.was_playing = False # reset so we re-evaluate cleanly next tick
        return

    if self.was_playing and result is False:
        finished_file = self.currently_playing
        self.stop_video()
        if self.end_callback and finished_file:
            self.end_callback(finished_file)

    self.was_playing = (result is True)
```

All paths in `_send_ipc_command` that currently return `False` on error should instead return `None` to allow `is_playing()` to propagate the UNKNOWN signal.

Acceptance check:

- An IPC timeout during video playback produces zero `videoEnd` scene transitions.
- A genuine video end (EOF detected via path property) still fires the callback correctly.
- The scene continues normally after mpv recovers from a restart.

### P2 - Main Scene Button Uses Raw fetch Without Authorization

File: `museum-dashboard/src/hooks/useSceneActions.js`

Line: 41

`runScene()` fetches the configured default scene name from the backend using a raw `fetch()` call instead of `authFetch`:

```javascript
const res = await fetch('/api/config/main_scene');
const config = await res.json();
const sceneName = config.json_file_name || 'intro.json';
```

The `/api/config/main_scene` route is protected by `@requires_auth` (HTTP Basic Auth). Without the `Authorization` header, the backend returns a `401` response with a plain-text body. Calling `res.json()` on a plain-text response throws a `SyntaxError`. The outer `catch` block catches this and shows `toast.error("Chyba konfigurácie: ...")`, but the scene never starts.

All other `api.*` calls in the file go through `authFetch`, which reads the stored token from `localStorage` and injects the `Authorization` header. Only this one call bypasses it.

Impact:

- The main "Run Scene" button fails with a config error toast for every authenticated user.
- `api.stopScene()` and named scene calls work correctly because they use `authFetch`.
- The fallback to `'intro.json'` never triggers because the exception is thrown before `config` is assigned.

Recommended fix:

Add a `getMainSceneConfig()` method to `api.js` that uses `authFetch`, and call it from the hook:

```javascript
// api.js
getMainSceneConfig: async () => {
  const res = await authFetch(`${API_URL}/config/main_scene`);
  return res.json();
},
```

```javascript
// useSceneActions.js
const config = await api.getMainSceneConfig();
```

Do not add a bare `authFetch` import to the hook — keeping all API calls behind the `api` object maintains a single abstraction layer.

Acceptance check:

- Logged-in user clicks "Run Scene" and the presentation starts without a config error.
- With broker down, the scene start attempt fails at the MQTT level, not the config fetch.

### P3 - `broadcast_stop()` Is Called Twice on Every Scene Completion

File: `raspberry_pi/main.py`

Lines: 288-316 (`_run_scene_logic`), 364-410 (`run_scene`)

On every normal scene completion, `broadcast_stop()` is called twice:

1. `run_scene()` calls `self.broadcast_stop()` at line 409 after the processing loop exits.
2. `_run_scene_logic()`'s `finally` block then calls `_set_scene_running(False, ...)` — which returns `True` because `scene_running` is still `True` at that moment — and calls `self.broadcast_stop()` again at line 302.

On external stop via `stop_scene()`, a different double occurs:

1. `stop_scene()` calls `broadcast_stop()` (line 349).
2. `run_scene()`'s loop exits because `scene_running` is now `False`, then calls `broadcast_stop()` again (line 409).

Impact:

- All MQTT devices receive two STOP publishes per scene end.
- STOP is idempotent so this does not cause incorrect physical behavior.
- Log output shows two `Broadcasting STOP signal` lines per scene, which can mislead operators.

Recommended fix:

- Remove the `self.broadcast_stop()` call from inside `run_scene()` (line 409). The `finally` block in `_run_scene_logic` already handles it with the `if transitioned:` guard.

Acceptance check:

- Each scene completion produces exactly one `Broadcasting STOP signal` log line.

### P3 - Web Log Handler Broadcasts Synchronously

File: `raspberry_pi/Web/handlers/log_handler.py`

Lines: 17-33

Each log record directly calls `dashboard.add_log_entry(...)`, which then emits websocket events:

```python
self.dashboard.add_log_entry(log_entry)
```

Impact:

- Runtime threads that log can also perform websocket fanout work.
- Slow/problematic web clients can add latency to logging paths.
- On RPi, this creates avoidable coupling between core runtime and dashboard display.

Recommended fix:

- Queue dashboard log events.
- Drain queue from a dashboard-owned background worker.
- Keep core logging path non-blocking, similar to the existing async SQLite handler.

Acceptance check:

- Heavy logging does not measurably slow scene processing or MQTT callbacks.

## Recommended Fix Order

1. ✅ Fix false success paths — DONE
   - manual MQTT API publish result
   - frontend `authFetch` non-2xx handling

2. ✅ Fix watchdog systemd ordering — DONE

3. ✅ Clean deployment workflow — DONE (Vite outDir points to `raspberry_pi/Web/dist`)

4. Fix main scene button auth — add `api.getMainSceneConfig()` using `authFetch`, call it from `useSceneActions.js`

5. Fix video end detection — tri-state `is_playing()` return (`True`/`False`/`None`)

6. Fix watchdog — periodic `running` heartbeat from `run_scene()` loop + review `scene_wait_max_seconds` policy

7. Remove double `broadcast_stop()` — delete the redundant call from `run_scene()` (line 409)

8. Improve dashboard failure isolation — bounded web restart loop with exponential backoff

9. Decouple log handler from runtime threads — async queue for dashboard WebSocket fanout

10. Improve device command truth (lower priority, no physical impact):
    - visible dashboard warning on MQTT publish failure in scene
    - feedback correlation or per-topic pending queue

## Verification Notes

No RPi runtime tests were run.

Attempted local checks:

- `npm run lint` was blocked by PowerShell script execution policy for `npm.ps1`.
- `npm.cmd run lint` then failed in the sandbox with `EPERM` while accessing `C:\Users\Wajdy\Documents`.
- `python -m compileall` could not run because `python` was not in PATH.
- `py -m compileall` failed with access denied to the local Python executable.

This report is therefore a static code review, not a runtime validation.
