# Museum System - Reliability And Stability Future Work

Updated: 2026-06-15

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short date or note if useful, and do not leave completed work only in chat or
git history.

Source documents that this file replaces:

- `RELIABILITY_CODE_REVIEW.md`
- `STABILITY_ANALYSIS.md`
- `STABILITY_ANALYSIS2.md`

This file is the practical consolidated TODO list for reliability and stability
work that still looks relevant in the current repository state. Items that were
already implemented or downgraded are tracked in
`99_reference_reliability_stability_completed_work.md`.

## Priority Meaning

- P1: should be handled before long unattended operation in a real
  installation.
- P2: should be handled during the first hardening pass after the main runtime
  is stable.
- P3: useful improvement, but not a deployment blocker.

## P1 - Web Dashboard Crash Loop Still Has Infinite Retry - DONE (2026-06-15)

Status: done

Where:

- `raspberry_pi/Web/app.py`

Current state:

- `run_dashboard()` now delegates to a bounded retry helper.
- The first failures use a short 2s/4s/8s fast retry budget.
- After that, the dashboard is marked `degraded` and retried every 300s with
  rate-limited logging.
- `/api/status` includes a `web_dashboard` diagnostic object when the web layer
  is available.

Why this is real:

- A permanent port bind problem or runtime error can create endless log spam.
- The operator does not get a clear "dashboard degraded" state.
- The core runtime will likely survive, but diagnostics become unnecessarily
  noisy.

Recommended work:

- Add a limited fast-retry budget with exponential backoff.
- After the fast retries are exhausted, mark the dashboard as degraded.
- Continue retrying slowly with rate-limited logging.

Acceptance:

- DONE: A simulated bind failure does not spam logs forever.
- DONE: The museum runtime continues without the dashboard.
- DONE: Logs clearly show that the web layer is degraded.

## P1 - Align Production MQTT Timing Defaults - DONE (2026-06-15)

Status: done

Where:

- `raspberry_pi/config/config.ini`
- `raspberry_pi/config/config.ini.example`
- `raspberry_pi/utils/config_manager.py`

Current state:

- Older analysis assumed `device_timeout` was already a conservative 180
  seconds.
- The current `config.ini` and `config.ini.example` both use
  `device_timeout = 25`.
- `ConfigManager` fallback remains 180 seconds for missing keys, but tracked
  runtime configs now explicitly choose the faster production value `25s`.
- `command_ack_timeout_ms` is separated from legacy `feedback_timeout` and
  remains `700ms` for fast command feedback.
- `node_offline_timeout_s` remains `5s`, but the current online/offline device
  registry uses `device_timeout`.

Why this is real:

- A copied config now uses a less aggressive timeout than the old 15s value.
- Short LAN/MQTT hiccups are less likely to create false offline states while
  still showing real device loss quickly.

Recommended work:

- DONE: Production `device_timeout` is set to `25s`. Current ESP status
  heartbeat is typically `5s`, so this allows roughly five missed heartbeats
  before a device is marked offline.
- DONE: Keep `command_ack_timeout_ms = 700` for fast feedback timeout behavior.
- DONE: Keep `node_offline_timeout_s = 5` documented as reserved/actuator-state
  timing; the current registry uses `device_timeout`.
- DONE: Document the difference between:
  - `device_timeout`
  - `node_offline_timeout_s`
  - `command_ack_timeout_ms`

Acceptance:

- DONE: `config.ini.example` matches the intended production recommendation.
- DONE: Documentation clearly explains which timeout means device offline and
  which one is only command ACK timing.

## P1/P2 - MQTT Reconnect Failure Paths Need Explicit Paho Cleanup - DONE (2026-06-15)

Status: done

Where:

- `raspberry_pi/utils/mqtt/mqtt_client.py`
- `raspberry_pi/utils/system_monitor.py`
- `docs/TO_DO/02_mqtt_security_hardening.md`
- `raspberry_pi/tests/test_mqtt_client_reconnect_cleanup.py`

Current state:

- `MQTTClient.connect()` now tracks whether the Paho network loop was started
  for the current attempt.
- On timeout, refused connection, or exception it stops the loop, disconnects
  the underlying client, and resets wrapper connection state before retrying.
