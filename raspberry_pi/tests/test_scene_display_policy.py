import json
import sys
from pathlib import Path


RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from utils.display_policy import (
    DISPLAY_SCENE_REQUIRED_REASON,
    DISPLAY_SCENE_VIDEO_REASON,
    action_requests_display,
    scene_contains_display_content,
)
from utils.scene_parser import SceneParser
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


class _DisplayPower:
    def __init__(self):
        self.reasons = []

    def request_on(self, reason):
        self.reasons.append(reason)
        return True


class _VideoHandler:
    def __init__(self):
        self.commands = []
        self.images = []

    def handle_command(self, message):
        self.commands.append(message)
        return True

    def show_image(self, filename):
        self.images.append(filename)
        return True


def _scene(actions=None, display_policy=None):
    data = {
        "sceneId": "display_policy_test",
        "initialState": "START",
        "states": {
            "START": {
                "onEnter": actions or [],
                "transitions": [{"type": "always", "goto": "END"}],
            }
        },
    }
    if display_policy:
        data["displayPolicy"] = display_policy
    return data


def _load_scene(tmp_path, data):
    scene_path = tmp_path / "scene.json"
    scene_path.write_text(json.dumps(data), encoding="utf-8")
    parser = SceneParser(logger=_Logger())
    assert parser.load_scene(str(scene_path)) is True
    return parser


def test_auto_policy_detects_play_video(tmp_path):
    parser = _load_scene(
        tmp_path,
        _scene([{"action": "video", "message": "PLAY_VIDEO:intro.mp4"}]),
    )

    assert parser.scene_display_request_reason() == DISPLAY_SCENE_VIDEO_REASON
    assert parser.scene_requires_display() is True


def test_required_policy_requires_display_without_video(tmp_path):
    parser = _load_scene(tmp_path, _scene(display_policy="required"))

    assert parser.scene_display_request_reason() == DISPLAY_SCENE_REQUIRED_REASON


def test_never_policy_suppresses_video_detection(tmp_path):
    parser = _load_scene(
        tmp_path,
        _scene(
            [{"action": "video", "message": "PLAY_VIDEO:intro.mp4"}],
            display_policy="never",
        ),
    )

    assert parser.scene_display_request_reason() is None
    assert parser.scene_requires_display() is False
    assert parser.state_executor.display_auto_enabled is False


def test_stop_video_only_does_not_require_display():
    scene = _scene([{"action": "video", "message": "STOP_VIDEO"}])

    assert scene_contains_display_content(scene) is False


def test_image_show_requires_display():
    action = {"action": "image", "message": "SHOW:slide.jpg"}

    assert action_requests_display(action) is True


def test_state_executor_requests_display_before_video_playback():
    display = _DisplayPower()
    video = _VideoHandler()
    executor = StateExecutor(
        video_handler=video,
        display_power_manager=display,
        logger=_Logger(),
    )

    executor._execute_video({"action": "video", "message": "PLAY_VIDEO:intro.mp4"})

    assert display.reasons == [DISPLAY_SCENE_VIDEO_REASON]
    assert video.commands == ["PLAY_VIDEO:intro.mp4"]


def test_state_executor_respects_display_auto_disable():
    display = _DisplayPower()
    video = _VideoHandler()
    executor = StateExecutor(
        video_handler=video,
        display_power_manager=display,
        logger=_Logger(),
    )
    executor.set_display_auto_enabled(False)

    executor._execute_video({"action": "video", "message": "PLAY_VIDEO:intro.mp4"})

    assert display.reasons == []
    assert video.commands == ["PLAY_VIDEO:intro.mp4"]
