# Museum System - Reliability Code Review

Original date: 2026-04-27
Last updated: 2026-05-06
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

1. **Audio is not stopped when the scene thread exits via an exception path** — silently leaves music streaming after a crash until the next scene start. New finding 2026-05-06, applies directly to the looped SceneV01 use case.
2. Scene MQTT publish failure policy is still a design gap for critical hardware actions.
3. Lower-priority issues that are real but less dangerous in normal operation: synchronous dashboard log broadcast, web crash loop, MQTT feedback ambiguity, and pygame `fadeout`/`stop` mismatch causing an audible click on every scene loop.

Already fixed (condensed list — short summaries under each closed finding below):

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

### P1 - Audio Not Stopped When Scene Thread Exits Via Exception (NEW 2026-05-06)

File:

- `raspberry_pi/main.py` — `_run_scene_logic()` finally block (≈ lines 340–353)

Verified code:

```python
try:
    self.run_scene()
except Exception as e:
    log.error(f"An error occurred during scene execution: {e}")
finally:
    # 1. Vypneme video
    if self.video_handler:
        self.video_handler.stop_video()

    # 2. Reset príznaku behu a broadcast STOP
    transitioned = self._set_scene_running(False, f"scene_thread_finally:{scene_filename}")
    if transitioned:
        if self.actuator_state_store:
            self.actuator_state_store.force_all_off(source='scene_end')
        self.broadcast_stop()
    ...
```

The `finally` branch stops video, transitions scene state to idle, force-offs the actuator state store, and publishes the MQTT STOP broadcast. It does **not** call `audio_handler.stop_all()`.

By contrast both `stop_scene()` and `cleanup()` *do* explicitly stop audio. The exception path is the asymmetric one.

Why audio still normally stops on a clean run:

- A scene that completes via the `END` state relies on `END.onEnter` containing `{"action": "audio", "message": "STOP"}` to silence the speakers.
- `broadcast_stop()` only publishes `<room_id>/STOP` over MQTT. Audio runs locally on the Pi, so MQTT STOP never silences it.

Why this fails in the exception path:

- If `run_scene()` raises (unexpected `state_executor` error, transition glitch, audio handler exception, anything), control jumps to `finally` *before* `END.onEnter` ever runs.
- The `END` state's `audio: STOP` action never fires.
- `finally` does not stop audio either.
- Result: music (e.g. SceneV01's `atmosfera.wav` stream) keeps playing on the Pi's speakers indefinitely.
- Recovery only happens at the next scene start, when `preload_files_for_scene()` calls `stop_all()`.

Impact for the looped SceneV01 use case:

- Hardware (lights, motors, smoke, relays) is correctly turned off via `actuator_state_store.force_all_off()` and `broadcast_stop()`.
- Audio remains live until a person presses the button again. In an unattended ambient installation the room can be silent-with-speakers-on for an unbounded amount of time.
- A single transient scene-thread exception is therefore enough to cause an audible reliability failure for visitors.

Recommended fix:

- In `_run_scene_logic.finally`, before stopping video and transitioning state, call `audio_handler.stop_all()` inside its own try/except so a failing audio shutdown still does not block the rest of the cleanup.
- Optionally also force `actuator_state_store.force_all_off()` and `broadcast_stop()` even when `transitioned` is False, so external `stop_scene()` followed by an exception does not leave the system in a half-stopped state. (Lower priority — `stop_scene()` already covers that path.)

Acceptance check:

- Inject an exception inside `run_scene()` (e.g. force-throw during state processing).
- Observed: audio is silenced as soon as the scene thread exits, not at the next button press.
- Hardware actuators are still turned off as before.

Verdict: real P1 for unattended looped operation. Small, surgical fix.

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

### P3 - Music Stop Fadeout Is Cut Short, Producing An Audible Click (NEW 2026-05-06)

File:

- `raspberry_pi/utils/audio_handler.py` — `stop_all()`

Verified code:

```python
if pygame.mixer.music.get_busy():
    self.logger.info("Stopping music stream...")
    pygame.mixer.music.fadeout(500)
    time.sleep(0.1)
    pygame.mixer.music.stop()
```

`pygame.mixer.music.fadeout(ms)` schedules a fade running asynchronously over 500 ms. The subsequent `time.sleep(0.1)` waits only 100 ms, then `pygame.mixer.music.stop()` cuts playback immediately. The fade is therefore aborted at roughly 20 % completion (still around 80 % volume), producing an audible click on the speakers every time `stop_all()` runs.

Why this matters for the looped SceneV01 use case:

- Every scene end runs `END.onEnter`'s `audio: STOP` action, which calls `handle_command("STOP")` → `stop_all()`.
- Every next scene start runs `preload_files_for_scene()` which also calls `stop_all()`.
- For a museum installation looping a single scene, this means an audible click on the speakers on every loop transition. It is the most visitor-perceptible runtime defect in the current code.

Why the fix does not break anything:

- Either `time.sleep(0.5)` to honour the fade or removing the `fadeout` and keeping just `stop()` gives consistent behaviour with no side effects on tracking state, channels, or `current_music_file` reset.
- The `pygame.mixer.stop()` call below (which halts SFX channels) and `active_effects.clear()` are unaffected.

Recommended fix (either is safe):

- Change `time.sleep(0.1)` to `time.sleep(0.5)` so the 500 ms fade actually completes.
- Or drop the `fadeout(500)` call entirely and rely on the immediate `stop()`. The click is replaced by a clean cut, which is at least consistent.

Acceptance check:

- Looping the scene on real hardware produces no click between iterations.
- The music stream is silenced cleanly within at most 500 ms of `STOP`.

Verdict: real P3 quality bug. Affects every loop iteration on real hardware.

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

1. **NEW: Stop audio in `_run_scene_logic.finally`** — small surgical fix; eliminates the "audio plays forever after a crash" failure mode for the looped SceneV01 deployment.
2. **NEW: Fix pygame `fadeout`/`stop` timing mismatch** — one-line change that removes the audible click on every scene loop end.
3. Improve dashboard failure isolation — bounded retry/backoff/degraded state for web dashboard startup crashes.
5. Decouple dashboard log broadcasting — add async bounded queue for web log events. Exception isolation already done.
6. Improve scene MQTT failure handling — add optional `onMqttFailure` policy for critical actions.
7. Improve feedback truth — add correlation IDs when the ESP protocol can support it, or add a per-topic queue/warning fallback.
8. Enforce frontend build in install/release flow.

## Final Verdict

- Audio-not-stopped-on-scene-exception is a real P1 for unattended looped operation; fix is small.
- Web crash loop is real but P3 by default.
- Scene MQTT failure behaviour is a design gap; P2 only for critical hardware actions.
- Feedback correlation is real but usually P3 because physical command delivery is not directly affected.
- Web log handler exception isolation is done; async queue/fanout decoupling remains.
- Vite output path is fixed; deployment enforcement is only partly fixed.
- Video-end tri-state and watchdog scene heartbeat are now in place and resolved.

## Verification Notes

No Raspberry Pi runtime tests were run.

This review was verified statically against the current repository state on Windows. The conclusions above are based on direct source inspection, not live hardware behavior.
