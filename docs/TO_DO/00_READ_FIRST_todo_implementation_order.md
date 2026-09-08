# TODO implementation order

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short date or note if useful, and do not leave completed work only in chat or
git history.

Do not delete TODO items just because they are implemented. The TODO file should
stay useful as project history:

- keep the original task/phase text,
- add `DONE` directly to the implemented heading or bullet,
- add a short completion note with date, changed files, and key tests when it
  helps future work,
- if only part of a section is finished, mark only that part as `DONE`,
- if a section is intentionally skipped or replaced, mark it as `SKIPPED` or
  `SUPERSEDED` with the reason and the replacement location,
- do not rely on chat history, memory files, or git history as the only record
  of completed TODO work.

For large completed work, add or update a small `Completed work` / `DONE log`
section inside the same TODO file. Cross-cutting reliability items can also be
summarized in `99_reference_reliability_stability_completed_work.md`, but the
primary record still belongs in the TODO file where the work was planned.

Whole-file completion rule:

- When every concrete item in an individual active TODO plan file is finished
  or intentionally closed, first mark each relevant section as `DONE`,
  `SKIPPED`, or `SUPERSEDED` inside that file.
- Then rename that TODO file with a `_DONE` suffix before `.md`, so completion
  is visible from the file list.
- Example: `04a_static_image_scene_action.md` becomes
  `04a_static_image_scene_action_DONE.md`.
- Keep the completed file in `docs/TO_DO/` unless a separate cleanup task
  explicitly moves archived plans elsewhere.
- Do not rename this `00_READ_FIRST_todo_implementation_order.md` index file or
  the `99_reference_reliability_stability_completed_work.md` reference file
  just because other TODOs are completed.

This file is the recommended order for working through the TODO plans in this
directory. File names are prefixed with the recommended order number so they
sort in the same order in file explorers.

## Core rule

Do not mix unrelated TODOs in one implementation session. Pick one numbered
block, implement only that scope, run its tests, mark the implemented parts as
`DONE`, then continue to the next block.

## Recommended order

### 1. Runtime stability hardening

File:

- `01_reliability_stability_future_work.md`

Why first:

- It contains remaining P1/P2 runtime risks.
- It stabilizes the base system before security, state reporting, display power,
  ambient mode, or cover control add more moving parts.
- It includes production MQTT timing defaults and dashboard credentials, which
  overlap with later MQTT/security work.

Recommended scope:

- Finish P1 items first.
- Then handle P2 items that directly affect deployment reliability.
- Leave P3 polish until after the higher-risk roadmap is stable.

### 2. MQTT broker authentication

File:

- `02_mqtt_security_hardening.md`

Why here:

- The broker is currently open to any LAN client that knows the IP.
- This adds a connection-level login without changing topic names or scene JSON.
- It creates the `config.local.ini` secret-storage pattern that later TODOs can
  reuse.

Important dependency:

- Do not disable `allow_anonymous` until the Raspberry Pi backend and all active
  ESP32/Shelly/Waveshare nodes can authenticate.
- If state-reporting firmware changes are going to happen immediately after this,
  consider combining ESP32 flashes for MQTT auth and state reporting to reduce
  repeated physical access.

### 3. Authoritative MQTT state reporting

File:

- `03_mqtt_state_reporting_rework_DONE.md`

Why after MQTT auth:

- It adds retained `/state` topics and makes Live view more truthful.
- It prepares the backend/frontend model needed by covers and richer device UI.
- It should stay compatible with the MQTT auth plan because auth does not change
  topic contracts.

Important dependency:

- ESP32 firmware must ignore its own `/state` topics when wildcard subscriptions
  are used.
- Retained state behavior must be tested with reconnects and broker restarts.

Progress:

- 2026-06-12: `03_mqtt_state_reporting_rework_DONE.md` phases 1 and 2 are marked
  `DONE`; backend, room config, tests, and Arduino ESP32 state publishing were
  implemented. Pi pytest validation passed, and retained relay/effect `/state`
  behavior was verified on `Room1_Relays_Ctrl`. Motor hardware validation is
  intentionally deferred because `Room1_ESP_Motory` is not currently available;
  verify `room1/motor1/state` and `room1/motor2/state` later when the motor ESP32
  can be connected.

### 3b. ESP-NOW relay-to-motor bridge

File:

- `03b_espnow_relay_motor_bridge.md`

Why after state reporting:

- It keeps the existing MQTT topic contract and uses retained motor `/state`
  plus `devices/<node_id>/status` already introduced by state reporting.
- The Raspberry Pi backend can remain mostly unchanged while the relay LAN
  controller becomes the runtime bridge for the WiFi-only motor controller.
- It should be completed before adding more movement-heavy devices that depend
  on reliable motor/actuator transport.

Important dependency:

- In production bridge mode, exactly one device should subscribe and act on
  `room1/motor1` and `room1/motor2`: either the relay bridge or the motor's
  legacy direct MQTT path, never both at the same time.

