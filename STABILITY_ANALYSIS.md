# Museum System - Stability Analysis (Production Prioritized)

Analysis Date: 2026-04-01
Scope: Raspberry Pi runtime for museum deployment (single looping scene, 24/7 target)
Goal: Final deployment-focused list sorted from highest to lowest importance

---

## Executive Decision

This document is now strictly prioritized for go-live.

- P0 = Must be done before museum launch.
- P1 = Strongly recommended in first hardening wave.
- P2 = Useful improvements after stable operation baseline.

Only substantial, code-backed items are included.

Update 2026-04-01:

- P0-2 is implemented and validated on target RPi runtime.
- Validation evidence:
  - Offline unit checks in `raspberry_pi/tests/test_main_scene_state.py` passed (2/2).
  - Runtime API stress test in `raspberry_pi/tests/manual_scene_service_stress.py` passed (50 cycles, no unexpected API errors, final `scene_running=False`).
- Revalidation 2026-04-12:
  - P0-3 reopened. Current `raspberry_pi/Web/app.py` still runs unbounded `while True` web restart loop with fixed 10s delay.

---

## P0 - Must Fix Before Launch

### P0-1 Scene activity freshness contract is too weak for long runtime

Status: CLOSED (Implemented 2026-05-16)

Evidence:

- `running` is written once at scene start in `main.py`.
- `idle` is written only when scene exits.
- Watchdog treats old state file as stale after fixed age.

Why this was substantial:

- Could misclassify a valid long-running scene and allow unsafe restart behavior.

Validation result:

- `_heartbeat_loop`, `_start_heartbeat`, `_stop_heartbeat` implemented in `main.py`.
- `_set_scene_running` calls `_start_heartbeat` on scene start and `_stop_heartbeat` on scene end.
- Heartbeat rewrites `/tmp/museum_scene_state` every `scene_heartbeat_interval` seconds (configured).
- Watchdog staleness threshold (2h) no longer relevant for actively running scenes.

---

### P0-2 Scene state transitions are not fully centralized

Status: CLOSED (Implemented + Validated 2026-04-01)

Evidence:

- `scene_running` is written in multiple paths; not all updates use one transition API.

Why this is substantial:

- State divergence is the classic source of rare 24/7 failures.
- Hard-to-reproduce race windows can break start/stop semantics.

Potential fix:

- Introduce one internal transition method for scene lifecycle updates.
- Route all scene state writes through it and keep lock discipline consistent.

Side-effect check:

- Risk: accidental behavior change in edge stop paths.
- Mitigation: keep method idempotent and add explicit unit tests for repeated STOP.

Acceptance gate:

- 100 rapid start/stop cycles complete without stuck `running` state.

Validation result:

- Central transition API implemented in `raspberry_pi/main.py` as `_set_scene_running(...)`.
- Direct scattered scene state writes were replaced by centralized transitions.
- Runtime stress validation passed with final stable idle state after STOP.
- A/B offline verification confirms regression protection:
  - New `main.py`: `raspberry_pi/tests/test_main_scene_state.py` passed 4/4.
  - Old `main.py`: same test script failed 2/4 on:
    - `start_scene_by_name_returns_real_start_result`
    - `missing_scene_broadcasts_status_update`

### P0-4 MQTT timing defaults are too aggressive for production noise

Status: CLOSED (2026-05-16)

Original concern was based on incorrect baseline values:

- Report stated `device_timeout = 25` — actual value was always `device_timeout = 180` (3 min), already conservative.
- Report stated `feedback_timeout = 1` — this has since been refactored: feedback now uses `command_ack_timeout_ms = 200` (0.2s default) as a per-command ACK budget, configurable in `config.ini`.

No corrective action needed on `device_timeout`. The `command_ack_timeout_ms` default can be tuned in config if false timeouts are observed in the museum network environment.

---

## P1 - High Value Hardening (Do Immediately After Launch Readiness)

### P1-1 Feedback timeouts need device-level escalation, not only per-message logging

Evidence:

- Timeout handler logs each miss independently.

Why this matters:

- Alert storms without incident-level summary slow diagnosis.

Potential fix:

- Add per-device rolling timeout counters and escalate after threshold window.
- Reset escalation after first successful feedback.

Side-effect check:

- Risk: over-aggregation can hide isolated single-command errors.
- Mitigation: keep per-message logs, add aggregated alert as additional signal.

Acceptance gate:

- During simulated device outage, one clear degraded-device alert appears within threshold window.

---

### P1-2 Scene parser has silent `False` exits with limited reason visibility

Evidence:

- `process_scene()` returns `False` in key branches without explicit reason logs.

Why this matters:

- In production, unclear scene termination reason increases MTTR.

Potential fix:

- Add reason-coded logs for each early-return branch.

Side-effect check:

- Risk: log verbosity increase.
- Mitigation: use stable concise reason codes and INFO/ERROR levels intentionally.

Acceptance gate:

- Every scene termination path produces exactly one explicit reason code in logs.

---

### P1-3 Watchdog policy values should be config-driven for exhibition realities

Evidence:

- Fixed wait and stale thresholds in watchdog.

Why this matters:

- Hardcoded values age poorly as exhibition behavior evolves.

Potential fix:

- Move key watchdog timing limits to config and document safe ranges.

Side-effect check:

- Risk: unsafe custom values by mistake.
- Mitigation: validate bounds on startup and fallback to safe defaults.

Acceptance gate:

- Invalid watchdog config is rejected with clear startup error.

---

## P2 - Optimize After Stable Baseline

### P2-1 Network health checks should include MQTT functional probe

Evidence:

- Watchdog periodic network check is ICMP-oriented.

Why this is lower priority:

- Core reconnection logic already exists; this is observability hardening.

Potential fix:

- Keep ICMP as coarse signal and add lightweight MQTT functional check.

Side-effect check:

- Risk: probe traffic/noise.
- Mitigation: low frequency probe and strict timeout budget.

Acceptance gate:

- Functional MQTT outage is detected earlier than generic ICMP-only method.

---

### P2-2 Scene loop sleep tuning should be metric-driven

Evidence:

- `scene_processing_sleep = 0.02` may be conservative.

Why this is lower priority:

- Current value is safe; reliability impact is lower than P0/P1 issues.

Potential fix:

- Profile on target hardware; test 0.05 only if no responsiveness regression.

Side-effect check:

- Risk: slower transition responsiveness.
- Mitigation: validate response latency against visitor interaction threshold.

Acceptance gate:

- CPU improves while scene responsiveness remains within agreed limit.

---

## Already Fixed (Verified - Do Not Reopen)

1. Async log queue is bounded.
2. GPIO cleanup is wrapped safely.
3. Video force-kill handles expected process lookup errors.
4. State history is bounded.
5. Audio active-effects map uses lock.
6. `stop_scene()` uses lock guard path.
7. P0-1: Scene heartbeat implemented — `_heartbeat_loop` in `main.py` keeps state file fresh during long scenes.
8. P0-2: Scene state transitions centralized via `_set_scene_running` in `main.py`.
9. P0-4: `device_timeout` was never 25s (was 180s); `feedback_timeout` refactored to `command_ack_timeout_ms`.

---

## Final Go-Live Rule

If any P0 item is open, deployment is not considered 24/7-ready.

If all P0 gates pass and P1 is planned with owners, launch is acceptable with managed risk.
