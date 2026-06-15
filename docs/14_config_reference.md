# Config Reference

Date: 2026-06-14

Purpose: one operator-facing place that lists configurable values for the
Raspberry Pi runtime.

## Source Of Truth

Current implemented config values come from:

- `raspberry_pi/config/config.ini.example`
- `raspberry_pi/utils/config_manager.py`
- `raspberry_pi/watchdog.py` for scene-aware watchdog wait values

Rules:

- Keep `raspberry_pi/config/config.ini.example` complete. A missing
  `config.ini` is auto-created from that template.
- When a TODO implementation adds, removes, or renames a config key, update
  this file in the same step.
- Planned keys listed near the bottom are not active until their TODO phase
  updates `config.ini.example`, `ConfigManager`, and tests.
- Do not put production secrets in tracked files.

## Runtime Config Files

| File | Status | Purpose |
| --- | --- | --- |
| `raspberry_pi/config/config.ini` | local/runtime | Real config used by the Pi. |
| `raspberry_pi/config/config.ini.example` | tracked template | Default template copied when `config.ini` is missing. |
| `raspberry_pi/config/rooms/<room_id>/devices.json` | local room config | Device/group mapping used by the dashboard and actuator state store. |
| `raspberry_pi/config/config.local.ini` | planned | Future ignored local override for MQTT secrets. See `docs/TO_DO/02_mqtt_security_hardening.md`. |

Boolean values should be written as `true` or `false`.

## Current Implemented Keys

Defaults below are the values currently documented in
`raspberry_pi/config/config.ini.example`.

### `[MQTT]`

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `broker_ip` | `127.0.0.1` | string | MQTT broker host/IP. Watchdog also pings this target. |
| `port` | `1883` | int | MQTT broker port. |
| `device_timeout` | `25` | seconds | Device status timeout for online/offline registry. With 5s ESP status heartbeats this allows roughly five missed heartbeats before marking a device offline. |
| `feedback_timeout` | `1` | seconds | Legacy/general feedback timeout. |
| `command_ack_timeout_ms` | `700` | milliseconds | Per-command acknowledgement timeout for MQTT feedback tracking. This affects command feedback, not device online/offline presence. |
| `node_offline_timeout_s` | `5` | seconds | Reserved actuator-state offline timing value. The current online/offline registry uses `device_timeout`. |

### `[GPIO]`

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `button_pin` | `27` | int | BCM GPIO pin for the physical start button. |
| `debounce_time` | `300` | milliseconds | Button debounce window. |

### `[Room]`

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `room_id` | `room1` | string | MQTT room namespace and asset/config room folder. |

### `[Scenes]`

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `directory` | `scenes` | path segment | Base scene directory relative to `raspberry_pi/`. Runtime uses `<directory>/<room_id>/`. |

### `[Audio]`

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `directory` | `audio` | path segment | Audio directory inside the current room folder. |
| `max_init_attempts` | `3` | int | Pygame mixer init attempts. |
| `init_retry_delay` | `5` | seconds | Delay between audio init attempts. |

### `[Video]`

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `directory` | `videos` | path segment | Video directory inside the current room folder. |
| `ipc_socket` | `/tmp/mpv_socket` | path | mpv IPC socket path. |
| `iddle_image` | `black.png` | filename | Current spelling is intentional in code/config. Do not rename casually. |
| `hwdec` | `auto-safe` | string | mpv hardware decoding option. |
| `video_output` | `gpu` | string | mpv video output option. |
| `gpu_context` | `drm` | string | mpv GPU context for Pi/headless playback. |
| `hwdec_codecs` | `h264,hevc` | comma string | Codecs allowed for hardware decoding. |
| `framedrop` | `vo` | string | mpv frame drop policy. |
| `mpv_extra_args` | empty | shell-like string | Extra mpv args parsed with `shlex.split`; quote values with spaces. |
| `health_check_interval` | `60` | seconds | Video handler health check interval. |
| `max_restart_attempts` | `3` | int | mpv auto-restart attempt limit. |
| `restart_cooldown` | `60` | seconds | Cooldown before another mpv restart attempt. |

