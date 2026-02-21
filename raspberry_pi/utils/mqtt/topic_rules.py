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
        self.room_id = room_id

    def subscriptions(self):
        """Subscription topics required by the current backend behavior."""
        return [
            'devices/+/status',
            f'{self.room_id}/+/feedback',
            f'{self.room_id}/scene',
            f'{self.room_id}/#',
        ]

    def scene_topic(self):
        return f'{self.room_id}/scene'

    def named_scene_topic(self):
        return f'{self.room_id}/start_scene'


class MQTTTopicRules:
    """Collection of reusable topic matching and mapping helpers."""

    @staticmethod
    def is_feedback_topic(topic):
        return topic.endswith(FEEDBACK_SUFFIX)

    @staticmethod
    def is_device_status_parts(topic_parts):
        return (
            len(topic_parts) == 3
            and topic_parts[0] == 'devices'
            and topic_parts[2] == 'status'
        )

    @staticmethod
    def is_scene_start_topic(topic):
        return topic.endswith('/scene')

    @staticmethod
    def is_named_scene_start_topic(topic):
        return topic.endswith('/start_scene')

    @staticmethod
    def expected_feedback_topic(original_topic):
        parts = original_topic.split('/')

        if parts[-1].upper() in ['STOP', 'RESET', 'GLOBAL']:
            return None

        if len(parts) >= 2 and parts[0].startswith('room'):
            return f'{original_topic}{FEEDBACK_SUFFIX}'

        if len(parts) >= 3 and parts[0] == 'devices':
            return f'{original_topic}{FEEDBACK_SUFFIX}'

        return None

    @staticmethod
    def original_topic_from_feedback(feedback_topic):
        if feedback_topic.endswith(FEEDBACK_SUFFIX):
            return feedback_topic[:-len(FEEDBACK_SUFFIX)]
        return None
