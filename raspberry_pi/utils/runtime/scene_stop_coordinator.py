"""Coordinated scene/runtime stop operations."""

from utils.display_policy import (
    DISPLAY_SCENE_REQUIRED_REASON,
    DISPLAY_SCENE_VIDEO_REASON,
)


class SceneStopCoordinator:
    """Keep shutdown ordering for scene, media, actuators, and MQTT STOP."""

    def __init__(self, owner, logger) -> None:
        self.owner = owner
        self.log = logger

    def stop_scene(self):
        """Stop the running scene and shut down all local/external devices."""
        owner = self.owner
        self.log.info(f"Initiating GLOBAL STOP for {owner.room_id}")

        transitioned = owner._set_scene_running(
            False,
            "external_stop",
            expect_current=True,
        )
        if not transitioned:
            self.release_display_reasons()
            self.force_actuators_off('external_stop_idle')
            owner.broadcast_stop()
            self.clear_current_scene()
            owner._dashboard_notifier_service().broadcast_status()
            return True

        self.stop_scene_parser()
        self.stop_audio()
        self.stop_video()
        self.release_display_reasons()
        self.force_actuators_off('external_stop')
        owner.broadcast_stop()
        self.clear_current_scene()
        owner._dashboard_notifier_service().broadcast_status()
        return True

    def stop_scene_parser(self) -> None:
        scene_parser = getattr(self.owner, 'scene_parser', None)
        if scene_parser:
            try:
                scene_parser.stop_scene()
            except Exception as exc:
                self.log.error(f"Error stopping parser: {exc}")

    def stop_audio(self) -> None:
        audio_handler = getattr(self.owner, 'audio_handler', None)
        if audio_handler:
            try:
                audio_handler.stop_audio()
            except Exception as exc:
                self.log.error(f"Error stopping audio: {exc}")

    def stop_audio_for_scene_finally(self) -> None:
        audio_handler = getattr(self.owner, 'audio_handler', None)
        if audio_handler:
            try:
                audio_handler.stop_audio()
            except Exception as exc:
                self.log.error(f"Error stopping audio in scene finally: {exc}")

    def stop_video(self) -> None:
        video_handler = getattr(self.owner, 'video_handler', None)
        if video_handler:
            try:
                video_handler.stop_video()
            except Exception as exc:
                self.log.error(f"Error stopping video: {exc}")

    def stop_idle_runtime(self) -> None:
        """Stop local media/devices during controller cleanup when no scene runs."""
        self.stop_audio()
        self.stop_video()
        self.release_display_reasons()
        self.force_actuators_off('service_cleanup')
        self.owner.broadcast_stop()

    def release_display_reasons(self) -> None:
        """Release scene-owned display power reasons."""
        display_power = getattr(self.owner, 'display_power_manager', None)
        if not display_power:
            return

        for reason in (DISPLAY_SCENE_VIDEO_REASON, DISPLAY_SCENE_REQUIRED_REASON):
            try:
                display_power.release(reason)
            except Exception as exc:
                self.log.error(f"Error releasing display reason {reason}: {exc}")

    def force_actuators_off(self, source: str) -> int:
        store = getattr(self.owner, 'actuator_state_store', None)
        if not store:
            return 0
        return store.force_all_off(source=source)

    def broadcast_stop(self) -> None:
        """Publish a STOP command to all MQTT devices in the room."""
        owner = self.owner
        mqtt_client = getattr(owner, 'mqtt_client', None)
        if mqtt_client and mqtt_client.is_connected():
            stop_topic = f"{owner.room_id}/STOP"
            self.log.debug(f"Broadcasting STOP signal to MQTT: {stop_topic}")
            try:
                mqtt_client.publish(stop_topic, "STOP")
            except Exception as exc:
                self.log.error(f"Failed to publish stop message: {exc}")

    def clear_current_scene(self) -> None:
        self.owner.current_scene_name = None
        self.owner.current_scene_state = None