### `[System]`

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `health_check_interval` | `120` | seconds | System monitor interval. |
| `main_loop_sleep` | `0.1` | seconds | Main controller loop sleep. |
| `mqtt_check_interval` | `60` | seconds | MQTT client connection check interval. |
| `scene_processing_sleep` | `0.005` | seconds | Scene processing loop sleep. |
| `web_dashboard_port` | `5000` | int | Flask/Socket.IO dashboard port. |
| `mqtt_retry_attempts` | `3` | int | MQTT publish/connect retry attempts used by runtime services. |
| `mqtt_retry_sleep` | `2` | seconds | Delay between MQTT retry attempts. |
| `mqtt_connect_timeout` | `10` | seconds | Initial MQTT connect timeout. |
| `mqtt_reconnect_timeout` | `5` | seconds | Reconnect attempt timeout. |
| `mqtt_reconnect_sleep` | `0.5` | seconds | Delay between reconnect attempts. |
| `scene_buffer_time` | `1` | seconds | Minimum scene-start buffer used by runtime. |
| `device_cleanup_interval` | `2` | seconds | Interval for device/registry cleanup tasks. |
| `scene_heartbeat_interval` | `60` | seconds | Heartbeat freshness while a scene is running. |
| `scene_wait_poll_interval` | `30` | seconds | Watchdog polling interval while waiting for a running scene to finish. Read directly by `watchdog.py`. |
| `scene_wait_max_seconds` | `7200` | seconds | Watchdog hard wait limit for a running scene. Raise above longest expected scene or ambient cycle duration. |

### `[Json]`

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `json_file_name` | `SceneV01.json` | filename | Default scene started by GPIO/default MQTT START. |

### `[Startup]`

Implemented for classic and ambient startup behavior. Ambient mode is now
handled by the runtime policy layer described in
`docs/TO_DO/06_ambient_loop_mode.md`.

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `mode` | `classic` | `classic`/`ambient` | Runtime startup mode. `classic` preserves current behavior. |
| `ambient_scene` | empty | filename | Ambient scene. Empty resolves to `[Json] json_file_name` in `ConfigManager`. |
| `ambient_start_policy` | `after_initial_connection_attempt` | enum | `after_initial_connection_attempt` or `wait_for_mqtt`. |
| `ambient_restart_delay_seconds` | `2` | seconds | Normal delay between ambient cycles. Must stay below `scene_wait_max_seconds`. Negative values clamp to `0`. |
| `ambient_error_retry_seconds` | `30` | seconds | Retry delay for missing/load/start failures. Negative values clamp to `0`. |
| `ambient_cycle_cleanup` | `scene_only` | enum | `scene_only` avoids global room STOP between normal cycles; `full_stop` keeps classic cleanup. |
| `ambient_ignore_default_start` | `true` | bool | Ignore GPIO/default MQTT START in ambient mode to avoid duplicates. |
| `ambient_allow_named_scene_start` | `true` | bool | Allow explicit named scene starts while ambient is idle/suspended. |
| `ambient_stop_behavior` | `suspend_until_restart` | enum | `suspend_until_restart` or `resume_after_delay`. `resume_after_delay` uses `ambient_restart_delay_seconds`. |

Current temporary room1 operating choice:

- Use `ambient_mode_smoke_test.json` as the configured ambient scene until the
  real production ambient scene is authored.
- Keep `config.ini.example` defaulting to `classic`; set the real Pi
  `config.ini` to `ambient` only for installations that should auto-start.

Ambient mode operator quick reference:

```ini
[Startup]
mode = classic | ambient
ambient_scene = <scene filename> | empty
ambient_start_policy = after_initial_connection_attempt | wait_for_mqtt
ambient_restart_delay_seconds = <non-negative seconds>
ambient_error_retry_seconds = <non-negative seconds>
ambient_cycle_cleanup = scene_only | full_stop
ambient_ignore_default_start = true | false
ambient_allow_named_scene_start = true | false
ambient_stop_behavior = suspend_until_restart | resume_after_delay
```

Recommended temporary room1 ambient config until a real scene exists:

```ini
[Startup]
mode = ambient
ambient_scene = ambient_mode_smoke_test.json
ambient_start_policy = after_initial_connection_attempt
ambient_restart_delay_seconds = 5
ambient_error_retry_seconds = 30
ambient_cycle_cleanup = scene_only
ambient_ignore_default_start = true
ambient_allow_named_scene_start = true
ambient_stop_behavior = suspend_until_restart
```

Ambient behavior notes:

- Empty `ambient_scene` uses `[Json] json_file_name`.
- `scene_only` skips global `room/STOP` between normal ambient cycles.
- `full_stop` sends the classic force-off/STOP cleanup between cycles.
- `suspend_until_restart` means dashboard/API Stop stops ambient until service
  restart or the landing dashboard `Zapnúť ambient` action.
- `resume_after_delay` means Stop behaves like another ambient cycle and uses
  `ambient_restart_delay_seconds`.