- `SystemMonitor.perform_periodic_health_check()` can repeatedly call
  `manage_connection_health()` during a broker/network outage without carrying
  stale Paho loop/socket state into later attempts.

Why this is real:

- A long broker outage, bad broker address, or rejected auth can keep
  exercising the failed-connect path for hours.
- Half-started Paho loop state can accumulate or leave the client in a bad
  retry state.
- The midnight service reset limits worst-case duration, but reconnect
  reliability should not depend on that reset.
- This overlaps with MQTT security hardening because failed auth uses the same
  failed-connect path.

Implemented work:

- DONE: Track whether each connect attempt started the Paho loop.
- DONE: Prefer Paho callback API v2 so current development installs do not emit
  the old callback API deprecation warning.
- DONE: On timeout, non-success return code, or exception, best-effort
  `loop_stop()` and `disconnect()` before returning `False` or retrying.
- DONE: Add fake-client tests for timeout, refused return code, exception, and
  successful reconnect.
- DONE: Keep timeout logging at debug level so broker outages do not flood
  production logs.

Acceptance:

- DONE: Repeated broker-down health checks do not increase active network-loop
  threads.
- DONE: Failed auth/timeouts leave the client ready for the next retry.
- DONE: Successful reconnect still subscribes and calls the restored callback.

## P2 - Scene MQTT Publish Failure Policy For Critical Actions

Status: open

Where:

- `raspberry_pi/utils/state_executor.py`
- scene schema / JSON format, if an opt-in policy is added
- dashboard log/status, if failures should be visible to the operator

Current state:

- `_execute_mqtt()` checks the result of `mqtt_client.publish(...)`.
- On failure it logs an error.
- The scene continues.

Why this is real:

- For ordinary effects, "log and continue" is a reasonable backward-compatible
  default.
- For critical motors or relays, the scene can continue with audio/video even
  though the physical room did not perform the expected action.

Recommended work:

- Keep `continue` as the default so existing scenes do not break.
- Add an opt-in policy, for example:
  - global `onMqttFailure: continue|retry|abort`
  - per-action `required: true` or `failurePolicy`
- On `abort`, move the system to a known safe state and show the error in the
  dashboard.

Acceptance:

- Existing scenes behave the same until they opt into the new policy.
- A critical MQTT action can retry or abort a scene instead of silently
  continuing.

## P2 - Feedback Tracking Needs Better Truthfulness For Fast Commands

Status: open

Where:

- `raspberry_pi/utils/mqtt/mqtt_feedback_tracker.py`

Current state:

- Pending feedback is keyed only by the original topic.
- A second command to the same topic replaces the first pending timer.
- The replacement is not explicitly visible as a correlation risk.

Why this is real:

- Two fast commands to the same topic cannot be reliably distinguished.
- A late `OK` from the first command can confirm the second command.
- The physical publish already happened, so this is not necessarily P1, but
  dashboard truth and diagnostics can be misleading.

Recommended work:

- Best fix: add command/correlation IDs to the ESP protocol.
- Short-term fix: at least log a warning when unresolved pending feedback for
  the same topic is replaced by a new command.
- Add a per-device rolling timeout counter and a clear degraded-device alert
  after a failure threshold.

Acceptance:

- Two fast commands either have distinguishable results or a clear warning that
  correlation is not guaranteed.
- A simulated device outage produces one understandable degraded-device signal,
  not only many isolated timeout logs.

## P2 - Dashboard Log Fanout Is Still Synchronous - DONE (2026-06-15)

Status: done

Where:

- `raspberry_pi/Web/handlers/log_handler.py`
- `raspberry_pi/Web/dashboard.py`
- `raspberry_pi/tests/test_dashboard_log_fanout.py`

Current state:

- `WebLogHandler.emit()` now isolates exceptions through
  `handleError(record)`.
- `dashboard.add_log_entry(...)` appends to the in-memory log buffer and then
  queues websocket fanout into a bounded dashboard-owned queue.
- A daemon `dashboard-log-fanout` worker drains queued log events and broadcasts
  the existing `new_log` event to connected clients.
- If the queue is full, runtime logging does not block. The websocket event is
  dropped and a rate-limited warning is written directly into the dashboard log
  buffer without recursively logging through Python logging.

Why this is real:

- The thread that logs also does dashboard websocket work.
- With one or two LAN clients the risk is low.
- With slow clients or many clients, logging can add latency to runtime
  threads.

