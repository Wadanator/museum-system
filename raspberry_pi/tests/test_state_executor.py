import sys
from pathlib import Path


# Ensure raspberry_pi/ is importable when tests are executed from repository root.
RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from utils.state_executor import StateExecutor


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

    def messages(self, level=None):
        return [
            message
            for record_level, message in self.records
            if level is None or record_level == level
        ]


class _FakeVideoHandler:
    def __init__(self, show_success=True, stop_success=True):
        self.show_success = show_success
        self.stop_success = stop_success
        self.images_shown = []
        self.stop_calls = 0

    def show_image(self, filename):
        self.images_shown.append(filename)
        return self.show_success

    def stop_video(self):
        self.stop_calls += 1
        return self.stop_success


def _build_executor(video_handler=None):
    logger = _Logger()
    executor = StateExecutor(video_handler=video_handler, logger=logger)
    return executor, logger


def test_image_show_calls_video_handler_show_image():
    video = _FakeVideoHandler()
    executor, logger = _build_executor(video)

    assert executor._execute_image(
        {"action": "image", "message": "SHOW:file.png"}
    ) is True

    assert video.images_shown == ["file.png"]
    assert video.stop_calls == 0
    assert logger.messages("debug") == ["Image: SHOW:file.png"]


def test_image_clear_calls_video_handler_stop_video():
    video = _FakeVideoHandler()
    executor, _logger = _build_executor(video)

    assert executor._execute_image(
        {"action": "image", "message": "CLEAR"}
    ) is True

    assert video.images_shown == []
    assert video.stop_calls == 1


def test_image_default_calls_video_handler_stop_video():
    video = _FakeVideoHandler()
    executor, _logger = _build_executor(video)

    assert executor._execute_image(
        {"action": "image", "message": "DEFAULT"}
    ) is True

    assert video.stop_calls == 1


def test_image_show_without_filename_fails_without_video_call():
    video = _FakeVideoHandler()
    executor, logger = _build_executor(video)

    assert executor._execute_image(
        {"action": "image", "message": "SHOW:"}
    ) is False

    assert video.images_shown == []
    assert video.stop_calls == 0
    assert "SHOW image command requires a filename" in logger.messages("error")[0]


def test_image_bare_filename_fails_without_video_call():
    video = _FakeVideoHandler()
    executor, logger = _build_executor(video)

    assert executor._execute_image(
        {"action": "image", "message": "file.png"}
    ) is False

    assert video.images_shown == []
    assert video.stop_calls == 0
    assert "SHOW:<filename> or CLEAR" in logger.messages("error")[0]


def test_image_unsafe_path_fails_without_video_call():
    video = _FakeVideoHandler()
    executor, logger = _build_executor(video)

    assert executor._execute_image(
        {"action": "image", "message": "SHOW:../file.png"}
    ) is False

    assert video.images_shown == []
    assert video.stop_calls == 0
    assert "basename" in logger.messages("error")[0]


def test_image_unsupported_extension_fails_without_video_call():
    video = _FakeVideoHandler()
    executor, logger = _build_executor(video)

    assert executor._execute_image(
        {"action": "image", "message": "SHOW:file.mp4"}
    ) is False

    assert video.images_shown == []
    assert video.stop_calls == 0
    assert ".png" in logger.messages("error")[0]


def test_image_without_video_handler_logs_simulation_warning():
    executor, logger = _build_executor()

    assert executor._execute_image(
        {"action": "image", "message": "SHOW:file.png"}
    ) is False

    assert logger.messages("warning") == [
        "No video handler (simulation): SHOW:file.png"
    ]


def test_execute_on_enter_dispatches_image_action():
    video = _FakeVideoHandler()
    executor, _logger = _build_executor(video)

    executor.execute_onEnter(
        {"onEnter": [{"action": "image", "message": "SHOW:intro.jpeg"}]}
    )

    assert video.images_shown == ["intro.jpeg"]
