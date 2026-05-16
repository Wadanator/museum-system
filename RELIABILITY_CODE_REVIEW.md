# Museum System - Reliability Code Review

Original date: 2026-04-27
Last updated: 2026-05-16
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

The system has solid reliability foundations: centralized scene lifecycle state updates, separated MQTT routing, bounded dashboard log history, video process restart logic, scene-state heartbeat for the watchdog, tri-state video IPC handling, and SocketIO status refresh on reconnect.

Currently open reliability risks:

1. Scene MQTT publish failure policy is still a design gap for critical hardware actions.
2. Lower-priority issues that are real but less dangerous in normal operation: synchronous dashboard log broadcast, web crash loop, MQTT feedback ambiguity.

Already fixed (condensed list — short summaries under each closed finding below):

- Audio not stopped on scene exception path — `_run_scene_logic.finally` now calls `stop_audio()` unconditionally.
- pygame fadeout click — `time.sleep(0.1)` → `time.sleep(0.5)` so the 500 ms fade completes before `stop()`.
- Main scene button auth fetch.
- Duplicate scene STOP broadcast.
- MQTT falsey payload validation.
- Video end detection no longer treats IPC unknown as confirmed EOF.
- Web log handler exception isolation.
- Manual MQTT API publish result check.
- Frontend `authFetch` non-2xx handling.
- Watchdog systemd `After=` ordering.
- Vite output path now points directly to `raspberry_pi/Web/dist`.
- Watchdog long-scene protection: scene-state heartbeat plus configurable `scene_wait_max_seconds` and `_SCENE_STATE_STALE_SECONDS`.

Important nuance: the Vite output path is fixed, but deployment is not fully enforced because the install scripts still do not run `npm run build`. If source changes are made and the build step is skipped, Flask can still serve stale assets from `raspberry_pi/Web/dist`.

## Findings

### [FIXED] P1 - Audio Not Stopped When Scene Thread Exits Via Exception

File: `raspberry_pi/main.py` — `_run_scene_logic()` finally block

**Problem:** When `run_scene()` raised an exception, the `finally` block stopped video, reset scene state, and broadcast MQTT STOP — but never called `audio_handler.stop_audio()`. On a clean scene end, `END.onEnter` normally issues the audio `STOP` action. On the exception path that action never runs, so music kept playing on the Pi's speakers until the next button press.

**Fix:** `_run_scene_logic.finally` now calls `audio_handler.stop_audio()` unconditionally (inside its own try/except) before the rest of cleanup. All three exit paths — clean end, external stop, and exception — now stop audio consistently.

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

Falsey-payload sub-issue: previously `if not topic or not message:` rejected valid payloads `0` and `False`. Already fixed — the guard now correctly accepts those values.

Recommended fix:

- Keep default policy as `continue` for backward compatibility.
- Add optional scene-level policy, for example `onMqttFailure: continue|retry|abort`.
- Surface failed scene MQTT publishes visibly in the dashboard.

Acceptance check:

- Existing scenes keep current behavior unless they opt into stricter failure policy.
- A critical MQTT action can retry, abort, or enter a known safe state.

Verdict: real design gap. P2 for critical hardware actions, otherwise P3/feature-level.

### [FIXED] P3 - Music Stop Fadeout Is Cut Short, Producing An Audible Click

File: `raspberry_pi/utils/audio_handler.py` — `stop_all()`

**Problem:** `fadeout(500)` schedules a 500 ms async fade, but `time.sleep(0.1)` waited only 100 ms before `stop()` cut playback at ~80 % volume — producing an audible click on every scene loop end.

**Fix:** `time.sleep(0.1)` → `time.sleep(0.5)`. The fade now completes before `stop()` is called.

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

### P3 - Feedback Tracking Is Not Correlated To A Specific Command - NOT CRITICAL FOR NOW

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

### [PARTLY FIXED] Production Frontend Can Drift From Source Frontend

Files:

- `museum-dashboard/vite.config.js`
- `raspberry_pi/Web/routes/main.py`
- `raspberry_pi/install.sh`
- `raspberry_pi/install_offline.sh`

Verified current state:

- Vite output path now points directly to `raspberry_pi/Web/dist`. The previous two-`dist` mismatch is structurally fixed.
- Install scripts still do not run `npm run build`. If a developer changes frontend source and forgets to build, Flask serves stale built assets.

Recommended fix:

- Document the required frontend build step in the deployment flow.
- Preferably add a controlled build step to install/release scripts, or add a CI/release check that verifies `raspberry_pi/Web/dist` is current after frontend changes.

Acceptance check:

- A clean deployment process always serves assets generated from current `museum-dashboard/src`.

Verdict: path drift fixed; deployment enforcement still open.

### [PARTLY FIXED] P3 - Web Log Handler Broadcasts Synchronously

Files:

- `raspberry_pi/Web/handlers/log_handler.py`
- `raspberry_pi/Web/dashboard.py`

Original problem:

