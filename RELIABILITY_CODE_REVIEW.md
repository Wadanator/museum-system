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

Highest-priority fixes before long unattended operation:

1. Add a scene heartbeat so watchdog does not misclassify long-running scenes.
2. Bound or degrade the web dashboard restart loop.
3. Make manual MQTT API return failure when publish fails.
4. Make frontend treat non-2xx API responses as errors.
5. Fix the watchdog systemd ordering.

## Findings

### P1 - Watchdog Can Interrupt A Long Scene

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

Recommended fix:

- Write a heartbeat while the scene is running, for example every 5-10 seconds.
- Store structured state, such as `{"state": "running", "updated_at": ...}`.
- Keep backward compatibility for the current plain `running`/`idle` format during rollout.

Acceptance check:

- During a multi-hour scene, watchdog always sees fresh running state.
- When the scene stops, heartbeat stops and state changes to idle.

### P1 - Web Dashboard Has An Infinite Crash Loop

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

1. Fix false success paths:
   - manual MQTT API publish result
   - frontend `authFetch` non-2xx handling

2. Fix watchdog safety:
   - scene heartbeat
   - correct systemd `After=`

3. Improve dashboard failure isolation:
   - bounded web restart loop
   - explicit degraded-web state

4. Improve device command truth:
   - feedback correlation or per-topic pending queue
   - visible MQTT failure policy for critical scene actions

5. Clean deployment workflow:
   - one build path for the production dashboard assets
   - document or automate copying frontend build into `raspberry_pi/Web/dist`

## Verification Notes

No RPi runtime tests were run.

Attempted local checks:

- `npm run lint` was blocked by PowerShell script execution policy for `npm.ps1`.
- `npm.cmd run lint` then failed in the sandbox with `EPERM` while accessing `C:\Users\Wajdy\Documents`.
- `python -m compileall` could not run because `python` was not in PATH.
- `py -m compileall` failed with access denied to the local Python executable.

This report is therefore a static code review, not a runtime validation.