Implemented work:

- Send log events into a bounded queue.
- Drain the queue from a dashboard-owned background worker.
- If the queue is full, drop websocket fanout and store a rate-limited
  dashboard warning.
- Keep frontend/API compatibility: `new_log`, `log_history`, `/api/logs`, and
  `/api/status.log_count` keep the same shape.

Acceptance:

- DONE - Runtime logging is not blocked by websocket fanout.
- DONE - A dashboard error never propagates back into the runtime thread that
  logged.
- DONE - Unit tests cover queued fanout, non-synchronous emit, full queue
  behavior, and websocket emit failures.

## P2 - Actuator State WebSocket Fanout Still Runs On MQTT Callback Path

Status: open

Where:

- `raspberry_pi/utils/mqtt/mqtt_actuator_state_store.py`
- `raspberry_pi/utils/runtime/dashboard_notifier.py`
- `raspberry_pi/Web/dashboard.py`

Current state:

- `MQTTActuatorStateStore._notify()` calls its update callback synchronously.
- The callback path reaches `WebDashboard.broadcast_device_runtime_state(...)`,
  which emits SocketIO events to connected dashboard clients.
- This happens from MQTT/device-state paths such as retained state reports,
  feedback confirmations, offline/online state changes, and forced-off updates.

Why this is real:

- The log fanout path is already async, but device runtime-state fanout still
  has the same risk shape.
- A slow dashboard client or SocketIO stall can make MQTT callback handling
  slower.
- During an ESP reconnect burst or retained-state replay, many state updates
  can arrive close together.

Recommended work:

- Move `device_runtime_state_update` delivery onto a bounded async queue,
  preferably through a small generic dashboard event queue.
- Coalesce by topic when overloaded so the newest actuator state wins instead
  of preserving every intermediate update.
- Add a rate-limited warning/counter when state updates are dropped or
  coalesced under pressure.

Acceptance:

- A slow/broken dashboard client cannot block MQTT message handling.
- A flood of state reports does not grow memory unbounded.
- After backpressure clears, the dashboard receives the latest known state for
  each topic.

## P2 - Async SQLite Logging Needs Drop Visibility And Shutdown Drain

Status: open

Where:

- `raspberry_pi/utils/logging_setup.py`
- `raspberry_pi/main.py`

Current state:

- `AsyncSQLiteHandler` uses a bounded queue with `maxsize=1000`.
- When the queue is full, `emit()` silently drops log records.
- `close()` asks the writer thread to stop and joins for a short timeout, but
  it does not explicitly wake the worker or drain all queued records before
  process exit.

Why this is real:

- The room can keep running, but post-incident diagnostics can lose exactly the
  logs needed to understand what happened.
- The planned midnight reset makes shutdown flushing important because shutdown
  is a normal daily event, not only a crash path.
- Silent drops make the dashboard/log database look complete when it may not be
  complete.

Recommended work:

- Maintain a dropped-record counter and emit a rate-limited warning when the
  queue overflows.
- Use a sentinel/event so `close()` wakes the writer immediately.
- Drain queued records on shutdown within a bounded deadline.
- Ensure `logging.shutdown()` or equivalent cleanup runs during controller
  shutdown.

Acceptance:

- A forced log burst records visible dropped-log diagnostics instead of failing
  silently.
- Normal shutdown flushes queued records within a bounded time.
- The daily reset preserves final shutdown/restart diagnostic lines as much as
  possible.

## P2 - Build/Deploy Flow Still Does Not Guarantee A Current Frontend Build - SKIP

Status: partly improved, still open

Where:

- `museum-dashboard/vite.config.js`
- `raspberry_pi/install.sh`
- `raspberry_pi/install_offline.sh`

Current state:

- Vite `outDir` now points directly to `../raspberry_pi/Web/dist`.
- Install scripts still do not run `npm run build`.

Why this is real:

- If `museum-dashboard/src` changes and the developer forgets to build, Flask
  can still serve old assets from `raspberry_pi/Web/dist`.

Recommended work:

- Add a clear release step or validation that `dist` matches the current
  frontend source.
- Online install can optionally run the frontend build when Node is available.
- Offline install should at minimum verify that a built `dist` exists and fail
  with a clear message if it does not.

Acceptance:

