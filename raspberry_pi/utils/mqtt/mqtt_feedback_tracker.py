#!/usr/bin/env python3
"""
MQTT Feedback Tracker - Per-command feedback tracking.

Tracks each published command individually and waits for specific feedback.
Example: prefix/motor1 -> expects prefix/motor1/feedback
"""

import time
import threading
from utils.logging_setup import get_logger
from utils.mqtt.topic_rules import MQTTTopicRules


class MQTTFeedbackTracker:
    """
    Per-command feedback tracker for MQTT published messages.

    Tracks each outgoing command and expects a corresponding feedback
    message within a configurable timeout window. Pending feedbacks are
    managed with per-command timers and thread-safe locking.
    """

    def __init__(self, logger=None, feedback_timeout=2):
        """
        Initialize the feedback tracker.

        Args:
            logger: Logger instance for feedback status messages.
            feedback_timeout: Seconds to wait for feedback before timing out
                (default: 2).
        """
        self.logger = logger or get_logger('mqtt_feedback')
        self.feedback_enabled = False
        self.feedback_timeout = feedback_timeout

        # {original_topic: {'command': message, 'timer': Timer, 'start_time': time}}
        self.pending_feedbacks = {}
        self.lock = threading.Lock()

    def enable_feedback_tracking(self):
        """
        Enable feedback tracking and clear any existing pending feedbacks.

        Has no effect if feedback tracking is already enabled.
        """
        with self.lock:
            if not self.feedback_enabled:
                self.feedback_enabled = True
                self.pending_feedbacks.clear()
                self.logger.info("MQTT feedback tracking enabled")

    def disable_feedback_tracking(self):
        """
        Disable feedback tracking and cancel all pending feedback timers.

        Logs a warning for each command that was still awaiting feedback
        at the time tracking was disabled. Has no effect if already disabled.
        """
        with self.lock:
            if self.feedback_enabled:
                self.feedback_enabled = False

                # Cancel all active timers and warn about unresolved feedbacks
                for original_topic, data in self.pending_feedbacks.items():
                    data['timer'].cancel()
                    self.logger.warning(
                        f"Scene ended with pending feedback on topic: {original_topic}"
                    )

                self.pending_feedbacks.clear()
                self.logger.info("MQTT feedback tracking disabled")

    def track_published_message(self, original_topic, message):
        """
        Track an individual published command and start its feedback timer.

        Skips audio/video topics (handled locally) and topics for which no
        feedback topic can be determined. If a timer already exists for the
        same topic, it is cancelled and replaced.

        Args:
            original_topic: The MQTT topic the command was published to.
            message: The command payload that was published.
        """
        if not self.feedback_enabled:
            return

        # Skip audio/video topics as they are handled locally
        if original_topic.endswith('/audio') or original_topic.endswith('/video'):
            self.logger.debug(
                f"Skipping feedback tracking for local topic: {original_topic}"
            )
            return

        expected_feedback_topic = MQTTTopicRules.expected_feedback_topic(original_topic)
        if expected_feedback_topic is None:
            self.logger.debug(f"No feedback expected for topic: {original_topic}")
            return

        with self.lock:
            # Cancel the existing timer if this topic already has a pending feedback
            if original_topic in self.pending_feedbacks:
                self.pending_feedbacks[original_topic]['timer'].cancel()

            timer = threading.Timer(
                self.feedback_timeout,
                self._handle_feedback_timeout,
                args=[original_topic, message]
            )

            self.pending_feedbacks[original_topic] = {
                'command': message,
                'timer': timer,
                'start_time': time.time(),
                'expected_feedback_topic': expected_feedback_topic
            }
            timer.start()
            self.logger.debug(
                f"📤 Sent: {original_topic} -> expecting feedback on: {expected_feedback_topic}"
            )

    def handle_feedback_message(self, feedback_topic, feedback_payload):
        """
        Process an incoming feedback message and resolve the matching pending command.

        Cancels the associated timeout timer and logs whether the feedback
        indicated success or an error. Logs a debug message if no matching
        pending command is found.

        Args:
            feedback_topic: The MQTT topic the feedback was received on.
            feedback_payload: The feedback payload string (e.g. 'OK' or error text).
        """
        # Resolve the original command topic from the feedback topic
        original_topic = MQTTTopicRules.original_topic_from_feedback(feedback_topic)

        with self.lock:
            if original_topic and original_topic in self.pending_feedbacks:
                start_time = self.pending_feedbacks[original_topic]['start_time']
                elapsed_time = time.time() - start_time

                self.pending_feedbacks[original_topic]['timer'].cancel()
                del self.pending_feedbacks[original_topic]

                if feedback_payload.upper() == "OK":
                    self.logger.info(
                        f"Feedback OK: {original_topic} ({elapsed_time:.3f}s)"
                    )
                else:
                    self.logger.warning(
                        f"Feedback ERROR: {original_topic} -> "
                        f"{feedback_payload} ({elapsed_time:.3f}s)"
                    )
            else:
                self.logger.debug(
                    f"Received feedback on {feedback_topic} with no pending command."
                )

    def _handle_feedback_timeout(self, original_topic, message):
        """
        Handle a feedback timeout for a command that received no response.

        Called automatically by the per-command timer when the feedback
        window expires. Removes the pending entry and logs a timeout error.

        Args:
            original_topic: The MQTT topic the original command was sent to.
            message: The command payload that was published.
        """
        with self.lock:
            if original_topic in self.pending_feedbacks:
                expected_topic = self.pending_feedbacks[original_topic][
                    'expected_feedback_topic'
                ]
                del self.pending_feedbacks[original_topic]
                self.logger.error(
                    f"FEEDBACK TIMEOUT: No response from device. "
                    f"Topic: {original_topic}, Command: {message}, "
                    f"Expected: {expected_topic}"
                )