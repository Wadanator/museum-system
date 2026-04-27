# Museum System - Reliability Code Review

Date: 2026-04-27
Scope: Raspberry Pi backend and web dashboard/frontend
Review type: static code review on Windows; Raspberry Pi runtime was not started

## Scope

Reviewed:

- `raspberry_pi/` backend runtime
- `raspberry_pi/Web/` Flask/SocketIO dashboard backend
- `museum-dashboard/src/` React/Vite dashboard source
- systemd service templates and install flow relevant to backend/frontend runtime

Ignored:

- Login/security/auth hardening
- `SceneGen`
- ESP32 firmware/code

## Executive Summary

The system already has useful reliability foundations: centralized scene lifecycle state updates, separated MQTT routing, bounded dashboard log history, video process restart logic, and SocketIO status refresh on reconnect.

The strongest remaining reliability risks are false state and scene-control ambiguity:

1. `video_handler.py` collapses mpv IPC failure into "video is not playing", so IPC errors can be interpreted as a natural video end.
2. Watchdog long-scene protection is incomplete: no scene heartbeat exists, and `scene_wait_max_seconds = 3600` can still force a restart during a long scene.
3. Several lower-priority issues are real but less dangerous in normal operation: synchronous dashboard log broadcast, web crash loop, and MQTT feedback ambiguity.

Already fixed in current code:

- Main scene button auth fetch.
- Duplicate scene STOP broadcast.
- MQTT falsey payload validation.
- Web log handler exception isolation.
- Manual MQTT API publish result check.
- Frontend `authFetch` non-2xx handling.
- Watchdog systemd `After=` ordering.
- Vite output path now points directly to `raspberry_pi/Web/dist`.

Important nuance: the Vite output path is fixed, but deployment is not fully enforced because the install scripts still do not run `npm run build`. If source changes are made and the build step is skipped, Flask can still serve stale assets from `raspberry_pi/Web/dist`.

## Findings

### [FIXED] P2 - Main Scene Button Used Raw fetch Without Authorization

Files:

- `museum-dashboard/src/hooks/useSceneActions.js`
- `museum-dashboard/src/services/api.js`
- `raspberry_pi/Web/routes/scenes.py`
- `raspberry_pi/Web/auth.py`

Original verified code:

- `useSceneActions.js` called raw `fetch('/api/config/main_scene')`.
- `scenes.py` protects `/api/config/main_scene` with `@requires_auth`.
- `auth.py` reads credentials from `request.authorization`.
- `api.js` had `authFetch`, but no `getMainSceneConfig()` wrapper.

Original hook behavior:

```javascript
const res = await fetch('/api/config/main_scene');
const config = await res.json();
const sceneName = config.json_file_name || 'intro.json';
```

Why this failed:

- The logged-in frontend stores the Basic Auth header in `localStorage`.
- Raw `fetch()` does not attach that header.
- Backend returns `401` with a plain-text body.
- `res.json()` then throws a JSON parse error.
- The outer `catch` shows a config error toast and the scene never starts.

Impact before fix:

- The main "Run Scene" button fails for authenticated users.
- Named scene calls and `stopScene()` work because they go through `api.*` methods using `authFetch`.
- The fallback to `intro.json` does not run because the exception occurs before `config` exists.
- The current built production asset in `raspberry_pi/Web/dist` also contains the raw fetch, so the deployed dashboard is affected.

Implemented fix:

- Added `getMainSceneConfig()` to `museum-dashboard/src/services/api.js`.
- The new method uses `authFetch`.
- `useSceneActions.js` now calls `api.getMainSceneConfig()` instead of raw `fetch`.
- Frontend production bundle was rebuilt after the source change, so `raspberry_pi/Web/dist` contains the fix.

Implemented source shape:

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

Do not import `authFetch` directly into the hook unless the existing API abstraction is intentionally being changed. Keeping route calls behind the `api` object is cleaner and consistent with the rest of the file.

Acceptance check:

- Logged-in user clicks the main run button and the configured scene starts.
- If scene start later fails because of MQTT or backend state, the error is from that later layer, not from config fetch.

Verdict: fixed in source and rebuilt into `raspberry_pi/Web/dist` on 2026-04-27.

### P2 - False Video-End Callback When mpv IPC Fails During Playback

Files:

