"""Scene lifecycle state and watchdog heartbeat handling."""

import threading
from pathlib import Path


class SceneLifecycle:
    """Own scene_running transitions and the watchdog state-file heartbeat."""

    def __init__(self, owner, state_file: Path, logger) -> None:
        self.owner = owner
        self.state_file = state_file
        self.log = logger

    def _current_state_file(self):
        provider = getattr(self.owner, '_scene_state_file', None)
        if callable(provider):
            return provider()
        return self.state_file

    def set_scene_running(self, is_running, reason, expect_current=None):
        """Centralized scene lifecycle transition with synchronized file updates."""
        state_value = 'running' if is_running else 'idle'
        owner = self.owner

        with owner.scene_lock:
            if expect_current is not None and owner.scene_running != expect_current:
                return False

            if owner.scene_running == is_running:
                return False

            owner.scene_running = is_running
            try:
                self._current_state_file().write_text(state_value)
            except OSError as exc:
                self.log.error(f"Failed to persist scene state '{state_value}': {exc}")

        if is_running:
            self.start_heartbeat()
        else:
            self.stop_heartbeat()

        self.log.info(f"Scene lifecycle transition -> {state_value} ({reason})")
        return True

    def heartbeat_loop(self) -> None:
        """Keep the watchdog scene state file fresh during long scenes."""
        owner = self.owner
        interval = float(owner.scene_heartbeat_interval)

        while not owner._heartbeat_stop_event.wait(interval):
            with owner.scene_lock:
                if owner._heartbeat_stop_event.is_set() or not owner.scene_running:
                    break
                try:
                    self._current_state_file().write_text('running')
                except OSError as exc:
                    self.log.warning(f"Scene heartbeat failed to update state file: {exc}")

    def start_heartbeat(self) -> None:
        """Start the heartbeat thread if it is not already running."""
        owner = self.owner
        thread = owner._heartbeat_thread
        if thread and thread.is_alive():
            return

        owner._heartbeat_stop_event.clear()
        owner._heartbeat_thread = threading.Thread(
            target=self.heartbeat_loop,
            name='scene-heartbeat',
            daemon=True,
        )
        owner._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        """Signal the heartbeat thread to stop and wait for it to exit."""
        owner = self.owner
        owner._heartbeat_stop_event.set()
        thread = owner._heartbeat_thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        owner._heartbeat_thread = None
