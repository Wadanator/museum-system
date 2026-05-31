"""Small dashboard notification facade used by runtime services."""


class DashboardNotifier:
    """Wrap dashboard/socket calls so scene runtime code stays UI-agnostic."""

    def __init__(self, owner, logger) -> None:
        self.owner = owner
        self.log = logger

    def broadcast_status(self) -> None:
        dashboard = getattr(self.owner, 'web_dashboard', None)
        if dashboard:
            dashboard.broadcast_status()

    def broadcast_scene_progress(self, state_name: str) -> None:
        owner = self.owner
        dashboard = getattr(owner, 'web_dashboard', None)
        owner.current_scene_state = state_name

        if not dashboard:
            return

        try:
            dashboard._broadcast_event(
                'scene_progress',
                {
                    'activeState': state_name,
                    'sceneName': owner.current_scene_name,
                },
            )
        except Exception as exc:
            self.log.error(f"Failed to emit socket event: {exc}")

    def broadcast_stats(self) -> None:
        dashboard = getattr(self.owner, 'web_dashboard', None)
        if dashboard:
            dashboard.broadcast_stats()

    def broadcast_device_runtime_state(self, snapshot: dict) -> None:
        dashboard = getattr(self.owner, 'web_dashboard', None)
        if dashboard:
            dashboard.broadcast_device_runtime_state(snapshot)

    def update_scene_statistics(self, scene_name=None) -> None:
        dashboard = getattr(self.owner, 'web_dashboard', None)
        if not dashboard:
            return

        try:
            name = scene_name or self.owner.current_scene_name
            if name:
                dashboard.update_scene_stats(name)
            else:
                self.log.warning("Cannot update scene stats: Unknown scene name")
                dashboard.stats['total_scenes_played'] += 1
                dashboard.save_stats()
            dashboard.socketio.emit(
                'stats_update',
                dashboard.stats,
                namespace='/'
            )
        except Exception as exc:
            self.log.error(f"Error updating stats: {exc}")