- `raspberry_pi/utils/video_handler.py`
- `raspberry_pi/utils/scene_parser.py`
- `raspberry_pi/utils/transition_manager.py`

Verified code areas:

- `video_handler.py`: `_restart_mpv()`
- `video_handler.py`: `_send_ipc_command()`
- `video_handler.py`: `check_if_ended()`
- `video_handler.py`: `is_playing()`
- `scene_parser.py`: `_on_video_ended()`
- `transition_manager.py`: `_check_video_end()`

Current problem:

`is_playing()` returns `False` both for a genuine ended/idle video and for unknown IPC states, including timeout, empty response, exception, and blocked restart paths. `check_if_ended()` treats `False` as a confirmed video end:

```python
is_playing_now = self.is_playing()

if self.was_playing and not is_playing_now:
    finished_file = self.currently_playing
    self.stop_video()
    if self.end_callback and finished_file:
        self.end_callback(finished_file)
```

There are two important failure paths.

Path A - restart succeeds:

- IPC fails.
- `_send_ipc_command()` calls `_restart_mpv()`.
- `_restart_mpv()` calls `_stop_current_process()`, then `_start_mpv()`.
- `currently_playing` usually becomes the idle image basename, for example `black.png`.
- Callback fires with `black.png`.
- `TransitionManager` checks video-end events using exact match against the transition target.
- A transition like `{"type": "videoEnd", "target": "ghost2.mp4"}` normally will not fire.

Path A is still wrong, but it usually does not advance a normal scene.

Path B - restart is blocked or IPC returns no usable response:

- IPC fails, returns empty response, or `_restart_mpv()` returns early due to cooldown or max restart attempts.
- `currently_playing` can remain the original video filename, for example `ghost2.mp4`.
- `is_playing()` returns `False`.
- `check_if_ended()` fires the callback with `ghost2.mp4`.
- `TransitionManager` sees `event == target` and can execute a false `videoEnd` transition.

Path B is the dangerous case: a live scene can jump forward as if the video finished naturally.

Why a simple restart flag is not enough:

- `_restart_mpv()` is called synchronously inside `_send_ipc_command()` and `is_playing()`.
- By the time execution returns to `check_if_ended()`, a flag set and cleared inside `_restart_mpv()` would already be cleared.
- `check_if_ended()` would not see that flag.

Why a `currently_playing` snapshot is helpful but insufficient:

- Snapshotting before `is_playing()` catches the common path where restart changes `currently_playing` from the real video to `black.png`.
- It does not catch empty IPC responses that do not restart mpv.
- It does not catch restart-blocked paths where `currently_playing` remains the original filename.

Recommended fix:

Change `is_playing()` from `bool` to a tri-state result:

- `True`: mpv confirms a real non-idle video path via IPC.
- `False`: mpv confirms idle/ended state.
- `None`: state is unknown because IPC failed, timed out, returned empty response, threw an exception, or entered a restart/error path.

Then change `check_if_ended()` so it only fires the callback on confirmed `False`, never on `None`:

```python
def check_if_ended(self) -> None:
    result = self.is_playing()  # True | False | None

    if result is None:
        # IPC/health state is unknown. Do not interpret this as a natural EOF.
        self.was_playing = False
        return

    if self.was_playing and result is False:
        finished_file = self.currently_playing
        self.stop_video()
        if self.end_callback and finished_file:
            self.end_callback(finished_file)

    self.was_playing = (result is True)
```

Implementation note:

- Be careful when changing `_send_ipc_command()` return values globally. Many callers only need truthy/falsy command success. The critical behavior is that `is_playing()` must be able to distinguish confirmed idle/end from unknown IPC failure.
- A robust implementation can keep `_send_ipc_command()` mostly compatible and add explicit handling in `is_playing()` for `None`/empty/error responses.
- Resetting `was_playing` on `None` avoids false transitions. The tradeoff is that a real EOF during an IPC outage may not fire immediately, which is safer than a false mid-scene jump.

Acceptance check:

- Simulated IPC timeout during video playback produces zero `videoEnd` scene transitions.
- Simulated empty IPC response produces zero `videoEnd` scene transitions.
- Simulated restart blocked by cooldown/max attempts produces zero false `videoEnd` transitions.
- A genuine completed video still fires exactly one callback with the correct filename.

Verdict: real P2 reliability bug. Fix with tri-state/unknown handling.

