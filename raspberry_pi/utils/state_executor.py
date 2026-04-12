#!/usr/bin/env python3
"""
State Executor - Executes actions within scene states.

Designed for expandability: new action types can be added by registering
an additional handler in the action_handlers dictionary.

Timeline actions are scheduled via threading.Timer on state entry rather
than evaluated on each processing tick. A monotonic state generation
counter ensures that timers belonging to a previous state never fire
after a state transition has occurred, even if the timer callback has
already been invoked by the OS when cancel() is called.
"""

import threading
from utils.logging_setup import get_logger


class StateExecutor:
    """
    Executes onEnter, onExit, and timeline actions for scene states.

    Dispatches each action to a registered handler function based on the
    action's 'action' type field. Supports dynamic extension by adding
    entries to the action_handlers dictionary.

    Timeline actions are pre-scheduled with threading.Timer on state entry.
    A state generation counter is used as a cancellation token: each state
    increments the counter, and timers that fire after a transition silently
    discard themselves because their captured generation no longer matches.

    This avoids the race condition where threading.Timer.cancel() arrives
    too late to stop a callback that has already started executing.
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

        self._active_timers: list[threading.Timer] = []
        self._state_generation: int = 0

        self.action_handlers = {
            "mqtt": self._execute_mqtt,
            "audio": self._execute_audio,
            "video": self._execute_video
        }

    def execute_onEnter(self, state_data):
        """
        Execute all onEnter actions for a state immediately upon entry.

        Schedules any timeline actions defined in the state immediately
        after the onEnter actions have been dispatched.

        Args:
            state_data: State definition dict containing an 'onEnter' list.
        """
        for action in state_data.get("onEnter", []):
            self._execute_action(action)

        self._schedule_timeline(state_data)

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

    def _schedule_timeline(self, state_data):
        """
        Schedule all timeline actions as threading.Timer instances.

        Captures the current state generation at scheduling time. Timers
        that fire after a state transition will detect the generation
        mismatch and discard themselves without executing any actions.

        Args:
            state_data: State definition dict containing a 'timeline' list.
        """
        timeline = state_data.get("timeline", [])
        if not timeline:
            return

        current_generation = self._state_generation

        for i, item in enumerate(timeline):
            if not isinstance(item, dict):
                self.logger.error(f"Invalid timeline item at index {i}: {item}")
                continue

            trigger_time = item.get("at", 0)

            timer = threading.Timer(
                trigger_time,
                self._fire_timeline_item,
                args=[item, current_generation]
            )
            timer.daemon = True
            timer.start()
            self._active_timers.append(timer)

        self.logger.debug(
            f"Scheduled {len(timeline)} timeline actions "
            f"(generation {current_generation})"
        )

    def _fire_timeline_item(self, item, generation):
        """
        Execute a single timeline action invoked by its threading.Timer.

        Discards the action silently if the state generation has advanced,
        meaning a state transition occurred after this timer was scheduled.
        This is the primary guard against stale timers executing in a
        state they were never meant for.

        Args:
            item: Timeline item dict to execute.
            generation: State generation captured at scheduling time.
        """
        if generation != self._state_generation:
            return

        if "action" in item:
            self._execute_action(item)
        elif "actions" in item:
            actions = item["actions"]
            if not isinstance(actions, list):
                self.logger.error(
                    f"Invalid actions list in timeline item: {actions}"
                )
                return
            for action in actions:
                self._execute_action(action)

    def check_and_execute_timeline(self, state_data, state_elapsed_time):
        """
        No-op retained for compatibility with the scene_parser processing loop.

        Timeline execution is handled entirely by threading.Timer instances
        scheduled in _schedule_timeline. This method is called on every
        processing tick by scene_parser but performs no work.

        Args:
            state_data: Unused.
            state_elapsed_time: Unused.
        """

    def reset_timeline_tracking(self):
        """
        Invalidate all pending timeline timers and advance the state generation.

        Incrementing the generation counter immediately neutralises any timer
        that has already entered its callback but not yet checked the guard,
        as well as any timer that fires after this call returns. Calling
        cancel() is a best-effort optimisation to avoid unnecessary thread
        wakeups, not a correctness requirement.

        Called on every state transition by scene_parser.
        """
        self._state_generation += 1

        for timer in self._active_timers:
            timer.cancel()
        self._active_timers.clear()

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
            except Exception as e:
                self.logger.error(
                    f"MQTT publish raised exception for {topic}: {e}"
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
            except Exception as e:
                self.logger.error(
                    f"Audio handler raised exception for '{message}': {e}"
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
            except Exception as e:
                self.logger.error(
                    f"Video handler raised exception for '{message}': {e}"
                )
                success = False

            if success:
                self.logger.debug(f"Video: {message}")
            else:
                self.logger.error(f"Video command failed: {message}")
        else:
            self.logger.warning(f"No video handler (simulation): {message}")