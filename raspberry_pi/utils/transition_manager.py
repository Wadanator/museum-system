# raspberry_pi/utils/transition_manager.py
#!/usr/bin/env python3
"""
Transition Manager - Manages state transitions (thread-safe and optimized).
"""

from collections import deque
from threading import Lock
import time
from utils.logging_setup import get_logger


class TransitionManager:
    """
    Evaluates and dispatches state transitions for the scene state machine.

    Maintains thread-safe event queues for MQTT, audio end, and video end
    events. Transition types are dispatched via a handler dictionary,
    making it straightforward to add new transition types.
    """

    EVENT_QUEUE_LIMIT = 50
    DROP_WARNING_INTERVAL_SECONDS = 60

    def __init__(self, logger=None):
        """
        Initialize the transition manager with empty event queues.

        Args:
            logger: Logger instance for transition events.
        """
        self.logger = logger or get_logger("TransitionManager")
        self.lock = Lock()

        # Event queues - deque with maxlen automatically discards oldest entries
        self.mqtt_events = deque(maxlen=self.EVENT_QUEUE_LIMIT)
        self.audio_end_events = deque(maxlen=self.EVENT_QUEUE_LIMIT)
        self.video_end_events = deque(maxlen=self.EVENT_QUEUE_LIMIT)
        self._drop_counts_since_warning = {
            "mqtt": 0,
            "audioEnd": 0,
            "videoEnd": 0,
        }
        self._last_drop_warning_ts = {
            "mqtt": 0.0,
            "audioEnd": 0.0,
            "videoEnd": 0.0,
        }

        # Transition type dispatch table: type string -> handler function
        self.transition_handlers = {
            "timeout": self._check_timeout,
            "audioEnd": self._check_audio_end,
            "videoEnd": self._check_video_end,
            "mqttMessage": self._check_mqtt_message,
            "always": self._check_always
        }

    def check_transitions(self, state_data, state_elapsed_time):
        """
        Evaluate all transitions for the current state and return the next state.

        Iterates through the state's transition list in order and returns the
        first transition target that fires. Access to event queues is
        protected by a lock for thread safety.

        Args:
            state_data: State definition dict containing a 'transitions' list.
            state_elapsed_time: Seconds elapsed since the current state was entered.

        Returns:
            str or None: Name of the next state if a transition fired,
                or None if no transition condition is met.
        """
        transitions = state_data.get("transitions", [])
        if not transitions:
            return None

        # Thread-safe access to event queues during evaluation
        with self.lock:
            for transition in transitions:
                trans_type = transition.get("type")
                handler = self.transition_handlers.get(trans_type)

                if handler:
                    # All handlers share the same standardized signature
                    next_state = handler(transition, state_elapsed_time)
                    if next_state:
                        return next_state
                else:
                    self.logger.warning(
                        f"Unknown transition type: {trans_type}"
                    )

        return None

    # --- Internal Check Methods ---
    # All accept (transition, state_elapsed_time) for a uniform call signature

    def _check_timeout(self, transition, state_elapsed_time):
        """
        Evaluate a timeout transition.

        Args:
            transition: Transition definition dict with a 'delay' key.
            state_elapsed_time: Seconds elapsed in the current state.

        Returns:
            str or None: Target state name if the delay has elapsed, else None.
        """
        delay = transition.get("delay", 0)

        if state_elapsed_time >= delay:
            return self._get_goto(
                transition,
                f"Timeout triggered ({delay}s)",
                level="debug"
            )
        return None

    def _check_audio_end(self, transition, _):
        """
        Evaluate an audioEnd transition.

        Fires when the target audio file has been registered as finished.
        Removes the consumed event from the queue.

        Args:
            transition: Transition definition dict with a 'target' key.
            _: Unused elapsed time argument (kept for uniform signature).

        Returns:
            str or None: Target state name if the audio end event is found,
                else None.
        """
        target = transition.get("target")

        # Iterate a snapshot; the Lock in check_transitions ensures safety
        for event in list(self.audio_end_events):
            if event == target:
                self.audio_end_events.remove(event)  # Consume the processed event
                return self._get_goto(
                    transition, f"AudioEnd triggered ({target})"
                )
        return None

    def _check_video_end(self, transition, _):
        """
        Evaluate a videoEnd transition.

        Fires when the target video file has been registered as finished.
        Removes the consumed event from the queue.

        Args:
            transition: Transition definition dict with a 'target' key.
            _: Unused elapsed time argument (kept for uniform signature).

        Returns:
            str or None: Target state name if the video end event is found,
                else None.
        """
        target = transition.get("target")

        for event in list(self.video_end_events):
            if event == target:
                self.video_end_events.remove(event)
                return self._get_goto(
                    transition, f"VideoEnd triggered ({target})"
                )
        return None

    def _check_mqtt_message(self, transition, _):
        """
        Evaluate an mqttMessage transition.

        Fires when a matching topic/message pair is found in the event queue.
        Removes the consumed event from the queue.

        Args:
            transition: Transition definition dict with 'topic' and 'message' keys.
            _: Unused elapsed time argument (kept for uniform signature).

        Returns:
            str or None: Target state name if a matching MQTT event is found,
                else None.
        """
        topic = transition.get("topic")
        message = transition.get("message")

        for event in list(self.mqtt_events):
            if event.get("topic") == topic and event.get("message") == message:
                self.mqtt_events.remove(event)
                return self._get_goto(
                    transition, f"MQTT triggered ({topic}={message})"
                )
        return None

    def _check_always(self, transition, _):
        """
        Evaluate an always transition (fires immediately unconditionally).

        Args:
            transition: Transition definition dict with a 'goto' key.
            _: Unused elapsed time argument (kept for uniform signature).

        Returns:
            str or None: Target state name.
        """
        return self._get_goto(transition, "Always transition")

    def _get_goto(self, transition, log_msg, level="info"):
        """
        Extract the 'goto' target from a transition and log the trigger message.

        Args:
            transition: Transition definition dict containing a 'goto' key.
            log_msg: Message to log when the transition fires.

        Returns:
            str or None: The target state name, or None if 'goto' is missing.
        """
        goto = transition.get("goto")
        if goto is None:
            self.logger.error(f"Transition missing 'goto': {transition}")
            return None
        if level == "debug":
            self.logger.debug(f"{log_msg} -> {goto}")
        elif level == "warning":
            self.logger.warning(f"{log_msg} -> {goto}")
        elif level == "error":
            self.logger.error(f"{log_msg} -> {goto}")
        else:
            self.logger.debug(f"{log_msg} -> {goto}")
        return goto

    # --- Event Registration Methods (Thread-Safe) ---

    def _append_event(self, queue, queue_name, event):
        """
        Append one event and record when deque(maxlen) will discard oldest data.

        The caller must hold self.lock.
        """
        if queue.maxlen is not None and len(queue) >= queue.maxlen:
            self._record_queue_drop(queue_name, queue.maxlen)
        queue.append(event)

    def _record_queue_drop(self, queue_name, queue_limit):
        """Log a rate-limited warning when transition events overflow."""
        self._drop_counts_since_warning[queue_name] += 1

        now = time.monotonic()
        last_warning = self._last_drop_warning_ts[queue_name]
        if (
            last_warning
            and now - last_warning < self.DROP_WARNING_INTERVAL_SECONDS
        ):
            return

        dropped = self._drop_counts_since_warning[queue_name]
        self._drop_counts_since_warning[queue_name] = 0
        self._last_drop_warning_ts[queue_name] = now
        self.logger.warning(
            "Transition event queue full; dropped %s %s event(s) "
            "(queue_limit=%s)",
            dropped,
            queue_name,
            queue_limit,
        )

    def register_mqtt_event(self, topic, message):
        """
        Register an incoming MQTT event for transition evaluation.

        Called from the MQTT message callback. Logs an error and returns
        early if either topic or message is None.

        Args:
            topic: The MQTT topic the message was received on.
            message: The message payload string.
        """
        if topic is None or message is None:
            self.logger.error("MQTT event missing topic or message")
            return

        with self.lock:
            self._append_event(
                self.mqtt_events,
                "mqtt",
                {"topic": topic, "message": message},
            )

        self.logger.debug(f"MQTT event registered: {topic}={message}")

    def register_audio_end(self, audio_file):
        """
        Register an audio file completion event.

        Args:
            audio_file: Filename of the audio track that finished playing.
        """
        with self.lock:
            self._append_event(self.audio_end_events, "audioEnd", audio_file)
        self.logger.debug(f"AudioEnd event registered: {audio_file}")

    def register_video_end(self, video_file):
        """
        Register a video file completion event.

        Args:
            video_file: Filename of the video that finished playing.
        """
        with self.lock:
            self._append_event(self.video_end_events, "videoEnd", video_file)
        self.logger.debug(f"VideoEnd event registered: {video_file}")

    def clear_events(self):
        """
        Clear all pending events from all queues.

        Typically called on state change to discard events that are no
        longer relevant to the incoming state.
        """
        with self.lock:
            cleared_counts = (
                len(self.mqtt_events),
                len(self.audio_end_events),
                len(self.video_end_events)
            )
            self.mqtt_events.clear()
            self.audio_end_events.clear()
            self.video_end_events.clear()

        self.logger.debug(
            f"All events cleared (mqtt={cleared_counts[0]}, "
            f"audio={cleared_counts[1]}, video={cleared_counts[2]})"
        )
