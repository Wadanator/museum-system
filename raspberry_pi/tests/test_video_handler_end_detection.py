import sys
import time
import types
from pathlib import Path

# Ensure raspberry_pi/ is importable when tests are executed from repository root.
RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

try:
    import psutil  # noqa: F401
except ModuleNotFoundError:
    sys.modules["psutil"] = types.SimpleNamespace(process_iter=lambda *_args, **_kwargs: [])

from utils.video_handler import VideoHandler


class _Logger:
    def __init__(self):
        self.records = []

    def _record(self, level, *args):
        self.records.append((level, " ".join(str(arg) for arg in args)))

    def debug(self, *args, **_kwargs):
        self._record("debug", *args)

    def info(self, *args, **_kwargs):
        self._record("info", *args)

    def warning(self, *args, **_kwargs):
        self._record("warning", *args)

    def error(self, *args, **_kwargs):
        self._record("error", *args)

    def critical(self, *args, **_kwargs):
        self._record("critical", *args)

    def count(self, level):
        return sum(
            1
            for record_level, _message in self.records
            if record_level == level
        )

    def messages(self, level=None):
        return [
            message
            for record_level, message in self.records
            if level is None or record_level == level
        ]


class _FakeProcess:
    def __init__(self, running=True):
        self.running = running

    def poll(self):
        return None if self.running else 1


def _build_handler(currently_playing="ghost2.mp4", was_playing=True):
    handler = VideoHandler.__new__(VideoHandler)
    handler.iddle_image = "/videos/black.png"
    handler.currently_playing = currently_playing
    handler.was_playing = was_playing
    handler.logger = _Logger()

    callbacks = []
    stops = []
    handler.end_callback = callbacks.append

    def _stop_video():
        stops.append(True)
        handler.currently_playing = "black.png"
        return True

    handler.stop_video = _stop_video
    return handler, callbacks, stops


def _build_ipc_handler():
    handler = VideoHandler.__new__(VideoHandler)
    handler.iddle_image = "/videos/black.png"
    handler.currently_playing = "ghost2.mp4"
    handler.was_playing = True
    handler.end_callback = None
    handler.logger = _Logger()
    handler.process = _FakeProcess(running=True)
    handler.ipc_socket = f"/tmp/museum_test_missing_mpv_socket_{id(handler)}"
    handler.health_check_interval = 60
    handler.last_health_check = time.time()
    handler.restart_cooldown = 60
    handler.max_restart_attempts = 3
    handler.restart_count = 1
    handler.last_restart_time = time.time()
    handler.ipc_failure_log_interval = 30
    handler.last_ipc_failure_log = 0.0
    handler.last_restart_block_log = 0.0
    return handler


def _manual_test_confirmed_video_end_fires_once_with_original_file():
    handler, callbacks, stops = _build_handler()
    handler._send_ipc_command = lambda *_args, **_kwargs: {
        "error": "success",
        "data": "/videos/black.png",
    }

    handler.check_if_ended()

    assert callbacks == ["ghost2.mp4"]
    assert len(stops) == 1
    assert handler.was_playing is False


def _manual_test_transient_ipc_unknown_does_not_fire_or_clear_same_video():
    handler, callbacks, stops = _build_handler()
    handler._send_ipc_command = lambda *_args, **_kwargs: None

    handler.check_if_ended()

    assert callbacks == []
    assert stops == []
    assert handler.was_playing is True


def _manual_test_video_can_end_after_transient_ipc_unknown():
    handler, callbacks, stops = _build_handler()
    responses = [
        None,
        {"error": "success", "data": "/videos/black.png"},
    ]
    handler._send_ipc_command = lambda *_args, **_kwargs: responses.pop(0)

    handler.check_if_ended()
    handler.check_if_ended()

    assert callbacks == ["ghost2.mp4"]
    assert len(stops) == 1
    assert handler.was_playing is False


def _manual_test_restart_during_unknown_resets_without_callback():
    handler, callbacks, stops = _build_handler()

    def _unknown_after_restart(*_args, **_kwargs):
        handler.currently_playing = "black.png"
        return None

    handler._send_ipc_command = _unknown_after_restart

    handler.check_if_ended()

    assert callbacks == []
    assert stops == []
    assert handler.was_playing is False


def _manual_test_empty_success_response_is_unknown():
    handler, callbacks, stops = _build_handler()
    handler._send_ipc_command = lambda *_args, **_kwargs: {
        "error": "success",
        "data": "",
    }

    handler.check_if_ended()

    assert callbacks == []
    assert stops == []
    assert handler.was_playing is True


