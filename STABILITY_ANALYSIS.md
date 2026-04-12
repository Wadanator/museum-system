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

Evidence:
- `running` is written once at scene start in `main.py`.
- `idle` is written only when scene exits.
- Watchdog treats old state file as stale after fixed age.

Why this is substantial:
- Can misclassify a valid long-running scene and allow unsafe restart behavior.
- Directly impacts the core requirement: scene must run reliably without unexpected interruption.

Potential fix:
- Move to heartbeat-style scene status (`state` + timestamp freshness).
- Keep backward compatibility during rollout (support old plain format for one release).

Side-effect check:
- Risk: frequent writes to `/tmp`.
- Mitigation: update heartbeat every 5-10 seconds (not every loop tick).

Acceptance gate:
- During a 3-hour loop test, watchdog never treats active scene as idle.

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

---

### P0-3 Web dashboard crash loop is unbounded

Status: OPEN (Revalidated 2026-04-12)

Evidence:
- Web thread retries forever with fixed 10s delay.

Why this is substantial:
- Persistent failure creates log flood and hides critical runtime signals.
- Operationally dangerous during unattended museum hours.

Potential fix:
- Add bounded retries and backoff.
- Enter explicit degraded-web state after retry budget is exhausted.

Side-effect check:
- Risk: dashboard may remain down longer after transient issue.
- Mitigation: schedule low-frequency background retry while keeping core scene runtime unaffected.

Acceptance gate:
- On forced web bind error, logs remain bounded and scene runtime remains healthy.

Current validation result (2026-04-12):
- `raspberry_pi/Web/app.py` contains an unbounded `while True` retry loop in `run_dashboard()`.
- Retry policy is fixed-delay (10s) and does not expose degraded-web state.

---

### P0-4 MQTT timing defaults are too aggressive for production noise

Evidence:
- `device_timeout = 25`
- `feedback_timeout = 1`

Why this is substantial:
- Causes false offline and false timeout signals in real networks.
- Produces avoidable operator noise and erodes trust in alerts.

Potential fix:
- Set `device_timeout = 60` baseline.
- Set `feedback_timeout = 3` baseline.

Side-effect check:
- Risk: slower detection of truly offline devices.
- Mitigation: keep escalation alerts for repeated failures and track mean recovery delay.

Acceptance gate:
- False offline flips drop significantly without missing real disconnect incidents.

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

---

## Final Go-Live Rule

If any P0 item is open, deployment is not considered 24/7-ready.

If all P0 gates pass and P1 is planned with owners, launch is acceptable with managed risk.
