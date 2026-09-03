#!/usr/bin/env python3

import os
import sys
import signal
import time
import threading
import logging
import json
from pathlib import Path

# Configure Python path for module imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.bootstrap import setup_bootstrap_logging, log_bootstrap_exception
from utils.device_outage_tracker import DeviceOutageTracker

log = logging.getLogger('museum.bootstrap')
config_manager = None
setup_logging_from_config = None
get_logger = None
ServiceContainer = None
SceneParser = None
start_web_dashboard = None
DashboardNotifier = None
AmbientLoopService = None
SceneLifecycle = None
SceneRuntimeService = None
SceneStopCoordinator = None
SystemActions = None

# State file read by watchdog.py before deciding to restart the service.
# Written 'running' when a scene starts, 'idle' when it ends.
_SCENE_STATE_FILE = Path('/tmp/museum_scene_state')


def _initialize_runtime():
    """Load runtime modules and switch from bootstrap logging to configured logging."""
    global config_manager, setup_logging_from_config, get_logger
    global ServiceContainer, SceneParser, start_web_dashboard, log
    global DashboardNotifier, AmbientLoopService, SceneLifecycle, SceneRuntimeService
    global SceneStopCoordinator, SystemActions

    from utils.config_manager import ConfigManager
    from utils.logging_setup import setup_logging_from_config as setup_logging_from_config_impl, get_logger as get_logger_impl
    from utils.service_container import ServiceContainer as service_container_cls
    from utils.scene_parser import SceneParser as scene_parser_cls
    from Web import start_web_dashboard as start_web_dashboard_func
    from utils.runtime import (
        AmbientLoopService as ambient_loop_service_cls,
        DashboardNotifier as dashboard_notifier_cls,
        SceneLifecycle as scene_lifecycle_cls,
        SceneRuntimeService as scene_runtime_service_cls,
        SceneStopCoordinator as scene_stop_coordinator_cls,
        SystemActions as system_actions_cls,
    )

    config_manager = ConfigManager()
    setup_logging_from_config = setup_logging_from_config_impl
    get_logger = get_logger_impl
    ServiceContainer = service_container_cls
    SceneParser = scene_parser_cls
    start_web_dashboard = start_web_dashboard_func
    AmbientLoopService = ambient_loop_service_cls
    DashboardNotifier = dashboard_notifier_cls
    SceneLifecycle = scene_lifecycle_cls
    SceneRuntimeService = scene_runtime_service_cls
    SceneStopCoordinator = scene_stop_coordinator_cls
    SystemActions = system_actions_cls

    logging_config = config_manager.get_logging_config()
    setup_logging_from_config(logging_config)
    log = get_logger('main')