def _manual_test_confirmed_video_path_keeps_playing_state():
    handler, callbacks, stops = _build_handler(was_playing=False)
    handler._send_ipc_command = lambda *_args, **_kwargs: {
        "error": "success",
        "data": "/videos/ghost2.mp4",
    }

    handler.check_if_ended()

    assert callbacks == []
    assert stops == []
    assert handler.was_playing is True


def _manual_test_missing_socket_ipc_logs_once_for_repeated_stop_commands():
    handler = _build_ipc_handler()
    restart_calls = []

    def _restart_mpv():
        restart_calls.append(True)
        return False

    handler._restart_mpv = _restart_mpv

    assert handler.stop_video() is False
    assert handler.stop_video() is False

    # stop_video sends two IPC commands. Across two calls that is four failures,
    # but only the first one should be an error; the rest are suppressed debug logs.
    assert len(restart_calls) == 4
    assert handler.logger.count("error") == 1
    assert handler.logger.count("debug") == 3
    assert "process/socket unavailable" in handler.logger.messages("error")[0]
    assert all(
        "suppressed" in message
        for message in handler.logger.messages("debug")
    )


def _manual_test_missing_socket_get_response_returns_none_without_log_storm():
    handler = _build_ipc_handler()
    restart_calls = []
    handler._restart_mpv = lambda: restart_calls.append(True) or False

    first = handler._send_ipc_command(["get_property", "path"], get_response=True)
    second = handler._send_ipc_command(["get_property", "path"], get_response=True)

    assert first is None
    assert second is None
    assert len(restart_calls) == 2
    assert handler.logger.count("error") == 1
    assert handler.logger.count("debug") == 1


def _manual_test_restart_block_log_is_throttled_during_cooldown():
    handler = _build_ipc_handler()
    handler.restart_count = handler.max_restart_attempts

    assert handler._restart_mpv() is False
    assert handler._restart_mpv() is False

    assert handler.logger.count("critical") == 1
    assert handler.logger.count("debug") == 1
    assert "exceeded 3 attempts" in handler.logger.messages("critical")[0]


def _manual_test_restart_attempts_reset_after_cooldown():
    handler = _build_ipc_handler()
    handler.restart_count = handler.max_restart_attempts
    handler.last_restart_time = time.time() - handler.restart_cooldown - 1

    actions = []
    handler._stop_current_process = lambda: actions.append("stop")
    handler._start_mpv = lambda: actions.append("start") or True

    original_sleep = time.sleep
    try:
        time.sleep = lambda _seconds: None
        assert handler._restart_mpv() is True
    finally:
        time.sleep = original_sleep

    assert actions == ["stop", "start"]
    assert handler.restart_count == 1
    assert handler.logger.count("warning") == 1
    assert "cooldown elapsed" in handler.logger.messages("warning")[0]


if __name__ == "__main__":
    print("Running video end detection checks (no mpv required)...")
    tests = [
        (
            "confirmed_video_end_fires_once_with_original_file",
            _manual_test_confirmed_video_end_fires_once_with_original_file,
        ),
        (
            "transient_ipc_unknown_does_not_fire_or_clear_same_video",
            _manual_test_transient_ipc_unknown_does_not_fire_or_clear_same_video,
        ),
        (
            "video_can_end_after_transient_ipc_unknown",
            _manual_test_video_can_end_after_transient_ipc_unknown,
        ),
        (
            "restart_during_unknown_resets_without_callback",
            _manual_test_restart_during_unknown_resets_without_callback,
        ),
        (
            "empty_success_response_is_unknown",
            _manual_test_empty_success_response_is_unknown,
        ),
        (
            "confirmed_video_path_keeps_playing_state",
            _manual_test_confirmed_video_path_keeps_playing_state,
        ),
        (
            "missing_socket_ipc_logs_once_for_repeated_stop_commands",
            _manual_test_missing_socket_ipc_logs_once_for_repeated_stop_commands,
        ),
        (
            "missing_socket_get_response_returns_none_without_log_storm",
            _manual_test_missing_socket_get_response_returns_none_without_log_storm,
        ),
        (
            "restart_block_log_is_throttled_during_cooldown",
            _manual_test_restart_block_log_is_throttled_during_cooldown,
        ),
        (
            "restart_attempts_reset_after_cooldown",
            _manual_test_restart_attempts_reset_after_cooldown,
        ),
    ]

    failed = 0
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"[PASS] {test_name}")
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {test_name}: {exc}")

    if failed:
        print(f"Video end detection checks failed: {failed}/{len(tests)}")
        raise SystemExit(1)

    print(f"Video end detection checks passed: {len(tests)}/{len(tests)}")