### P2 - Watchdog Can Interrupt A Long Scene

Files:

- `raspberry_pi/main.py`
- `raspberry_pi/watchdog.py`

Verified code:

- `main.py` writes `/tmp/museum_scene_state` only in `_set_scene_running()`.
- The scene loop in `run_scene()` does not heartbeat or touch the state file.
- `watchdog.py` treats the state file as stale after 7200 seconds.
- `watchdog.py` also has `scene_wait_max_seconds = 3600`.

Current watchdog logic:

```python
age = time.time() - _SCENE_STATE_FILE.stat().st_mtime
if age > 7200:
    log.debug('Scene state file is %.0fs old - treating as idle', age)
    return False

return _SCENE_STATE_FILE.read_text().strip() == 'running'
```

Impact:

- A valid multi-hour scene can be treated as idle after the file mtime becomes stale.
- A watchdog restart can be allowed while the scene is still active.
- Even with a heartbeat, the one-hour `scene_wait_max_seconds` cap can still force restart if a restart reason appears during a long scene.

Recommended fix:

- While a scene is running, periodically rewrite or touch `/tmp/museum_scene_state` with the same `running` content.
- Keep the current plain `running`/`idle` format for now. JSON state would require an atomic update on both writer and reader.
- Review `scene_wait_max_seconds`: make it configurable, increase it, or remove the hard cap for ambient/multi-hour installations.

Acceptance check:

- During a multi-hour scene, watchdog always sees a fresh `running` state file.
- When the scene stops, heartbeat stops and state changes to `idle`.
- Watchdog does not force-restart mid-scene solely because a long scene exceeded one hour.

Verdict: real P2. It needs multiple conditions to trigger, but the outcome is severe enough to fix before unattended long-scene operation.

### P3 - Web Dashboard Has An Infinite Crash Loop

File:

- `raspberry_pi/Web/app.py`

Verified code:

`socketio.run(...)` is wrapped in an unbounded `while True` loop. On every exception, it logs an error and retries after 10 seconds.

Impact:

- Persistent bind/runtime failure creates endless repeated error logs.
- Operators get noisy failure output instead of a clear degraded dashboard state.
- Core scene runtime does not directly crash from this path, so this is not P1.

Recommended fix:

- Use bounded fast retries with exponential backoff.
- After the fast retry budget is exhausted, mark dashboard as degraded.
- Continue low-frequency retry with rate-limited logging.

Acceptance check:

- Forced web bind failure does not flood logs indefinitely.
- Scene runtime continues normally while web dashboard is degraded.

Verdict: real issue, but P3 by default. It can be treated as P2 only if dashboard availability is operationally critical.

### [FIXED] Manual MQTT API Reports Success When Publish Fails

Files:

- `raspberry_pi/Web/routes/commands.py`
- `raspberry_pi/utils/mqtt/mqtt_client.py`

Current code now checks the boolean return value from `controller.mqtt_client.publish(...)` and returns `503` when publish fails. `MQTTClient.publish()` returns `False` when disconnected, when paho returns a nonzero result code, or on exception.

Important limit:

- This confirms local MQTT publish success, not physical hardware acknowledgement.
- Hardware acknowledgement still depends on feedback topics and the feedback tracker.

Acceptance check:

- With broker disconnected, manual MQTT command returns an HTTP error instead of `success: true`.

Verdict: fixed at publish-wrapper level.

### P2/P3 - Scene Continues When MQTT Actions Fail

File:

- `raspberry_pi/utils/state_executor.py`

Verified code:

`_execute_mqtt()` logs failed publish but does not stop or alter scene progression:

```python
success = self.mqtt_client.publish(topic, message, retain=False)
if success:
    self.logger.debug(f"MQTT: {topic} = {message}")
else:
    self.logger.error(f"MQTT publish failed: {topic}")
```

Impact:

- Audio/video timeline can continue while physical devices did not move.
- This is safe as a backward-compatible default for existing scenes.
- For critical relay/motor actions, it can desynchronize the physical room from the scene timeline.

Additional small bug - fixed:

`_execute_mqtt()` checks:

```python
if not topic or not message:
```

That treated valid falsey payloads such as `0` or `False` as missing. The schema allows string, number, and boolean messages.

Implemented fix:

```python
if not topic or message is None or (isinstance(message, str) and message == ""):
```

