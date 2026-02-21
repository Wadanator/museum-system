#!/usr/bin/env python3
"""
State Executor - Executes actions within scene states.

Designed for expandability: new action types can be added by registering
an additional handler in the action_handlers dictionary.
"""

from utils.logging_setup import get_logger


class StateExecutor:
    """
    Executes onEnter, onExit, and timeline actions for scene states.

    Dispatches each action to a registered handler function based on the
    action's 'action' type field. Supports dynamic extension by adding
    entries to the action_handlers dictionary.
    """

    def __init__(self, mqtt_client=None, audio_handler=None,
                 video_handler=None, logger=None):
        """
        Initialize the state executor and register action handlers.

        Args:
            mqtt_client: MQTT client instance for publishing commands.
            audio_handler: Audio handler for playback commands.
            video_handler: Video handler for playback commands.
            logger: Logger instance for execution events.
        """
        self.mqtt_client = mqtt_client
        self.audio_handler = audio_handler
        self.video_handler = video_handler
        self.logger = logger or get_logger("StateExecutor")

        # Tracks timeline actions already executed in the current state
        self.executed_timeline_actions = set()

        # Action type dispatch table.
        # To add a new action type (e.g. "lights"), register it here.
        self.action_handlers = {
            "mqtt": self._execute_mqtt,
            "audio": self._execute_audio,
            "video": self._execute_video
        }

    def execute_onEnter(self, state_data):
        """
        Execute all onEnter actions for a state immediately upon entry.

        Args:
            state_data: State definition dict containing an 'onEnter' list.
        """
        actions = state_data.get("onEnter", [])
        if not actions:
            return

        self.logger.debug(f"Executing onEnter: {len(actions)} actions")
        for action in actions:
            self._execute_action(action)

    def execute_onExit(self, state_data):
        """
        Execute all onExit actions for a state upon departure.

        Args:
            state_data: State definition dict containing an 'onExit' list.
        """
        actions = state_data.get("onExit", [])
        if not actions:
            return

        self.logger.debug(f"Executing onExit: {len(actions)} actions")
        for action in actions:
            self._execute_action(action)

    def check_and_execute_timeline(self, state_data, state_elapsed_time):
        """
        Execute any timeline actions whose trigger time has been reached.

        Each timeline item is identified by a unique action_id to ensure
        it fires exactly once per state entry. Supports both single-action
        items ('action' key) and multi-action items ('actions' key).

        Args:
            state_data: State definition dict containing a 'timeline' list.
            state_elapsed_time: Seconds elapsed since the current state was entered.
        """
        timeline = state_data.get("timeline", [])
        if not timeline:
            return

        for i, timeline_item in enumerate(timeline):
            if not isinstance(timeline_item, dict):
                self.logger.error(
                    f"Invalid timeline item at index {i}: {timeline_item}"
                )
                continue

            trigger_time = timeline_item.get("at", 0)
            # Unique ID per timeline item to prevent re-execution within a state
            action_id = f"{id(state_data)}_{i}_{trigger_time}"

            # Skip already-executed actions
            if action_id in self.executed_timeline_actions:
                continue

            # Fire the action if its trigger time has been reached
            if state_elapsed_time >= trigger_time:
                self.logger.debug(f"Timeline trigger at {trigger_time}s")

                # Single action or grouped actions list
                if "action" in timeline_item:
                    self._execute_action(timeline_item)
                elif "actions" in timeline_item:
                    actions = timeline_item["actions"]
                    if not isinstance(actions, list):
                        self.logger.error(
                            f"Invalid actions list at index {i}: {actions}"
                        )
                        continue
                    for action in actions:
                        self._execute_action(action)

                self.executed_timeline_actions.add(action_id)

    def reset_timeline_tracking(self):
        """Clear the set of executed timeline actions on state change."""
        self.executed_timeline_actions.clear()

    def _execute_action(self, action):
        """
        Dispatch a single action to its registered handler.

        Args:
            action: Action dict containing at minimum an 'action' type key.
        """
        if not isinstance(action, dict):
            self.logger.error(f"Action must be a dict: {action}")
            return

        action_type = action.get("action")
        if not action_type:
            self.logger.error(f"Action missing 'action' type: {action}")
            return

        # Dynamic dispatch via registered handler table
        handler = self.action_handlers.get(action_type)

        if handler:
            try:
                handler(action)
            except Exception as e:
                self.logger.error(
                    f"Error executing action '{action_type}': {e}"
                )
        else:
            self.logger.warning(f"Unknown action type: {action_type}")

    # --- Concrete action implementations ---

    def _execute_mqtt(self, action):
        """
        Publish an MQTT message for an mqtt-type action.

        Logs a simulation warning if the MQTT client is not connected.

        Args:
            action: Action dict with 'topic' and 'message' keys.
        """
        topic = action.get("topic")
        message = action.get("message")

        if not topic or not message:
            self.logger.error(
                f"MQTT action missing topic or message: {action}"
            )
            return

        if self.mqtt_client and self.mqtt_client.is_connected():
            try:
                success = self.mqtt_client.publish(topic, message, retain=False)
                if success:
                    self.logger.debug(f"MQTT: {topic} = {message}")
                else:
                    self.logger.error(f"MQTT publish failed: {topic}")
            except Exception as exc:
                self.logger.error(
                    f"MQTT publish raised exception for {topic}: {exc}"
                )
        else:
            self.logger.warning(
                f"MQTT not connected (simulation): {topic} = {message}"
            )

    def _execute_audio(self, action):
        """
        Send a command to the audio handler for an audio-type action.

        Logs a simulation warning if no audio handler is available.

        Args:
            action: Action dict with a 'message' key containing the command string.
        """
        message = action.get("message")

        if not message:
            self.logger.error(f"Audio action missing message: {action}")
            return

        if self.audio_handler:
            try:
                success = self.audio_handler.handle_command(message)
            except Exception as exc:
                self.logger.error(
                    f"Audio handler raised exception for '{message}': {exc}"
                )
                success = False

            if success:
                self.logger.debug(f"Audio: {message}")
            else:
                self.logger.error(f"Audio command failed: {message}")
        else:
            self.logger.warning(f"No audio handler (simulation): {message}")

    def _execute_video(self, action):
        """
        Send a command to the video handler for a video-type action.

        Logs a simulation warning if no video handler is available.

        Args:
            action: Action dict with a 'message' key containing the command string.
        """
        message = action.get("message")

        if not message:
            self.logger.error(f"Video action missing message: {action}")
            return

        if self.video_handler:
            try:
                success = self.video_handler.handle_command(message)
            except Exception as exc:
                self.logger.error(
                    f"Video handler raised exception for '{message}': {exc}"
                )
                success = False

            if success:
                self.logger.debug(f"Video: {message}")
            else:
                self.logger.error(f"Video command failed: {message}")
        else:
            self.logger.warning(f"No video handler (simulation): {message}")