### 4. Dashboard scene editor remaining polish

File:

- `04_scenegen_v2_remaining_polish.md`

Why here:

- The dashboard-integrated scene editor is already mostly implemented.
- Finishing remaining validation/polish before adding more device types makes
  later cover/display/ambient workflows easier to test from the dashboard.
- This is lower infrastructure risk than MQTT auth or state reporting.

Recommended scope:

- Finish medium-priority missing items first.
- Do not reopen already completed SceneGen requirements unless a real regression
  or new workflow requires it.

### 4a. Static image scene action

File:

- `04a_static_image_scene_action.md`

Why here:

- It adds a small but user-facing scene JSON feature before larger display mode
  work.
- It touches the current dashboard editor, so it fits naturally after dashboard
  editor polish.
- It reuses the existing video/mpv display backend and should be implemented
  before ambient/display workflows rely on static images.

Recommended scope:

- Keep the action simple: show one image or clear back to the configured idle
  image.
- Preserve existing `video` action image compatibility.
- Update backend schema/runtime, dashboard editor, docs, and tests together.
- Do not modify `SceneGen_DO_NOT_UPDATE/`; the standalone SceneGen app is no
  longer used.

### 5. CEC display power control

File:

- `05_cec_display_power_control.md`

Why here:

- It is mostly local to Raspberry Pi runtime and HDMI display behavior.
- It benefits from stable scene lifecycle and dashboard status.
- It should be implemented before ambient loop mode if ambient scenes will use
  video/display behavior.

Important dependency:

- Do hardware proof first. HDMI-CEC support depends on the actual display and
  Raspberry Pi setup.

### 6. Ambient loop mode

File:

- `06_ambient_loop_mode.md`

Why after CEC:

- Ambient mode changes startup and repeat behavior of scenes.
- If display power control exists, ambient video loops can use the final display
  policy instead of inventing a temporary one.
- It depends on scene lifecycle reliability, so it should not be first.

Recommended scope:

- Keep `classic` as the default mode.
- Add `ambient` as an explicit config-driven mode.
- Test stop/shutdown behavior carefully so ambient restart does not fight manual
  stop or service shutdown.

### 7. Cover / roleta support

File:

- `07_cover_roleta_support.md`

Why later:

- It touches real 230 V movement, safety policy, MQTT command/state contracts,
  frontend UI, backend state handling, and possibly Shelly/ESP32 firmware.
- It benefits from MQTT auth and authoritative state reporting being stable.
- It should not be mixed with unrelated cleanup or core refactors.

Important dependency:

- Confirm final hardware and safety behavior before coding.
- Electrical/interlock safety is not just a software task.

### 8. Legacy cleanup final pass

File:

- `08_legacy_cleanup_audit.md`

Why near the end:

- Many low-risk cleanup items are already done.
- Cleanup is safest when the active runtime path is stable and tests are passing.
- Avoid mixing deletions with feature work, because it makes regressions harder
  to diagnose.

Recommended scope:

- Do small cleanup batches.
- Run tests after each batch.
- Mark deleted/kept items as `DONE` or "kept intentionally" in the audit.

### 9. State machine refactor decision

Files:

- `09_state_machine_refactor_decision.md`
- `10_state_machine_refactor_implementation_plan.md`

Why last:

- These plans overlap and both describe a major core refactor to Pydantic and
  Transitions.
- The current custom state machine is already integrated with scenes, MQTT,
  audio, video, transitions, watchdog state, and dashboard expectations.
- This should not be mixed with security, device state reporting, display power,
  ambient mode, or cover work.

Recommended first action:

- Do not implement immediately.
- First reconcile these two files into one current plan or mark one as
  superseded.
- Only proceed if the benefit is still worth the regression risk after the
  earlier roadmap is stable.

### 10. State machine refactor implementation

Files:

- final reconciled state-machine plan from order 9

Why absolutely last:

- It changes the core execution engine.
- It requires the broadest regression suite.
- It should happen only after the system has stable tests and the higher-value
  deployment/security/device-state work is complete.

Minimum acceptance before starting:

- Existing scene JSON compatibility is proven with tests.
- MQTT transitions still work.
- Timeout, audioEnd, videoEnd, always, and mqttMessage transitions still behave
  exactly as before.
- Watchdog scene state file behavior stays compatible.

### 99. Reference only - completed reliability work

File:

- `99_reference_reliability_stability_completed_work.md`

Use this before planning a change, but do not treat it as active work. It records
what is already done or reduced to lower practical risk.

## Practical combined-work notes

- MQTT auth and MQTT state reporting both touch ESP32 firmware. If the same
  physical devices are hard to access, plan the firmware flashes together, but
  still mark each TODO phase separately as `DONE`.
- CEC display power and ambient loop mode are related operationally. Implement
  CEC first if ambient mode will run long video loops.
- Cover support depends on MQTT/state foundations. Do not start it while the
  broker auth rollout is half-finished.
- Legacy cleanup can be done between larger features, but only in tiny batches
  with tests.