This keeps `None` and empty string invalid, while allowing valid payloads `0` and `False`.

Recommended fix:

- Keep default policy as `continue` for backward compatibility.
- Add optional scene-level policy, for example `onMqttFailure: continue|retry|abort`.
- Surface failed scene MQTT publishes visibly in the dashboard.

Acceptance check:

- Existing scenes keep current behavior unless they opt into stricter failure policy.
- A critical MQTT action can retry, abort, or enter a known safe state.
- Payloads `0` and `False` are not rejected as missing.

Verdict: real design gap. P2 for critical hardware actions, otherwise P3/feature-level.

### P3 - Feedback Tracking Is Not Correlated To A Specific Command

File:

- `raspberry_pi/utils/mqtt/mqtt_feedback_tracker.py`

Verified code:

Pending feedback is keyed only by `original_topic`. A second command to the same topic cancels and replaces the first pending timer:

```python
if original_topic in self.pending_feedbacks:
    self.pending_feedbacks[original_topic]['timer'].cancel()

self.pending_feedbacks[original_topic] = {
    'command': message,
    ...
}
```

Impact:

- Two fast commands to the same topic cannot be distinguished.
- A late `OK` from the first command can confirm the second command.
- Runtime state and timeout logs can become misleading.
- Physical impact is usually low because both MQTT publishes already happened.

Recommended fix:

- Best fix: add command IDs/correlation IDs to the ESP protocol.
- If protocol cannot change yet, keep a short per-topic pending queue.
- At minimum, log a warning when replacing an unresolved pending feedback entry.

Acceptance check:

- Two fast commands to one topic produce two distinguishable outcomes or an explicit warning that correlation is not guaranteed.

Verdict: real P3. It can become P2 if dashboard truth is used for safety-critical operator decisions.

### [FIXED] Frontend Does Not Treat Non-2xx HTTP Responses As Errors

File:

- `museum-dashboard/src/services/api.js`

Current `authFetch()` now throws for every `!res.ok` and attempts to parse backend JSON error fields.

Acceptance check:

- Backend `400`, `500`, and `503` responses do not produce success UI state.

Verdict: fixed.

### [PARTLY FIXED] Production Frontend Can Drift From Source Frontend

Files:

- `museum-dashboard/vite.config.js`
- `raspberry_pi/Web/routes/main.py`
- `raspberry_pi/install.sh`
- `raspberry_pi/install_offline.sh`

Verified current state:

- Vite is configured with `outDir: '../raspberry_pi/Web/dist'`.
- Flask serves assets from `raspberry_pi/Web/dist`.
- The old separate `museum-dashboard/dist` output path is no longer the active build target.
- Install scripts create services but do not run `npm run build`.

Impact:

- The previous two-dist mismatch is structurally fixed.
- Source changes can still fail to reach production if the build step is skipped.
- Built assets in `raspberry_pi/Web/dist` remain the source of truth for Flask runtime.

Recommended fix:

- Document the required frontend build step in the deployment flow.
- Preferably add a controlled build step to install/release scripts, or add a CI/release check that verifies `raspberry_pi/Web/dist` is current after frontend changes.

Acceptance check:

- A clean deployment process always serves assets generated from current `museum-dashboard/src`.

Verdict: path drift fixed, deployment enforcement only partly fixed.

### [FIXED] Watchdog Service Uses Wrong systemd Ordering

File:

- `raspberry_pi/services/museum-watchdog.service.template`

Current code:

```ini
After=museum-system.service
```

This now matches the installed main service name.

Note:

- `Wants=museum-system.service` is optional. The current watchdog loop can start the service when it sees it inactive, so `Wants=` is not required for correctness.

Verdict: fixed.

### [FIXED] P3 - broadcast_stop() Was Called Twice

File:

- `raspberry_pi/main.py`

Original verified paths:

Normal completion:

1. `run_scene()` exits the processing loop and calls `broadcast_stop()`.
2. `_run_scene_logic()` then runs its `finally` block, transitions scene state to idle, and calls `broadcast_stop()` again.

External stop:

1. `stop_scene()` transitions state to idle and calls `broadcast_stop()`.
2. `run_scene()` sees `scene_running == False`, exits, and calls `broadcast_stop()` again.

Impact before fix:

