#!/usr/bin/env python3
"""
MQTT Feedback Tracker - Per-command feedback tracking with actuator state integration.

Tracks each published command individually and waits for the corresponding
/feedback response within a configurable timeout window. On successful feedback,
the confirmed state is propagated to MQTTActuatorStateStore when one is wired in.
"""

import time
import threading
from typing import Optional

from utils.logging_setup import get_logger
from utils.mqtt.topic_rules import MQTTTopicRules


class MQTTFeedbackTracker:
    """
    Per-command feedback tracker for MQTT published messages.

    Tracks each outgoing command and expects a corresponding feedback
    message within a configurable timeout window. Pending feedbacks are
    managed with per-command timers and thread-safe locking.

    Optionally integrates with MQTTActuatorStateStore to record confirmed
    hardware states when feedback OK is received.
    """

    def __init__(self, logger=None, feedback_timeout: float = 2) -> None:
        """
        Initialize the feedback tracker.

        Args:
            logger: Logger instance for feedback status messages.
            feedback_timeout: Seconds to wait for feedback before timing out.
        """
        self.logger = logger or get_logger('mqtt_feedback')
        self.feedback_enabled = False
        self.feedback_timeout = feedback_timeout

        # {original_topic: {'command': str, 'timer': Timer, 'start_time': float,
        #                   'expected_feedback_topic': str}}
        self.pending_feedbacks = {}
        self.lock = threading.Lock()

        # Optional state store — set via set_state_store()
        self._state_store = None

    # ==========================================================================
    # CONFIGURATION
    # ==========================================================================

    def set_state_store(self, store) -> None:
        """
        Wire an MQTTActuatorStateStore for confirmed state propagation.

        When set, successful feedback messages cause the store to record
        the confirmed ON/OFF state for the corresponding endpoint topic.

        Args:
            store: MQTTActuatorStateStore instance or None to disable.
        """
        self._state_store = store

    # ==========================================================================
    # TRACKING LIFECYCLE
    # ==========================================================================

    def enable_feedback_tracking(self) -> None:
        """
        Enable feedback tracking and clear any existing pending feedbacks.

        Has no effect if feedback tracking is already enabled.
        """
        with self.lock:
            if not self.feedback_enabled:
                self.feedback_enabled = True
                self.pending_feedbacks.clear()
                self.logger.info("MQTT feedback tracking enabled")

    def disable_feedback_tracking(self) -> None:
        """
        Disable feedback tracking and cancel all pending feedback timers.

        Cancels any pending feedback timers and clears internal tracking state.
        This is expected during normal scene shutdown, so pending entries are
        reported as a single info summary instead of per-topic warnings.

        Has no effect if already disabled.
        """
        with self.lock:
            if self.feedback_enabled:
                self.feedback_enabled = False
                pending_count = len(self.pending_feedbacks)
                for data in self.pending_feedbacks.values():
                    data['timer'].cancel()
                if pending_count:
                    self.logger.info(
                        "Scene finished; cleared %d pending feedback entries",
                        pending_count,
                    )
                self.pending_feedbacks.clear()
                self.logger.info("MQTT feedback tracking disabled")

    def track_published_message(self, original_topic: str, message: str) -> None:
        """
        Track an individual published command and start its feedback timer.

        Also records the desired state in MQTTActuatorStateStore (if wired)
        so the UI can show the intended state before feedback arrives.

        Skips audio/video topics (handled locally) and topics for which no
        feedback topic can be determined. If a timer already exists for the
        same topic, it is cancelled and replaced.

        Args:
            original_topic: The MQTT topic the command was published to.
            message: The command payload that was published.
        """
        # Always record desired state regardless of feedback tracking mode
        if self._state_store:
            self._state_store.update_desired(original_topic, message)

        if not self.feedback_enabled:
            return

        # Skip audio/video topics as they are handled locally
        if original_topic.endswith(('/audio', '/video')):
            self.logger.debug(
                f"Skipping feedback tracking for local topic: {original_topic}"
            )
            return

        expected_feedback_topic = MQTTTopicRules.expected_feedback_topic(original_topic)
        if expected_feedback_topic is None:
            self.logger.debug(f"No feedback expected for topic: {original_topic}")
            return

        with self.lock:
            if original_topic in self.pending_feedbacks:
                self.pending_feedbacks[original_topic]['timer'].cancel()

            timer = threading.Timer(
                self.feedback_timeout,
                self._handle_feedback_timeout,
                args=[original_topic, message],
            )

            self.pending_feedbacks[original_topic] = {
                'command': message,
                'timer': timer,
                'start_time': time.time(),
                'expected_feedback_topic': expected_feedback_topic,
            }
            timer.start()
            self.logger.debug(
                f"Sent: {original_topic} -> expecting feedback: {expected_feedback_topic}"
            )

    def handle_feedback_message(self, feedback_topic: str, feedback_payload: str) -> None:
        """
        Process an incoming feedback message and resolve the matching pending command.

        On successful feedback (payload == 'OK'), propagates the confirmed
        state to MQTTActuatorStateStore if one is wired in.

        Cancels the associated timeout timer and logs the latency. Logs a
        debug message if no matching pending command is found.

        Args:
            feedback_topic: The MQTT topic the feedback was received on.
            feedback_payload: The feedback payload string ('OK' or error text).
        """
        original_topic = MQTTTopicRules.original_topic_from_feedback(feedback_topic)

        with self.lock:
            if original_topic and original_topic in self.pending_feedbacks:
                data = self.pending_feedbacks[original_topic]
                elapsed = time.time() - data['start_time']
                command = data['command']

                data['timer'].cancel()
                del self.pending_feedbacks[original_topic]

                is_ok = feedback_payload.upper() == 'OK'

                if is_ok:
                    self.logger.info(
                        f"Feedback OK: {original_topic} ({elapsed * 1000:.0f}ms)"
                    )
                else:
                    self.logger.warning(
                        f"Feedback ERROR: {original_topic} -> "
                        f"{feedback_payload} ({elapsed * 1000:.0f}ms)"
                    )

                # Propagate confirmed state outside the lock to avoid potential
                # re-entrant locking inside the store's own lock.
                confirmed_command = command if is_ok else None
            else:
                self.logger.debug(
                    f"Unmatched feedback on {feedback_topic}"
                )
                confirmed_command = None
                original_topic = None

        if confirmed_command is not None and self._state_store and original_topic:
            self._state_store.update_confirmed(
                original_topic, confirmed_command, source='feedback'
            )

    # ==========================================================================
    # INTERNAL HELPERS
    # ==========================================================================

    def _handle_feedback_timeout(self, original_topic: str, message: str) -> None:
        """
        Handle a feedback timeout for a command that received no response.

        Args:
            original_topic: The MQTT topic the original command was sent to.
            message: The command payload that was published.
        """
        with self.lock:
            if original_topic in self.pending_feedbacks:
                expected = self.pending_feedbacks[original_topic][
                    'expected_feedback_topic'
                ]
                del self.pending_feedbacks[original_topic]
                self.logger.error(
                    f"FEEDBACK TIMEOUT: {original_topic} | command={message} "
                    f"| expected={expected} | timeout={self.feedback_timeout}s"
                )