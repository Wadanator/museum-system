# Scene Lifecycle + Lease Proposal (24/7 Reliability)

Date: 2026-04-01
Scope: Reliable scene start/run/stop semantics for watchdog-safe 24/7 operation
Status: Design draft for review (no code changes in this document)

---

## Understanding Summary

1. The runtime must never get stuck in ambiguous state between scene and watchdog.
2. Core user expectation is simple: scene starts, scene finishes, system remains responsive.
3. Restart safety is critical: watchdog must not kill valid long-running scenes.
4. Shared state transitions must be deterministic and serialized.
5. Diagnostics must be explicit enough for operators to understand failures quickly.
6. Non-goal: adding heavy orchestration or external state services.

---

## Assumptions

1. Single room controller process owns one active scene at a time.
2. Watchdog remains external process and uses local file contract for scene status.
3. Local filesystem `/tmp` is available and writable in normal operation.
4. Backward compatibility is needed during migration from plain `running`/`idle` format.

---

## Problem Statement

Current contract uses a coarse scene flag file and mixed write ownership for scene state.

Main risks:
- Stale state during long scenes.
- Non-uniform `scene_running` transitions.
- Restart decisions based on weak state evidence.

---

## Design Approaches

### Approach A (Recommended): Lease File + Explicit Lifecycle State Machine

Summary:
- Replace plain text state file with JSON lease payload.
- Keep explicit lifecycle states in runtime.
- Refresh lease heartbeat periodically while running.

Lease example:

```json
{
  "version": 1,
  "generation": 42,
  "scene_name": "SceneV01.json",
  "state": "running",
  "started_at": 1775018400.1,
  "last_progress_at": 1775018465.4,
  "reason": "button_start",
  "pid": 1234
}
```

Potential fix:
- Introduce a single state-transition API (`set_scene_state`).
- Update lease atomically from that API.
- Refresh `last_progress_at` every 5-10 seconds while running.

Why recommended:
- Highest observability and safest watchdog decisions.
- Predictable recovery behavior.

Trade-off:
- Slightly larger implementation than minimal patch.

---

### Approach B: Keep Current File, Add Timestamp Suffix

Summary:
- Keep `running`/`idle`, append timestamp in string format.

Potential fix:
- Write `running:<ts>` periodically.
- Watchdog parses value and fallback to old format.

Pros:
- Fastest migration.

Cons:
- Fragile parsing, weaker extensibility than structured JSON.

---

### Approach C: In-Memory Only State + Watchdog RPC Probe

Summary:
- Runtime exposes health endpoint with scene state.
- Watchdog queries endpoint instead of reading file.

Pros:
- Clean API contract.

Cons:
- Adds new dependency on web/service availability.
- More moving parts for failure isolation.

---

## Recommended Decision

Choose Approach A.

Reason:
- Best fit for 24/7 resilience with low complexity increase.
- Strongest basis for future diagnostics and automated restart control.

---

## Proposed Lifecycle Contract

States:
- `idle`
- `starting`
- `running`
- `stopping`
- `failed`

Rules:
1. All transitions must go through one method.
2. Side effects (web emit, watchdog lease write, metrics) happen inside transition handler.
3. Repeated `stop` in `stopping`/`idle` is idempotent.
4. `failed` must include reason code.

---

## Watchdog Decision Model (Potential fix)

Inputs:
- lease `state`
- `last_progress_at`
- process health

Policy:
1. `running` + fresh heartbeat => no restart.
2. `running` + stale heartbeat => mark suspected stuck, wait grace interval, recheck.
3. still stale after grace => controlled restart path.
4. `starting` stale beyond startup threshold => transition to failure recovery.

---

## Failure Modes and Handling

1. Lease file missing:
- Potential fix: watchdog treats as unknown, retries short window, then recovers.

2. Lease parse error:
- Potential fix: fallback parser for legacy format + warning.

3. Runtime crash mid-scene:
- Potential fix: stale `running` lease + dead process triggers restart.

4. Double stop request:
- Potential fix: idempotent stop transition returns success without extra side effects.

---

## Decision Log

1. Decision: keep file-based watchdog contract.
- Alternatives: web probe only.
- Why: fewer dependencies, safer under partial failures.

2. Decision: structured JSON lease over text format.
- Alternatives: `running:<ts>`.
- Why: extensible and less ambiguous.

3. Decision: centralized scene state transition API.
- Alternatives: distributed ad-hoc writes.
- Why: deterministic behavior and easier testing.

---

## Verification Plan

1. Long-scene test (3h): watchdog must never restart active scene.
2. Forced freeze test: stale heartbeat must trigger recovery within target SLA.
3. Rapid start/stop stress (100 cycles): no deadlock, no zombie running state.
4. Crash injection test: restart path must recover to `idle` and accept next scene.

---

## Open Questions (Please confirm)

1. What is acceptable max recovery time when a scene is truly stuck?
2. Is preserving currently running scene always more important than quick restart?
3. Do you want strict fail-closed behavior (stop everything on ambiguity) or fail-open (continue scene)?
4. Is JSON lease acceptable for your operations tooling, or do you prefer simpler text format?

---

## Decision Lock Request

Does this document accurately reflect your intent for the second topic (lifecycle + watchdog lease reliability)?
Please confirm or correct before implementation planning.
