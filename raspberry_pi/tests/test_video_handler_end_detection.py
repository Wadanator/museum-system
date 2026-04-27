import sys
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
    def debug(self, *_args, **_kwargs):
        pass

    def info(self, *_args, **_kwargs):
        pass

    def warning(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass

    def critical(self, *_args, **_kwargs):
        pass


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