- `WebLogHandler.emit()` called `dashboard.add_log_entry(...)` which iterated SocketIO sessions and emitted log events synchronously.
- Runtime threads that logged were therefore performing dashboard websocket fanout work.
- A dashboard exception could escape back into the runtime thread that called `log.info(...)`.

What was changed:

- `WebLogHandler.emit()` now isolates exceptions raised by the dashboard via the standard `logging.Handler` failure path, so a dashboard fault no longer propagates into runtime threads.

Still open:

- Synchronous fanout to SocketIO clients remains. With one or two LAN clients the practical risk is low, but a slow client can still add latency to whichever thread is logging at that moment.

Recommended fix:

- Put dashboard log events into a bounded queue and drain them from a dashboard-owned background worker.
- Drop or coalesce old log events if the queue is full.

Verdict: exception isolation done; full async decoupling remains a low-urgency P3.

## Closed Findings (Already Fixed)

These were previously analysed in detail. Implementation specifics have been removed; the problem statement is kept for traceability.

### [FIXED] P2 - Main Scene Button Used Raw fetch Without Authorization

The dashboard's main "Run Scene" button used a raw `fetch('/api/config/main_scene')` that did not attach the Basic Auth header stored in `localStorage`. The endpoint is `@requires_auth`, so the request returned 401 plain-text, the JSON parse threw, the outer `catch` showed a config error toast, and the scene never started. The fallback to `intro.json` also never ran because the exception fired before `config` existed.

Fix: route the call through the authenticated API helper and rebuild the production frontend bundle.

### [FIXED] P2 - False Video-End Callback When mpv IPC Fails During Playback

`is_playing()` returned `False` both for a genuine ended/idle video and for unknown IPC states (timeout, empty response, exception, blocked restart). `check_if_ended()` treated `False` as a confirmed video end and could fire the end callback with the original video filename, which `TransitionManager` then matched against a `videoEnd` transition target — causing live scenes to jump forward as if the video had finished naturally.

Fix: `is_playing()` now distinguishes confirmed-playing, confirmed-idle, and unknown. End callbacks fire only on confirmed-idle.

### [FIXED] P2 - Watchdog Could Interrupt A Long Scene

Watchdog had no scene heartbeat, treated the state file as stale after a fixed window, and capped scene-wait time at one hour. A long scene could therefore be force-restarted mid-playback.

Fix: main.py now writes a periodic `running` heartbeat under the scene lock while a scene is active; watchdog reads `scene_wait_max_seconds` from config; the stale threshold is a named constant.

### [FIXED] Manual MQTT API Reports Success When Publish Fails

Manual MQTT command endpoint always returned `success: true` even when the broker was disconnected and `MQTTClient.publish()` returned False.

Fix: the publish wrapper return value is now checked and the API returns an HTTP error when publish fails. (This is local-broker delivery success, not hardware acknowledgement.)

### [FIXED] Frontend Does Not Treat Non-2xx HTTP Responses As Errors

`authFetch()` previously returned non-2xx responses as if they were successes, so backend `400/500/503` could end up driving success UI state.

Fix: `authFetch()` now throws on every non-OK response and attempts to parse a backend JSON error.

### [FIXED] Watchdog Service Used Wrong systemd Ordering

The watchdog unit's `After=` clause did not match the installed main service name, so unit ordering at boot was unreliable.

Fix: the `After=` value now matches the installed main service name.

### [FIXED] P3 - broadcast_stop() Was Called Twice

Both normal completion and external stop produced two `broadcast_stop()` calls. STOP is idempotent so physical behaviour stayed correct, but logs showed duplicate entries.

Fix: the redundant call inside `run_scene()` was removed; `_run_scene_logic.finally` and `stop_scene()` are now the single sources of STOP broadcast.

### [FIXED] MQTT Action Falsey Payload Validation

`_execute_mqtt()` previously rejected valid payloads `0` and `False` because of an `if not topic or not message:` guard.

Fix: the guard now treats only `None` and empty string as missing, while preserving `0` and `False` as valid payloads.

## Recommended Fix Order

1. Improve dashboard failure isolation — bounded retry/backoff/degraded state for web dashboard startup crashes.
3. Decouple dashboard log broadcasting — add async bounded queue for web log events. Exception isolation already done.
4. Improve scene MQTT failure handling — add optional `onMqttFailure` policy for critical actions.
5. Improve feedback truth — add correlation IDs when the ESP protocol can support it, or add a per-topic queue/warning fallback.
6. Enforce frontend build in install/release flow.

## Final Verdict

- Audio-not-stopped-on-scene-exception: fixed.
- Web crash loop is real but P3 by default.
- Scene MQTT failure behaviour is a design gap; P2 only for critical hardware actions.
- Feedback correlation is real but usually P3 because physical command delivery is not directly affected.
- Web log handler exception isolation is done; async queue/fanout decoupling remains.
- Vite output path is fixed; deployment enforcement is only partly fixed.
- Video-end tri-state and watchdog scene heartbeat are now in place and resolved.

## Verification Notes

No Raspberry Pi runtime tests were run.

This review was verified statically against the current repository state on Windows. The conclusions above are based on direct source inspection, not live hardware behavior.