- Recoverable missing/load/start failures use `ambient_error_retry_seconds`.

### `[Logging]`

| Key | Default | Type | Notes |
| --- | --- | --- | --- |
| `log_level` | `INFO` | level | Global log level fallback. |
| `log_directory` | `logs` | path segment | Log directory resolved under `raspberry_pi/` unless absolute handling is added later. |
| `max_file_size_mb` | `5` | MB | Rotating log file size. |
| `backup_count` | `3` | int | Rotating backup file count. |
| `daily_backup_days` | `7` | days | Daily backup retention. |
| `console_colors` | `false` | bool | Colorized console logs. |
| `file_logging` | `true` | bool | Enable file logging. |
| `console_logging` | `false` | bool | Enable console logging. |
| `log_format` | `detailed` | enum-ish string | Current format preset. |

### `[LogLevels]`

Per-logger overrides. Use exact logger names from `get_logger(...)`.

Current template names:

```ini
museum.main = INFO
museum.watchdog = INFO
museum.sceneparser = INFO
museum.statemachine = WARNING
museum.stateexecutor = WARNING
museum.transitionmanager = WARNING
museum.servicecontainer = INFO
museum.btn_handler = WARNING
museum.sys_monitor = WARNING
museum.device_outage_tracker = WARNING
museum.config = WARNING
museum.bootstrap = INFO
museum.mqtt = WARNING
museum.mqtt_handler = WARNING
museum.mqtt_feedback = WARNING
museum.mqtt_devices = WARNING
museum.actuator_store = WARNING
museum.audio = WARNING
museum.video = INFO
museum.web = INFO
werkzeug = ERROR
flask = ERROR
urllib3 = ERROR
paho = ERROR
socketio = ERROR
engineio = ERROR
```

## Planned Keys Not Yet Implemented

This section exists so implementation TODOs do not invent conflicting config
names. Do not rely on these keys in production until their related TODO is
implemented and moved into the current section above.

### Planned `[Display]` - CEC Display Power Control

Source: `docs/TO_DO/05_cec_display_power_control.md`.

| Key | Planned default | Type | Notes |
| --- | --- | --- | --- |
| `enabled` | `true` | bool | Enable display power manager. |
| `backend` | `cec` | `cec`/`noop` | Use `noop` for monitors without CEC or dev machines. |
| `mode` | `auto` | enum | Display policy mode. See the CEC TODO before implementing. |
| `cec_target` | `0` | string/int | CEC logical target address. |
| `cec_client_path` | `cec-client` | command/path | CEC CLI executable. |
| `cec_adapter` | `auto` | string | Optional CEC adapter selector from the TODO draft. |
| `idle_timeout_seconds` | `300` | seconds | Idle delay before standby. |
| `power_on_lead_seconds` | `8` | seconds | Optional lead time before expected display use. |
| `power_command_timeout_seconds` | `3` | seconds | Timeout for CEC power commands. |
| `power_status_timeout_seconds` | `2` | seconds | Timeout for CEC status queries. |
| `min_seconds_between_power_commands` | `15` | seconds | Anti-spam/cooldown for CEC commands. |
| `wait_for_power_on_before_video` | `false` | bool | If true, video waits briefly for display power-on. Keep bounded. |
| `max_video_start_wait_seconds` | `1.0` | seconds | Maximum wait before video starts anyway. |
| `standby_on_service_stop` | `true` | bool | Put display in standby during service cleanup. |
| `startup_power_state` | `standby` | enum | Desired initial display state. |

### Planned MQTT Security Keys

Source: `docs/TO_DO/02_mqtt_security_hardening.md`.

Planned tracked template keys:

```ini
[MQTT]
username =
password =
tls_enabled = false
tls_ca_file =
tls_insecure = false
```

Planned internal flat config names:

```python
mqtt_username
mqtt_password
mqtt_tls_enabled
mqtt_tls_ca_file
mqtt_tls_insecure
```

Security rule: real production credentials should live in ignored
`raspberry_pi/config/config.local.ini`, not in tracked `config.ini` or
`config.ini.example`.

## Maintenance Checklist

When adding or changing a config key:

1. Update `raspberry_pi/config/config.ini.example`.
2. Update `raspberry_pi/utils/config_manager.py` or the direct reader that owns
   the key.
3. Add or update tests for parsing/defaults/validation.
4. Update this reference.
5. Update the relevant TODO file and mark implemented steps `DONE`.
6. If the operator must touch the key during setup, update
   `docs/10_museum_backend_setup.md`.
