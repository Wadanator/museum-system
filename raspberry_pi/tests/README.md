# Test Profiles

Use these from `raspberry_pi/` on the Raspberry Pi.

## Quick Offline

Fast pytest checks only, including offline runtime smoke checks. No service,
MQTT broker, GPIO, audio device, video player, or dashboard required.

```bash
source venv/bin/activate
python3 tests/run_quick_tests.py
```

Equivalent direct pytest command:

```bash
pytest -q \
  tests/test_ambient_loop_service.py \
  tests/test_ambient_status_wiring.py \
  tests/test_dashboard_log_fanout.py \
  tests/test_schema_validator.py \
  tests/test_mqtt_feedback_state.py \
  tests/test_mqtt_state_reporting.py \
  tests/test_device_status_broadcast.py \
  tests/test_main_scene_state.py \
  tests/test_heartbeat.py \
  tests/test_transition_manager_overflow.py \
  tests/test_video_handler_end_detection.py \
  tests/test_runtime_smoke.py \
  tests/test_state_executor.py \
  tests/test_web_dashboard_retry.py
```

## Safe Non-Stress

Runs the same unified pytest suite as Quick Offline. This is the best routine
"did I break core code?" check, and can optionally include live service
diagnostics with `--include-service`.

```bash
source venv/bin/activate
python3 tests/run_safe_tests.py
```

## Live Service Diagnostic

Not a stress test, but it talks to the running dashboard and may start/stop a
scene. Use only when the museum service can be safely exercised.

```bash
source venv/bin/activate
python3 tests/run_safe_tests.py --include-service --url http://127.0.0.1:5000
```

The runner uses the default credentials from `Web/config.py`. Override them
only when testing a different deployment:

```bash
python3 tests/run_safe_tests.py --include-service --user admin --password '...'
```

The underlying script is `manual_ws_museum_diagnostic.py`.

## Legacy Wrapper

`manual_runtime_refactor_smoke.py` is kept as a compatibility wrapper, but the
offline runtime smoke assertions now live in `test_runtime_smoke.py` and run
through pytest.

## Stress / Disruptive

Run only intentionally:

- `manual_scene_service_stress.py`
- `run_scene_stress_scenev01.sh`
- `manual_web_retry_p03_test.sh`

These can repeatedly hit APIs, stop/start scenes, occupy port `5000`, or touch
systemd services.
