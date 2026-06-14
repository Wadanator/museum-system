"""Scene start/run orchestration extracted from MuseumController."""

import threading
import time


OUTCOME_NORMAL_END = 'normal_end'
OUTCOME_MISSING_SCENE = 'missing_scene'
OUTCOME_LOAD_FAILURE = 'load_failure'
OUTCOME_PARSER_UNAVAILABLE = 'parser_unavailable'
OUTCOME_START_FAILURE = 'start_failure'
OUTCOME_ERROR = 'error'
OUTCOME_EXPLICIT_STOP = 'explicit_stop'
OUTCOME_SHUTDOWN = 'shutdown'


class SceneRuntimeService:
    """Own scene thread creation and scene execution flow."""

    def __init__(self, owner, logger) -> None:
        self.owner = owner
        self.log = logger

    def initiate_scene_start(self, scene_filename, log_message):
        """Common entry point for starting a scene."""
        owner = self.owner

        if not owner.mqtt_client or not owner.mqtt_client.is_connected():
            self.log.warning(
                "Starting scene without MQTT connection - external devices may not respond"
            )

        if not owner._set_scene_running(
            True,
            f"start:{scene_filename}",
            expect_current=False,
        ):
            self.log.info(
                f"Scene already running, ignoring request to start: {scene_filename}"
            )
            return False

        owner.current_scene_name = scene_filename
        owner.current_scene_state = None
        self.log.info(log_message)

        owner._dashboard_notifier_service().broadcast_status()

        owner.scene_thread = threading.Thread(
            target=owner._run_scene_logic,
            args=(scene_filename,),
            name=f"{owner.room_id}-scene-runner",
            daemon=True,
        )
        owner.scene_thread.start()
        return True

    def run_scene_logic(self, scene_filename):
        """Worker thread function containing the core scene flow."""
        return self._run_scene_once(scene_filename)

    def _run_scene_once(self, scene_filename):
        """Run one scene lifecycle and return its completion outcome."""
        owner = self.owner
        scene_path = owner.build_scene_path(scene_filename)

        try:
            self.log.debug(f"Attempting to load scene from: {scene_path}")

            if not owner._scene_file_exists(scene_path):
                self.log.critical(f"Scene file not found: {scene_path}")
                owner._set_scene_running(False, f"missing_scene_file:{scene_filename}")
                self._clear_current_scene_and_status()
                return OUTCOME_MISSING_SCENE

            if not owner.scene_parser:
                self.log.error("Scene parser not available")
                owner._set_scene_running(False, "scene_parser_unavailable")
                self._clear_current_scene_and_status()
                return OUTCOME_PARSER_UNAVAILABLE

            self.log.debug(f"Loading scene: {scene_path}")
            if owner.scene_parser.load_scene(scene_path):
                self._wire_scene_progress_callback()

                if not owner.scene_running or owner.shutdown_requested:
                    self.log.info("Scene start cancelled before execution.")
                    self._clear_current_scene_and_status()
                    return self._cancelled_start_outcome()

                outcome = OUTCOME_ERROR
                try:
                    outcome = owner.run_scene()
                    if not outcome:
                        outcome = self._infer_scene_outcome()
                except Exception as exc:
                    self.log.error(f"An error occurred during scene execution: {exc}")
                    outcome = OUTCOME_ERROR
                finally:
                    self._cleanup_after_scene_thread(scene_filename)
                return outcome
            else:
                self.log.error(f"Failed to load scene: {scene_filename}")
                owner._set_scene_running(False, f"scene_load_failed:{scene_filename}")
                self._clear_current_scene_and_status()
                return OUTCOME_LOAD_FAILURE

        except Exception as exc:
            self.log.error(f"Critical error in scene thread: {exc}")
            owner._set_scene_running(False, f"scene_thread_exception:{scene_filename}")
            self._clear_current_scene_and_status()
            return OUTCOME_ERROR

    def run_scene(self):
        """Execute the loaded state machine scene."""
        owner = self.owner

        if not owner.scene_parser.scene_data:
            self.log.error("No scene data available")
            owner._set_scene_running(False, "missing_scene_data")
            return OUTCOME_LOAD_FAILURE

        stats_scene_name = owner.current_scene_name
        self.log.debug("Starting state machine scene execution")

        feedback_tracker = getattr(owner.mqtt_client, 'feedback_tracker', None) if owner.mqtt_client else None
        if feedback_tracker:
            feedback_tracker.enable_feedback_tracking()

        if not owner.scene_parser.start_scene():
            self.log.error("Failed to start scene state machine")
            if feedback_tracker:
                feedback_tracker.disable_feedback_tracking()
            return OUTCOME_START_FAILURE

        outcome = OUTCOME_NORMAL_END
        while not owner.shutdown_requested:
            if not owner.scene_running:
                self.log.debug("Scene execution was stopped externally.")
                outcome = OUTCOME_EXPLICIT_STOP
                break

            scene_continues = owner.scene_parser.process_scene()

            if not scene_continues:
                outcome = self._infer_scene_outcome(default=OUTCOME_NORMAL_END)
                break

            time.sleep(owner.scene_processing_sleep)
        else:
            outcome = OUTCOME_SHUTDOWN

        self.log.debug("Scene execution finished")

        if feedback_tracker:
            feedback_tracker.disable_feedback_tracking()

        if owner.video_handler:
            owner.video_handler.stop_video()

        owner._update_scene_statistics(stats_scene_name)
        return outcome

    def _wire_scene_progress_callback(self) -> None:
        owner = self.owner
        if not owner.web_dashboard:
            return
        if hasattr(owner.scene_parser, 'state_machine'):
            owner.scene_parser.state_machine.on_state_change = (
                owner._dashboard_notifier_service().broadcast_scene_progress
            )

    def _clear_current_scene_and_status(self) -> None:
        self.owner.current_scene_name = None
        self.owner.current_scene_state = None
        self.owner._dashboard_notifier_service().broadcast_status()

    def _cleanup_after_scene_thread(self, scene_filename) -> None:
        owner = self.owner
        stop_coordinator = owner._stop_coordinator_service()
        stop_coordinator.stop_audio_for_scene_finally()
        if owner.video_handler:
            owner.video_handler.stop_video()

        transitioned = owner._set_scene_running(
            False,
            f"scene_thread_finally:{scene_filename}",
        )
        if transitioned:
            stop_coordinator.force_actuators_off(source='scene_end')
            owner.broadcast_stop()

        self._clear_current_scene_and_status()

    def _cancelled_start_outcome(self):
        if self.owner.shutdown_requested:
            return OUTCOME_SHUTDOWN
        return OUTCOME_EXPLICIT_STOP

    def _infer_scene_outcome(self, default=OUTCOME_NORMAL_END):
        owner = self.owner
        if owner.shutdown_requested:
            return OUTCOME_SHUTDOWN
        if not owner.scene_running:
            return OUTCOME_EXPLICIT_STOP
        return default
