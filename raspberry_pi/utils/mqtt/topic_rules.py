#!/usr/bin/env python3
"""
Shared MQTT topic rules and helpers.

This module centralizes topic patterns used by the MQTT client,
message router, and feedback tracker so behavior stays consistent
while remaining easy to maintain.
"""

FEEDBACK_SUFFIX = '/feedback'


class MQTTRoomTopics:
    """Room-scoped topics for control and scene events."""

    def __init__(self, room_id):
        """
        Initialize room topics with a specific room identifier.

        Args:
            room_id: Unique identifier for the room (e.g. 'room1').
        """
        self.room_id = room_id

    def subscriptions(self):
        """
        Return the subscription topics required by the current backend behavior.

        Returns:
            list: MQTT topic strings to subscribe to for this room.
        """
        return [
            'devices/+/status',
            f'{self.room_id}/+/feedback',
            f'{self.room_id}/scene',
            f'{self.room_id}/#',
        ]

    def scene_topic(self):
        """
        Return the topic used to trigger the default scene for this room.

        Returns:
            str: MQTT topic string for scene start commands.
        """
        return f'{self.room_id}/scene'

    def named_scene_topic(self):
        """
        Return the topic used to trigger a named scene for this room.

        Returns:
            str: MQTT topic string for named scene start commands.
        """
        return f'{self.room_id}/start_scene'


class MQTTTopicRules:
    """Collection of reusable topic matching and mapping helpers."""

    @staticmethod
    def is_feedback_topic(topic):
        """
        Check whether a topic is a feedback topic.

        Args:
            topic: The MQTT topic string to evaluate.

        Returns:
            bool: True if the topic ends with the feedback suffix.
        """
        return topic.endswith(FEEDBACK_SUFFIX)

    @staticmethod
    def is_device_status_parts(topic_parts):
        """
        Check whether topic parts represent a device status message.

        Expected pattern: devices/<device_id>/status

        Args:
            topic_parts: List of topic segments split by '/'.

        Returns:
            bool: True if the parts match the device status pattern.
        """
        return (
            len(topic_parts) == 3
            and topic_parts[0] == 'devices'
            and topic_parts[2] == 'status'
        )

    @staticmethod
    def is_scene_start_topic(topic):
        """
        Check whether a topic is a default scene start topic.

        Args:
            topic: The MQTT topic string to evaluate.

        Returns:
            bool: True if the topic ends with '/scene'.
        """
        return topic.endswith('/scene')

    @staticmethod
    def is_named_scene_start_topic(topic):
        """
        Check whether a topic is a named scene start topic.

        Args:
            topic: The MQTT topic string to evaluate.

        Returns:
            bool: True if the topic ends with '/start_scene'.
        """
        return topic.endswith('/start_scene')

    @staticmethod
    def expected_feedback_topic(original_topic):
        """
        Determine the expected feedback topic for a given command topic.

        Returns None for control commands (STOP, RESET, GLOBAL) and for
        topics that do not match known room or device patterns.

        Args:
            original_topic: The MQTT topic the command was published to.

        Returns:
            str or None: The expected feedback topic, or None if no feedback
                is expected for this topic.
        """
        parts = original_topic.split('/')

        # Control commands do not expect feedback
        if parts[-1].upper() in ['STOP', 'RESET', 'GLOBAL']:
            return None

        # Room-scoped topics (e.g. roomX/...) expect feedback
        if len(parts) >= 2 and parts[0].startswith('room'):
            return f'{original_topic}{FEEDBACK_SUFFIX}'

        # Device-scoped topics (e.g. devices/...) expect feedback
        if len(parts) >= 3 and parts[0] == 'devices':
            return f'{original_topic}{FEEDBACK_SUFFIX}'

        return None

    @staticmethod
    def original_topic_from_feedback(feedback_topic):
        """
        Derive the original command topic from a feedback topic.

        Args:
            feedback_topic: The MQTT feedback topic string.

        Returns:
            str or None: The original topic with the feedback suffix removed,
                or None if the topic does not end with the feedback suffix.
        """
        if feedback_topic.endswith(FEEDBACK_SUFFIX):
            return feedback_topic[:-len(FEEDBACK_SUFFIX)]
        return None