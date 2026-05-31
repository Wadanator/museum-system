"""Scene start/run orchestration extracted from MuseumController."""

import threading
import time


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
        owner = self.owner
        scene_path = owner.build_scene_path(scene_filename)

        try:
            self.log.debug(f"Attempting to load scene from: {scene_path}")

            if not owner._scene_file_exists(scene_path):
                self.log.critical(f"Scene file not found: {scene_path}")
                owner._set_scene_running(False, f"missing_scene_file:{scene_filename}")
                self._clear_current_scene_and_status()
                return

            if not owner.scene_parser:
                self.log.error("Scene parser not available")
                owner._set_scene_running(False, "scene_parser_unavailable")
                self._clear_current_scene_and_status()
                return

            self.log.debug(f"Loading scene: {scene_path}")
            if owner.scene_parser.load_scene(scene_path):
                self._wire_scene_progress_callback()

                if not owner.scene_running or owner.shutdown_requested:
                    self.log.info("Scene start cancelled before execution.")
                    self._clear_current_scene_and_status()
                    return

                try:
                    owner.run_scene()
                except Exception as exc:
                    self.log.error(f"An error occurred during scene execution: {exc}")
                finally:
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
            else:
                self.log.error(f"Failed to load scene: {scene_filename}")
                owner._set_scene_running(False, f"scene_load_failed:{scene_filename}")
                self._clear_current_scene_and_status()

        except Exception as exc:
            self.log.error(f"Critical error in scene thread: {exc}")
            owner._set_scene_running(False, f"scene_thread_exception:{scene_filename}")
            self._clear_current_scene_and_status()

    def run_scene(self):
        """Execute the loaded state machine scene."""
        owner = self.owner

        if not owner.scene_parser.scene_data:
            self.log.error("No scene data available")
            owner._set_scene_running(False, "missing_scene_data")
            return

        stats_scene_name = owner.current_scene_name
        self.log.debug("Starting state machine scene execution")

        feedback_tracker = getattr(owner.mqtt_client, 'feedback_tracker', None) if owner.mqtt_client else None
        if feedback_tracker:
            feedback_tracker.enable_feedback_tracking()

        if not owner.scene_parser.start_scene():
            self.log.error("Failed to start scene state machine")
            if feedback_tracker:
                feedback_tracker.disable_feedback_tracking()
            return

        while not owner.shutdown_requested:
            if not owner.scene_running:
                self.log.debug("Scene execution was stopped externally.")
                break

            scene_continues = owner.scene_parser.process_scene()

            if not scene_continues:
                break

            time.sleep(owner.scene_processing_sleep)

        self.log.debug("Scene execution finished")

        if feedback_tracker:
            feedback_tracker.disable_feedback_tracking()

        if owner.video_handler:
            owner.video_handler.stop_video()

        owner._update_scene_statistics(stats_scene_name)

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
