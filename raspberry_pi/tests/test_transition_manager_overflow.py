from utils.transition_manager import TransitionManager


class _Logger:
    def __init__(self):
        self.debugs = []
        self.warnings = []
        self.errors = []

    def debug(self, message, *args):
        self.debugs.append(message % args if args else message)

    def warning(self, message, *args):
        self.warnings.append(message % args if args else message)

    def error(self, message, *args):
        self.errors.append(message % args if args else message)


def test_transition_event_queue_does_not_warn_before_limit():
    logger = _Logger()
    manager = TransitionManager(logger=logger)

    for index in range(manager.EVENT_QUEUE_LIMIT):
        manager.register_mqtt_event(f"room1/button/{index}", "ON")

    assert len(manager.mqtt_events) == manager.EVENT_QUEUE_LIMIT
    assert logger.warnings == []


def test_transition_event_queue_warns_when_mqtt_events_are_dropped():
    logger = _Logger()
    manager = TransitionManager(logger=logger)

    for index in range(manager.EVENT_QUEUE_LIMIT + 1):
        manager.register_mqtt_event(f"room1/button/{index}", "ON")

    assert len(manager.mqtt_events) == manager.EVENT_QUEUE_LIMIT
    assert manager.mqtt_events[0] == {
        "topic": "room1/button/1",
        "message": "ON",
    }
    assert logger.warnings == [
        "Transition event queue full; dropped 1 mqtt event(s) "
        "(queue_limit=50)"
    ]


def test_transition_event_drop_warning_is_rate_limited():
    logger = _Logger()
    manager = TransitionManager(logger=logger)

    for index in range(manager.EVENT_QUEUE_LIMIT + 3):
        manager.register_audio_end(f"track_{index}.mp3")

    assert len(manager.audio_end_events) == manager.EVENT_QUEUE_LIMIT
    assert logger.warnings == [
        "Transition event queue full; dropped 1 audioEnd event(s) "
        "(queue_limit=50)"
    ]
    assert manager._drop_counts_since_warning["audioEnd"] == 2


def test_transition_event_drop_monitoring_covers_video_queue():
    logger = _Logger()
    manager = TransitionManager(logger=logger)

    for index in range(manager.EVENT_QUEUE_LIMIT + 1):
        manager.register_video_end(f"clip_{index}.mp4")

    assert len(manager.video_end_events) == manager.EVENT_QUEUE_LIMIT
    assert logger.warnings == [
        "Transition event queue full; dropped 1 videoEnd event(s) "
        "(queue_limit=50)"
    ]
