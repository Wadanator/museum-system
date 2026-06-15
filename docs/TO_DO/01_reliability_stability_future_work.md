# Museum System - Reliability And Stability Future Work

Updated: 2026-05-23

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

## P1 - Align Production MQTT Timing Defaults

Status: open / values need a final decision

Where:

- `raspberry_pi/config/config.ini`
- `raspberry_pi/config/config.ini.example`
- `raspberry_pi/utils/config_manager.py`

Current state:

- Older analysis assumed `device_timeout` was already a conservative 180
  seconds.
- The current `config.ini` and `config.ini.example` both use
  `device_timeout = 15`.
- `ConfigManager` fallback is 180 seconds, but a real copied config overrides
  that fallback with 15 seconds.
- `command_ack_timeout_ms` is now separated from legacy `feedback_timeout`,
  which is good, but production values still need to be explicit.

Why this is real:

- A copied config can override the safer fallback with an aggressive timeout.
- Short LAN/MQTT hiccups can create false offline states for devices.

Recommended work:

- Decide the production default for `device_timeout` based on the real ESP
  heartbeat interval.
- Likely use 60-180 seconds for device presence.
- Keep a lower `node_offline_timeout_s` only for actuator-state indication if
  that distinction remains useful.
- Document the difference between:
  - `device_timeout`
  - `node_offline_timeout_s`
  - `command_ack_timeout_ms`

Acceptance:

- `config.ini.example` matches the intended production recommendation.
- Documentation clearly explains which timeout means device offline and which
  one is only command ACK timing.

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

## P2 - Dashboard Log Fanout Is Still Synchronous

Status: partly improved, still open

Where:

- `raspberry_pi/Web/handlers/log_handler.py`
- `raspberry_pi/Web/dashboard.py`

Current state:

- `WebLogHandler.emit()` now isolates exceptions through
  `handleError(record)`.
- `dashboard.add_log_entry(...)` still directly calls websocket fanout through
  `_broadcast_event(...)`.

Why this is real:

- The thread that logs also does dashboard websocket work.
- With one or two LAN clients the risk is low.
- With slow clients or many clients, logging can add latency to runtime
  threads.

Recommended work:

- Send log events into a bounded queue.
- Drain the queue from a dashboard-owned background worker.
- If the queue is full, drop or merge old logs and emit a rate-limited warning.

Acceptance:

- Runtime logging is not blocked by websocket fanout.
- A dashboard error never propagates back into the runtime thread that logged.

## P2 - Build/Deploy Flow Still Does Not Guarantee A Current Frontend Build

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

## P2/P3 - Dashboard Credentials And Secret Key Are Still Hardcoded

Status: open

Where:

- `raspberry_pi/Web/config.py`

Current state:

- `USERNAME = 'admin'`
- `PASSWORD = 'admin'`
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

## P3 - Transition Event Queue Overflow Monitoring

Status: open

Where:

- `raspberry_pi/utils/transition_manager.py`

Current state:

- MQTT/audio/video event queues are `deque(maxlen=50)`.
- When full, `deque` silently drops the oldest events.

Why this is real:

- The locking discipline looks safe.
- During an MQTT flood, events can be lost without diagnostics.

Recommended work:

- Before append, check whether the queue is full.
- Maintain a drop counter and log a rate-limited warning.

Acceptance:

- During an artificial flood, logs show that transition events were dropped.
- Without a flood, this creates no log noise.

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