class MuseumController:
    """Main controller for the museum system, managing all components and operations."""
    
    def __init__(self, config_manager):
        """Initialize the Museum Controller with all necessary components."""
        self.config_manager = config_manager
        self.config = config_manager.get_all_config()
        self.shutdown_requested = False
        self._cleaned_up = False
        
        self.start_time = time.monotonic()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Room configuration
        self.room_id = self.config['room_id']
        self.json_file_name = self.config['json_file_name']
        self.scenes_dir = self.config['scenes_dir']
        
        # System settings
        self.main_loop_sleep = self.config['main_loop_sleep']
        self.scene_processing_sleep = self.config['scene_processing_sleep']
        self.web_dashboard_port = self.config['web_dashboard_port']
        
        # Scene execution state
        self.scene_running = False
        self.current_scene_name = None
        self.current_scene_state = None
        self.scene_lock = threading.Lock()
        self.scene_thread = None
        self.scene_shutdown_join_timeout = max(
            2.0, float(self.config.get('scene_buffer_time', 1.0))
        )

        # Scene heartbeat — keeps /tmp/museum_scene_state fresh during long scenes
        self.scene_heartbeat_interval: float = max(1.0, self.config['scene_heartbeat_interval'])
        self._heartbeat_stop_event: threading.Event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

        # Runtime helpers keep the public MuseumController API stable while
        # moving scene lifecycle/stop/system responsibilities out of main.py.
        self.ambient_loop = AmbientLoopService(self, log)
        self.dashboard_notifier = DashboardNotifier(self, log)
        self.scene_lifecycle = SceneLifecycle(self, _SCENE_STATE_FILE, log)
        self.stop_coordinator = SceneStopCoordinator(self, log)
        self.system_actions = SystemActions(self, log)
        self.scene_runtime = SceneRuntimeService(self, log)
        
        log.debug(f"Initializing Museum Controller for {self.room_id}")
        
        self.services = ServiceContainer(self.config, self.room_id, log)
        self.services.init_all_services()

        from utils.mqtt.mqtt_actuator_state_store import MQTTActuatorStateStore
        self.actuator_state_store = MQTTActuatorStateStore()
        self._bootstrap_actuator_state_store()
        
        # Device outage tracker for ESP device statistics
        self.outage_tracker = DeviceOutageTracker()
        
        # Extract service references for direct access throughout the controller
        self.audio_handler = self.services.audio_handler
        self.video_handler = self.services.video_handler
        self.mqtt_client = self.services.mqtt_client
        self.mqtt_message_handler = self.services.mqtt_message_handler
        self.mqtt_device_registry = self.services.mqtt_device_registry
        self.mqtt_feedback_tracker = self.services.mqtt_feedback_tracker
        self.system_monitor = self.services.system_monitor
        self.button_handler = self.services.button_handler
        self.display_power_manager = self.services.display_power_manager

        self._wire_dependencies()
        
        # Web Dashboard
        self.web_dashboard = None
        start_web_dashboard_func = globals().get('start_web_dashboard')
        if start_web_dashboard_func:
            try:
                self.web_dashboard = start_web_dashboard_func(self, port=self.web_dashboard_port)
            except Exception as e:
                log.warning(f"Web dashboard failed to start: {e}")

    def _wire_dependencies(self):
        """Wire callbacks and dependencies between services and the controller."""
        
        # 1. MQTT Callbacks
        if self.mqtt_message_handler:
            self.mqtt_message_handler.set_handlers(
                device_registry=self.mqtt_device_registry,
                feedback_tracker=self.mqtt_feedback_tracker,
                actuator_state_store=self.actuator_state_store,
                button_callback=self.on_button_press,
                named_scene_callback=self.start_scene_by_name,
                display_power_manager=self.display_power_manager,
            )

        # Actuator state store - wire feedback tracker and WebSocket broadcast
        if self.mqtt_feedback_tracker and self.actuator_state_store:
            self.mqtt_feedback_tracker.set_state_store(self.actuator_state_store)

        def _on_actuator_state_change(snapshot: dict) -> None:
            self._dashboard_notifier_service().broadcast_device_runtime_state(snapshot)

        self.actuator_state_store.set_update_callback(_on_actuator_state_change)

        if self.mqtt_device_registry:
            self.mqtt_device_registry.on_status_change = self._on_device_status_change
        
        # 2. MQTT Connection callbacks
        if self.mqtt_client:
            self.mqtt_client.connection_lost_callback = self._on_mqtt_connection_lost
            self.mqtt_client.connection_restored_callback = self._on_mqtt_connection_restored
            
        # 3. Scene Parser
        self.scene_parser = SceneParser(
            mqtt_client=self.mqtt_client,
            audio_handler=self.audio_handler,
            video_handler=self.video_handler,
            display_power_manager=self.display_power_manager,
        )
        
        # Connect scene parser to MQTT message handler so incoming messages
        # can trigger mqttMessage transitions in the running state machine
        if self.mqtt_message_handler:
            self.mqtt_message_handler.scene_parser = self.scene_parser
            log.debug("Scene parser connected to MQTT message handler for transitions")
            
        # 4. Button Handler Callback
        if self.button_handler:
            self.button_handler.set_callback(self.on_button_press)

    def _dashboard_notifier_service(self):
        """Return the dashboard notifier, lazily creating it for lightweight tests."""
        service = getattr(self, 'dashboard_notifier', None)
        if service is None:
            cls = globals().get('DashboardNotifier')
            if cls is None:
                from utils.runtime.dashboard_notifier import DashboardNotifier as cls
            service = cls(self, log)
            self.dashboard_notifier = service
        return service

    def _ambient_loop_service(self):
        """Return the ambient policy helper, lazily creating it for tests."""
        service = getattr(self, 'ambient_loop', None)
        if service is None:
            cls = globals().get('AmbientLoopService')
            if cls is None:
                from utils.runtime.ambient_loop_service import AmbientLoopService as cls
            service = cls(self, log)
            self.ambient_loop = service
        return service

    def _scene_lifecycle_service(self):
        """Return the scene lifecycle helper, lazily creating it for tests."""
        service = getattr(self, 'scene_lifecycle', None)
        if service is None:
            cls = globals().get('SceneLifecycle')
            if cls is None:
                from utils.runtime.scene_lifecycle import SceneLifecycle as cls
            service = cls(self, _SCENE_STATE_FILE, log)
            self.scene_lifecycle = service
        return service

    def _scene_state_file(self):
        """Return the current watchdog scene-state file path."""
        return _SCENE_STATE_FILE

    def _scene_runtime_service(self):
        """Return the scene runtime service, lazily creating it for tests."""
        service = getattr(self, 'scene_runtime', None)
        if service is None:
            cls = globals().get('SceneRuntimeService')
            if cls is None:
                from utils.runtime.scene_runtime_service import SceneRuntimeService as cls
            service = cls(self, log)
            self.scene_runtime = service
        return service

    def _stop_coordinator_service(self):
        """Return the stop coordinator, lazily creating it for tests."""
        service = getattr(self, 'stop_coordinator', None)
        if service is None:
            cls = globals().get('SceneStopCoordinator')
            if cls is None:
                from utils.runtime.scene_stop_coordinator import SceneStopCoordinator as cls
            service = cls(self, log)
            self.stop_coordinator = service
        return service

    def _system_actions_service(self):
        """Return system action helper, lazily creating it for tests."""
        service = getattr(self, 'system_actions', None)
        if service is None:
            cls = globals().get('SystemActions')
            if cls is None:
                from utils.runtime.system_actions import SystemActions as cls
            service = cls(self, log)
            self.system_actions = service
        return service

    def _bootstrap_actuator_state_store(self):
        """Initialize actuator runtime state entries from the room devices config."""
        store = getattr(self, 'actuator_state_store', None)
        if not store:
            return

        primary_path = Path(self.config.get('devices_config_path', ''))
        candidate_paths = [primary_path] if primary_path else []
        legacy_path = Path(self.scenes_dir) / self.room_id / 'devices.json'
        if legacy_path not in candidate_paths:
            candidate_paths.append(legacy_path)

        for path in candidate_paths:
            if not path or not path.exists():
                continue
            try:
                with path.open('r', encoding='utf-8') as file_obj:
                    devices_config = json.load(file_obj)
                count = store.initialize_from_devices_config(devices_config)
                log.debug(
                    "Actuator state store bootstrapped from %s (%d topics)",
                    path,
                    count,
                )
                return
            except Exception as exc:
                log.error(f"Failed to bootstrap actuator state store from {path}: {exc}")
                return

        log.warning("No devices.json found for actuator state bootstrap")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        log.warning(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_requested = True
        if self.mqtt_client:
            self.mqtt_client.shutdown_requested = True
        self._request_ambient_shutdown()

    def _request_ambient_shutdown(self):
        """Wake ambient restart waits when the controller is shutting down."""
        try:
            self._ambient_loop_service().request_shutdown()
        except Exception as exc:
            log.error(f"Failed to notify ambient shutdown: {exc}")

    def _apply_ambient_operator_stop_policy(self):
        """Suspend ambient auto-restart when Stop is an operator safety action."""
        try:
            ambient = self._ambient_loop_service()
            if self.shutdown_requested or self._cleaned_up:
                ambient.request_shutdown()
                return
            if ambient.should_suspend_on_operator_stop():
                ambient.suspend_by_operator_stop()
        except Exception as exc:
            log.error(f"Failed to apply ambient stop policy: {exc}")

    def _on_device_status_change(self, device_id: str, status: str) -> None:
        """Handle MQTT device online/offline transitions."""
        # Track outages (short disconnections) to JSON
        outage_tracker = getattr(self, 'outage_tracker', None)
        if outage_tracker:
            outage_tracker.on_device_status_change(device_id, status)
        
        if self.actuator_state_store:
            if status == 'offline':
                self.actuator_state_store.mark_node_offline(device_id)
            elif status == 'online':
                self.actuator_state_store.mark_node_online(device_id)

        if self.web_dashboard:
            try:
                self.web_dashboard.broadcast_stats()
            except Exception as exc:
                log.error(f"Failed to broadcast stats after device status change: {exc}")

    def _set_scene_running(self, is_running, reason, expect_current=None):
        """Centralized scene lifecycle transition with synchronized file/state updates."""
        return self._scene_lifecycle_service().set_scene_running(
            is_running,
            reason,
            expect_current=expect_current,
        )

    def _heartbeat_loop(self) -> None:
        """Periodically rewrite the scene state file to 'running' so the watchdog
        does not mistake a long-running scene for a hung service."""
        self._scene_lifecycle_service().heartbeat_loop()

    def _start_heartbeat(self) -> None:
        """Start the heartbeat thread if it is not already running."""
        self._scene_lifecycle_service().start_heartbeat()

    def _stop_heartbeat(self) -> None:
        """Signal the heartbeat thread to stop and wait for it to exit."""
        self._scene_lifecycle_service().stop_heartbeat()

    def _on_mqtt_connection_lost(self):
        if self.shutdown_requested or self._cleaned_up:
            log.debug("MQTT connection closed during planned shutdown")
        else:
            log.warning("MQTT connection lost - system will continue with limited functionality")

    def _on_mqtt_connection_restored(self):
        if self.system_monitor:
            self.system_monitor.send_ready_notification()
        log.info(f"System ready - {self.room_id} operational")
        self._ambient_loop_service().start_after_mqtt_restore_if_needed()

    def on_button_press(self):
        """Handle button press to start default scene."""
        if self._ambient_loop_service().should_ignore_default_start():
            log.info("Ignoring default scene start in ambient mode")
            return False
        return self._initiate_scene_start(
            self.json_file_name,
            "Button pressed - starting default scene",
        )

    def start_default_scene(self):
        """Public method to start default scene."""
        if self._ambient_loop_service().should_ignore_default_start():
            log.info("Ignoring default scene start in ambient mode")
            return False
        return self._initiate_scene_start(self.json_file_name, "Starting default scene")

    def start_scene_by_name(self, scene_file_name):
        """Public method to start a specific scene by file name."""
        if not self._ambient_loop_service().should_allow_named_scene_start():
            log.info(
                f"Named scene start rejected by ambient policy: {scene_file_name}"
            )
            return False
        return self._initiate_scene_start(
            scene_file_name,
            f"Starting named scene: {scene_file_name}",
        )

    def resume_ambient_scene(self):
        """Resume ambient mode after an operator stop from the dashboard."""
        ambient = self._ambient_loop_service()
        if not ambient.is_enabled():
            log.info("Ambient resume requested while ambient mode is disabled")
            return False

        if self.scene_running:
            ambient.resume()
            log.info("Ambient resume requested while a scene is already running")
            return True

        return ambient.resume_from_operator()

    def _start_ambient_after_initial_connection(self):
        """Apply ambient boot policy after the initial MQTT connection attempt."""
        return self._ambient_loop_service().start_after_boot_if_needed()

    def _initiate_scene_start(self, scene_filename, log_message):
        """Common entry point for starting a scene."""
        return self._scene_runtime_service().initiate_scene_start(
            scene_filename,
            log_message,
        )

    def build_scene_path(self, scene_filename):
        """Build the absolute path to a scene file for the current room."""
        return os.path.join(self.scenes_dir, self.room_id, scene_filename)

    def _scene_file_exists(self, scene_path):
        """Compatibility wrapper so tests can patch main.os.path.exists."""
        return os.path.exists(scene_path)

    def _run_scene_logic(self, scene_filename):
        """Worker thread function containing the core logic to load and run a scene."""
        return self._scene_runtime_service().run_scene_logic(scene_filename)

    def stop_scene(self):
        """Stop the running scene and shut down all local and external devices."""
        self._apply_ambient_operator_stop_policy()
        return self._stop_coordinator_service().stop_scene()

    def broadcast_stop(self):
        """Publish a STOP command to all MQTT devices in the room."""
        self._stop_coordinator_service().broadcast_stop()

    def run_scene(self):
        """Execute the loaded state machine scene."""
        return self._scene_runtime_service().run_scene()

    def _update_scene_statistics(self, scene_name=None):
        """Update scene play statistics for the web dashboard."""
        self._dashboard_notifier_service().update_scene_statistics(scene_name)

    def system_restart(self):
        """Reboot the Raspberry Pi (triggered from the web dashboard)."""
        self._system_actions_service().system_restart()

    def system_shutdown(self):
        """Power off the Raspberry Pi (triggered from the web dashboard)."""
        self._system_actions_service().system_shutdown()

    def service_restart(self):
        """Exit the process so systemd can restart the museum service."""
        self._system_actions_service().service_restart()

    def run(self):
        """Run the main application loop."""
        log.debug("Starting Museum Controller")
        
        # Check MQTT Connection
        if self.mqtt_client:
            if not self.mqtt_client.establish_initial_connection():
                if self.shutdown_requested:
                    return
                log.warning("NETWORK ERROR: System starting in OFFLINE MODE. Will retry connection in background.")

        if not self.shutdown_requested:
            self._start_ambient_after_initial_connection()
        
        last_device_cleanup = time.time()
        device_cleanup_interval = self.config['device_cleanup_interval']
        
        use_polling = (hasattr(self.button_handler, 'use_polling') and 
                    self.button_handler.use_polling if self.button_handler else False)
        
        try:
            while not self.shutdown_requested:      
                current_time = time.time()
                
                if self.system_monitor:
                    self.system_monitor.perform_periodic_health_check(self.mqtt_client)

                if use_polling and self.button_handler:
                    self.button_handler.check_button_polling()
                
                if current_time - last_device_cleanup >= device_cleanup_interval:
                    if self.mqtt_device_registry:
                        self.mqtt_device_registry.cleanup_stale_devices()
                    last_device_cleanup = current_time
                
                sleep_time = self.main_loop_sleep if self.scene_running else 0.1
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            log.debug("Received keyboard interrupt")
        except Exception as e:
            log.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up all system resources gracefully."""
        if self._cleaned_up:
            return

        log.debug("Initiating cleanup...")
        self._cleaned_up = True
        self._request_ambient_shutdown()

        try:
            if self.scene_running:
                log.debug("Active scene detected during cleanup; stopping it first.")
                self.stop_scene()
            else:
                self._stop_coordinator_service().stop_idle_runtime()
        except Exception as e:
            log.error(f"Safe runtime stop during cleanup failed: {e}")

        scene_thread = self.scene_thread
        if (
            scene_thread
            and scene_thread.is_alive()
            and scene_thread is not threading.current_thread()
        ):
            scene_thread.join(timeout=self.scene_shutdown_join_timeout)
            if scene_thread.is_alive():
                log.warning("Scene thread did not finish before cleanup timeout")

        if self.web_dashboard:
            try:
                self.web_dashboard.update_stats()
                self.web_dashboard.save_stats()
                log.debug("Dashboard stats saved.")
            except Exception as e:
                log.error(f"Failed to save stats during cleanup: {e}")

        if self.services:
            self.services.cleanup()
            
        if self.scene_parser:
             self.scene_parser.cleanup()

        log.debug("Museum Controller stopped cleanly")

def main():
    setup_bootstrap_logging()

    controller = None
    try:
        _initialize_runtime()
        controller = MuseumController(config_manager)
        controller.run()
    except Exception as e:
        if get_logger:
            log.error(f"Critical application error: {e}")
        else:
            log_bootstrap_exception(e)
        sys.exit(1)
    finally:
        if controller:
            controller.cleanup()

if __name__ == "__main__":
    main()
