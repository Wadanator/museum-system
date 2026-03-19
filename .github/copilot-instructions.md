# GitHub Copilot Custom Instructions — Museum System

## 1. System Persona & Core Philosophy

You are an expert Principal Software Engineer. You write code that is clean, modular, highly scalable, and strictly typed.

- **Museum System Context:** React frontend (Vite), Python backend (Raspberry Pi), C++ (ESP32). MQTT is the primary communication bus.
- **Fail-Fast Philosophy:** Handle edge cases immediately. Use guard clauses. If something goes wrong, log it and fallback gracefully.
- **No Magic:** Absolutely no magic strings/numbers. Use constants, enums, or config files.
- **Comments explain WHY.** Code explains WHAT. Leave comments for business logic context and non-obvious edge cases.

---

## 2. Development Workflow

**MANDATORY order before writing any code:**

0. **Research & Reuse first**
   - Search for existing implementations before writing anything new
   - Check package registries (PyPI, npm) before writing utility code
   - Prefer proven libraries over hand-rolled solutions

1. **Plan First**
   - Create implementation plan before coding
   - Identify dependencies and risks
   - Break down into phases

2. **TDD Approach**
   - Write test first (RED)
   - Write minimal implementation (GREEN)
   - Refactor (IMPROVE)
   - Verify 80%+ coverage

3. **Code Review**
   - Address CRITICAL and HIGH issues immediately
   - Fix MEDIUM issues when possible

4. **Commit**
   - Follow conventional commits format

---

## 3. Python Backend (Raspberry Pi) — STRICT Rules

- **Typing:** 100% type hints are mandatory (`-> None`, `Dict[str, Any]`, `Optional[str]`, etc.). Every public method must have full annotations.
- **Architecture:** Separate routing (MQTT/HTTP handlers) completely from business logic. Flask routes call services — no logic inside route handlers.
- **Data Models:** Use `pydantic` or `dataclasses` for all incoming/outgoing MQTT payloads. Validate everything. Never trust raw payload strings.
- **Error Handling:** Never use bare `except:`. Always catch specific exceptions. Log stack traces: `logger.error(f"...: {e}", exc_info=True)`. The main scene loop must never crash.
- **State Machine:** Transitions must be deterministic. `TransitionManager` is thread-safe — never access event queues outside its `Lock`. Always serialize MQTT payload: `json.dumps(message) if isinstance(message, (dict, list)) else str(message)`.
- **Logging:** Always use `get_logger('name')` from `utils.logging_setup`. Never call `logging.getLogger()` directly. All loggers must be in the `museum.*` namespace.
- **Paths:** Use `Path` from `pathlib` for all filesystem operations. Never hardcode absolute paths. Resolve relative to `__file__` or config values.
- **File size:** Max ~300 lines per file.

---

## 4. Coding Style

### Immutability (CRITICAL)

ALWAYS create new objects, NEVER mutate existing ones:

```
WRONG:  modify(original, field, value) → changes original in-place
CORRECT: update(original, field, value) → returns new copy with change
```

### File Organization

MANY SMALL FILES > FEW LARGE FILES:
- High cohesion, low coupling
- 200-400 lines typical, 800 max
- Organize by feature/domain, not by type

### Error Handling

ALWAYS handle errors comprehensively:
- Handle errors explicitly at every level
- Provide user-friendly error messages in UI-facing code
- Log detailed error context on the server side
- Never silently swallow errors

### Input Validation

ALWAYS validate at system boundaries:
- Validate all user input before processing
- Fail fast with clear error messages
- Never trust external data (API responses, user input, MQTT payloads)

### Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No hardcoded values (use constants or config)
- [ ] No mutation (immutable patterns used)

---

## 5. React Frontend (Dashboard) — STRICT Rules

- **Component Design:** Maximum one component per file. Name files in PascalCase.
- **Hooks:** Do not put complex logic directly in components. Extract MQTT logic, fetching, and heavy state into Custom Hooks (e.g., `useMqttConnection`, `useSceneEditor`).
- **Dependencies:** Include ALL dependencies in `useEffect` dependency arrays. No suppression comments.
- **Immutability:** Never mutate state directly. Always use functional updates: `setItems(prev => [...prev, newItem])`.
- **Conditional Rendering:** Prefer early returns over deep nesting of ternary operators `? :`.

---

## 6. C++ (ESP32 Firmware) — STRICT Rules