- All MQTT devices can receive duplicate STOP messages.
- STOP appears idempotent, so physical behavior should remain correct.
- Logs show duplicate "Broadcasting STOP signal" entries, which makes debugging noisier.

Implemented fix:

- Removed the redundant `broadcast_stop()` call from inside `run_scene()`.
- Current call graph is safe because `_run_scene_logic().finally` handles normal completion and `stop_scene()` handles external stop.
- `run_scene()` is currently called only from `_run_scene_logic()`.

Acceptance check:

- Normal scene completion produces one STOP broadcast.
- External stop produces one STOP broadcast.

Verdict: fixed on 2026-04-27.

### [PARTLY FIXED] P3 - Web Log Handler Broadcasts Synchronously

Files:

- `raspberry_pi/Web/handlers/log_handler.py`
- `raspberry_pi/Web/dashboard.py`

Verified path:

- `WebLogHandler.emit()` calls `dashboard.add_log_entry(...)`.
- `add_log_entry()` appends to the log buffer and calls `_broadcast_event('new_log', ...)`.
- `_broadcast_event()` iterates connected SocketIO sessions and calls `socketio.emit(...)`.

Impact:

- Runtime threads that log can perform dashboard websocket fanout work.
- With 1-2 LAN clients, practical blocking risk is probably low.
- Architecturally, this couples core runtime logging to dashboard delivery.

Implemented small fix:

- `WebLogHandler.emit()` now catches exceptions raised by `dashboard.add_log_entry(...)`.
- It routes those exceptions through `self.handleError(record)`, which is the standard `logging.Handler` failure path.
- A dashboard exception therefore should not escape back into the runtime thread that called `log.info(...)`.

Recommended fix:

- Put dashboard log events into a bounded queue.
- Drain that queue from a dashboard-owned background worker.
- Drop or coalesce old log events if the queue is full.
- Full async queue/fanout decoupling remains open.

Acceptance check:

- Heavy logging does not measurably slow scene processing or MQTT callbacks.
- A dashboard exception does not escape through logging.
- A slow dashboard client still can add synchronous latency until the async queue is implemented.

Verdict: exception isolation fixed on 2026-04-27; synchronous fanout remains a low-urgency P3 architecture issue.

## Recommended Fix Order

1. Main scene button auth - DONE:
   - Add `api.getMainSceneConfig()` using `authFetch`.
   - Replace raw `fetch('/api/config/main_scene')`.
   - Rebuild frontend into `raspberry_pi/Web/dist`.

2. Fix video end detection:
   - Change `is_playing()` to distinguish `True`, `False`, and `None`.
   - Fire `videoEnd` callback only on confirmed `False`.

3. Fix watchdog long-scene behavior:
   - Add periodic `running` heartbeat while a scene is active.
   - Review or configure `scene_wait_max_seconds`.

4. Remove duplicate STOP - DONE:
   - Delete the redundant `broadcast_stop()` call from `run_scene()`.

5. Improve dashboard failure isolation:
   - Add bounded retry/backoff/degraded state for web dashboard startup crashes.

6. Decouple dashboard log broadcasting:
   - Exception isolation is DONE.
   - Add async bounded queue for web log events.

7. Improve scene MQTT failure handling:
   - Add optional retry/abort/continue policy.
   - Falsey MQTT payload handling is DONE.

8. Improve feedback truth:
   - Add correlation IDs when ESP protocol can support it, or add a per-topic queue/warning fallback.

## Final Verdict

The review findings are mostly real. The important corrections are:

- Web crash loop is real, but P3 by default, not P1/P2.
- Scene MQTT failure behavior is a design gap; P2 only for critical hardware actions.
- MQTT falsey payload validation is fixed, but scene-level MQTT failure policy remains open.
- Feedback correlation is real but usually P3 because physical command delivery is not directly affected.
- Web log handler exception isolation is fixed, but async queue/fanout decoupling remains open.
- Vite output path is fixed, but deployment enforcement is only partly fixed.
- The video-end issue is a real P2, and the correct fix is tri-state/unknown handling, not only a restart flag or filename snapshot.
- The main scene button raw fetch was a real P2 user-facing bug and is now fixed in source.

## Verification Notes

No Raspberry Pi runtime tests were run.

This review was verified statically against the current repository state on Windows. The conclusions above are based on direct source inspection, not live hardware behavior.