- A clean deployment process cannot silently deploy an outdated dashboard
  build.

## P2 - Dashboard Media Upload Needs Size And Disk-Space Guard

Status: open

Where:

- `raspberry_pi/Web/routes/media.py`
- `raspberry_pi/Web/app.py`
- `raspberry_pi/config/config.ini.example`

Current state:

- Authenticated media upload validates file extension, then writes the uploaded
  file directly to the media folder.
- There is no configured maximum upload size, per-media size limit, free-disk
  reserve check, or atomic temp-file rename.

Why this is real:

- An accidental huge upload or browser retry can fill the Raspberry Pi storage.
- Full disk can break SQLite logging, scene saves, media playback, package
  updates, and general OS stability.
- Authentication reduces malicious access, but operator mistakes are still
  realistic in a museum installation.

Recommended work:

- Add configurable upload limits for image/audio/video files.
- Add a minimum free-space reserve before accepting uploads.
- Save uploads to a temporary file and rename atomically after validation.
- Clean up partial temp files on failed uploads.

Acceptance:

- Oversized uploads are rejected before writing the full file.
- Low-disk conditions return a clear dashboard error and preserve existing
  files.
- Interrupted uploads do not leave broken final media files behind.

## P2/P3 - Dashboard Credentials And Secret Key Are Still Hardcoded

Status: open

Where:

- `raspberry_pi/Web/config.py`

Current state:

- `USERNAME = 'admin'`
- `PASSWORD = 'admin12321'`
- `SECRET_KEY = 'museum_controller_secret'`

Why this is real:

- If the dashboard only runs inside an isolated trusted LAN, this is not the
  same kind of risk as a scene runtime bug.
- If the dashboard is reachable from a broader network, this becomes a practical
  deployment blocker.

Recommended work:

- Load credentials and secret from environment variables or config outside the
  repository.
- When default `admin/admin` is used, log an explicit production warning.
- Document how to change the values on the Pi.

Acceptance:

- A production installation does not use credentials stored in source code.
- The system can still run in dev mode with simple defaults.

## P3 - Transition Event Queue Overflow Monitoring - DONE (2026-06-15)

Status: done

Where:

- `raspberry_pi/utils/transition_manager.py`
- `raspberry_pi/tests/test_transition_manager_overflow.py`

Current state:

- MQTT/audio/video event queues are `deque(maxlen=50)`.
- Before appending to a full queue, `TransitionManager` records that the next
  append will drop the oldest event.
- A rate-limited warning reports dropped transition events per queue type:
  `mqtt`, `audioEnd`, or `videoEnd`.

Why this is real:

- The locking discipline looks safe.
- During an MQTT flood, events can be lost without diagnostics.

Implemented work:

- Before append, check whether the queue is full.
- Maintain per-queue drop counters.
- Log the first drop immediately and then rate-limit repeated warnings.

Acceptance:

- DONE - During an artificial flood, logs show that transition events were
  dropped.
- DONE - Without a flood, this creates no warning log noise.
- DONE - Unit tests cover MQTT, audioEnd, videoEnd, and rate-limiting.

## P3 - Explicit Reason Codes For Scene Termination

Status: open

Where:

- `raspberry_pi/utils/scene_parser.py`
- possibly `raspberry_pi/main.py`

Current state:

- `process_scene()` returns `False` when the scene is finished or when current
  state data is missing, without an explicit reason code.

Why this is real:

- Production diagnostics are faster when every scene termination path produces
  one stable reason.

Recommended work:

- Add short reason codes, for example:
  - `scene_finished`
  - `missing_current_state_data`
  - `scene_start_failed`
  - `external_stop`
- Log exactly one termination reason per scene end.

Acceptance:

- Every normal or error scene end has one clear reason in the logs.

## Intentionally Not Moved To TODO

These items from the old documents are not current TODOs:

- Scene heartbeat and centralized scene state transitions are implemented.
- Video IPC `unknown` should no longer trigger a false `videoEnd`.
- The manual MQTT API checks unsuccessful publish results.
- Frontend `authFetch` now throws for non-2xx responses.
- Vite output path is fixed; only release/build enforcement remains open.
- The old claim that "there are no tests" is outdated. Tests for heartbeat,
  scene state, MQTT feedback state, and video end detection exist in the
  repository.