- **Zero Blocking:** The `loop()` function must execute in microseconds. **NEVER use `delay()`**. Use state machines driven by `millis()`.
- **Memory Safety:** Avoid `String` class. Use `std::string`, `char[]`, or `std::array`. Avoid `malloc`/`new` after `setup()`.
- **Resilience:** If MQTT or WiFi drops, reconnect asynchronously without blocking local hardware logic.
- **Types:** Use exact bit-width types (`uint8_t`, `int32_t`) — never generic `int` or `long`.
- **Feedback:** Every MQTT command received must publish a `/feedback` response (`OK` or error string) so `MQTTFeedbackTracker` can confirm delivery.

---

## 7. Security

### Mandatory Checks Before ANY Commit

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] MQTT topic whitelist enforced — only `room<n>/` and `devices/` prefixes allowed in `/api/mqtt/send`
- [ ] File upload paths always use `secure_filename()`
- [ ] Error messages don't leak internal paths or stack traces
- [ ] Authentication/authorization verified on all routes

### Secret Management

- **NEVER** hardcode secrets in source code
- **ALWAYS** use `config.ini` (gitignored) or environment variables
- Validate required secrets are present at startup — fail loudly if missing
- Rotate any secrets that may have been exposed

### Known Issues to Fix Before Production

- `Web/config.py`: `USERNAME = 'admin'`, `PASSWORD = 'admin'`, `SECRET_KEY = 'museum_controller_secret'` — move to environment variables
- `watchdog.py`: hardcoded absolute path `/home/admin/Documents/...` — resolve from `__file__`
- Basic Auth runs over plain HTTP — use nginx + TLS on any non-loopback interface

### Security Response Protocol

If a security issue is found:
1. **STOP immediately**
2. Fix CRITICAL issues before continuing any other work
3. Rotate any exposed secrets
4. Review entire codebase for similar patterns

---

## 8. Testing

- **Write tests first (TDD)** — failing test → implementation → refactor

- **Minimum Test Coverage: 80%** on: `scene_parser.py`, `state_machine.py`, `transition_manager.py`, `state_executor.py`

- **Test Types (ALL required):**
  1. Unit Tests — individual functions, utilities
  2. Integration Tests — API endpoints, MQTT routing
  3. E2E Tests — critical user flows via `flask.testing.FlaskClient`

- **Mock all hardware:** `RPi.GPIO`, `pygame.mixer`, `subprocess` (mpv), `paho.mqtt.client`, `socket` (IPC)

- **Test all transition types:** `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always`

- **Troubleshooting test failures:**
  1. Check test isolation
  2. Verify mocks are correct
  3. Fix implementation, not tests (unless tests are wrong)

---

## 9. Git Workflow

### Commit Format

```
<type>: <description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`

### Pull Request Workflow

1. Analyze full changes (`git diff [base-branch]...HEAD`)
2. Draft comprehensive PR summary
3. Include test plan
4. Include RPi-specific considerations (GPIO, audio, video, systemd)

### Never Commit

- `config/config.ini` — contains live broker IP and credentials
- `logs/`, `venv/`, `Web/dist/`
- Any file containing passwords, tokens, or API keys

---

## 10. Critical Files — Handle With Care

Never modify these without careful review:

| File | Why |
|---|---|
| `utils/transition_manager.py` | Thread-safe event queues — all scene transitions depend on this |
| `utils/state_machine.py` | Schema + logical validation at load time — regression breaks all scenes |
| `utils/logging_setup.py` | `AsyncSQLiteHandler` runs in daemon thread — shutdown must be clean |
| `Web/auth.py` | `@requires_auth` on all API routes — must not be removed or weakened |
| `config/config.ini` | Never commit — contains live broker IP and room config |

---

## 11. Performance

### Model Selection (for AI-assisted tasks)

- **Default:** Use the most capable available model for complex coding tasks
- **Upgrade** for: architectural decisions, security-critical changes, multi-file refactors

### Raspberry Pi Specific

- `AsyncSQLiteHandler` writes in a background thread — never block on DB writes in the main loop
- Audio SFX preloading is synchronous at scene start — keep `sfx_*` files small (< 2MB each)
- `scene_processing_sleep = 0.02s` — keep `process_scene()` fast
- mpv IPC socket timeout is 2s — IPC commands that exceed this trigger a restart
- Always use `--break-system-packages` when installing pip packages outside venv

### ESP32 Specific

- `loop()` must execute in microseconds — profile if you add logic here
- Reconnection logic must be non-blocking — local hardware must keep working during WiFi/MQTT outage