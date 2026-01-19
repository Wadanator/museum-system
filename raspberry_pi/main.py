#!/usr/bin/env python3

import os
import sys
import signal
import time
import threading
import subprocess

# Configure Python path for module imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.config_manager import ConfigManager
from utils.logging_setup import setup_logging_from_config, get_logger

# Initialize configuration and logging
config_manager = ConfigManager()
logging_config = config_manager.get_logging_config()
log = setup_logging_from_config(logging_config)
log = get_logger('main')

# Import core system modules
try:
    from utils.mqtt.mqtt_client import MQTTClient
    from utils.mqtt.mqtt_message_handler import MQTTMessageHandler
    from utils.mqtt.mqtt_feedback_tracker import MQTTFeedbackTracker
    from utils.mqtt.mqtt_device_registry import MQTTDeviceRegistry
    from utils.scene_parser import SceneParser
    from utils.audio_handler import AudioHandler
    from utils.video_handler import VideoHandler
    from utils.system_monitor import SystemMonitor
    from utils.button_handler import ButtonHandler
    from Web import start_web_dashboard
    log.debug("Core modules imported successfully")
except ImportError as e:
    log.critical(f"Failed to import core modules: {e}")
    sys.exit(1)

class MuseumController:
    """Main controller for the museum system, managing all components and operations."""
    
    def __init__(self, config_manager):
        """Initialize the Museum Controller with all necessary components."""
        self.config_manager = config_manager
        self.config = config_manager.get_all_config()
        self.shutdown_requested = False
        self._cleaned_up = False
        
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
        self.current_scene_name = None  # Track current scene name for stats
        self.scene_lock = threading.Lock()
        
        # Initialize components
        log.info(f"Initializing Museum Controller for {self.room_id}")
        self._initialize_components()

    def _initialize_components(self):
        """Initialize all system components in the correct order."""
        # Audio Handler
        try:
            self.audio_handler = AudioHandler(
                self.config['audio_dir'],
                max_init_attempts=self.config.get('audio_max_init_attempts', 3),
                init_retry_delay=self.config.get('audio_init_retry_delay', 5)
            )
        except Exception as e:
            log.warning(f"Audio handler initialization failed: {e}")
            self.audio_handler = None
        
        # Video Handler
        try:
            self.video_handler = VideoHandler(
                video_dir=self.config['video_dir'],
                ipc_socket=self.config['ipc_socket'],
                iddle_image=self.config['iddle_image'],
                health_check_interval=self.config['video_health_check_interval'],
                max_restart_attempts=self.config['video_max_restart_attempts'],
                restart_cooldown=self.config['video_restart_cooldown']
            )
        except Exception as e:
            log.warning(f"Video handler initialization failed: {e}")
            self.video_handler = None
        
        # MQTT Components
        self.mqtt_device_registry = MQTTDeviceRegistry(
            device_timeout=int(self.config.get('device_timeout', 180))
        )
        
        self.mqtt_feedback_tracker = MQTTFeedbackTracker(
            feedback_timeout=float(self.config.get('feedback_timeout', 2))
        )
        
        # Create message handler
        self.mqtt_message_handler = MQTTMessageHandler()
        self.mqtt_message_handler.set_handlers(
            device_registry=self.mqtt_device_registry,
            feedback_tracker=self.mqtt_feedback_tracker,
            button_callback=self.on_button_press,
            named_scene_callback=self.start_scene_by_name
        )
        
        self.mqtt_client = MQTTClient(
            broker_host=self.config['broker_ip'],
            broker_port=int(self.config['port']),
            client_id=f"{self.room_id}_controller",
            room_id=self.room_id,
            retry_attempts=self.config.get('mqtt_retry_attempts', 3),
            retry_sleep=self.config.get('mqtt_retry_sleep', 2),
            connect_timeout=self.config.get('mqtt_connect_timeout', 10),
            reconnect_timeout=self.config.get('mqtt_reconnect_timeout', 5),
            reconnect_sleep=self.config.get('mqtt_reconnect_sleep', 0.5),
            check_interval=self.config.get('mqtt_check_interval', 60)
        )
        
        self.mqtt_client.set_handlers(
            self.mqtt_message_handler,
            self.mqtt_feedback_tracker,
            self.mqtt_device_registry
        )
        
        self.mqtt_client.connection_lost_callback = self._on_mqtt_connection_lost
        self.mqtt_client.connection_restored_callback = self._on_mqtt_connection_restored
        
        # Scene Parser
        self.scene_parser = SceneParser(
            mqtt_client=self.mqtt_client,
            audio_handler=self.audio_handler,
            video_handler=self.video_handler
        )
        
        # Connect scene parser to MQTT message handler
        self.mqtt_message_handler.scene_parser = self.scene_parser
        log.debug("Scene parser connected to MQTT message handler for transitions")
        
        # System Monitor
        self.system_monitor = SystemMonitor(
            health_check_interval=self.config.get('health_check_interval', 120)
        )
        self.system_monitor.log_startup_info(
            self.room_id, 
            self.config['broker_ip'], 
            self.config['button_pin']
        )
        
        # Button Handler
        try:
            self.button_handler = ButtonHandler(
                pin=self.config['button_pin'],
                debounce_time=self.config.get('debounce_time', 300)
            )
            self.button_handler.set_callback(self.on_button_press)
        except Exception as e:
            log.warning(f"Button handler initialization failed: {e}")
            self.button_handler = None
        
        # Web Dashboard
        self.web_dashboard = None
        start_web_dashboard_func = globals().get('start_web_dashboard')
        if start_web_dashboard_func:
            try:
                self.web_dashboard = start_web_dashboard_func(self, port=self.web_dashboard_port)
            except Exception as e:
                log.warning(f"Web dashboard failed to start: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        log.warning(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_requested = True
        if self.mqtt_client:
            self.mqtt_client.shutdown_requested = True

    def _on_mqtt_connection_lost(self):
        log.warning("MQTT connection lost - system will continue with limited functionality")

    def _on_mqtt_connection_restored(self):
        self.system_monitor.send_ready_notification()
        log.info(f"System ready - {self.room_id} operational")

    def on_button_press(self):
        """Handle button press to start default scene."""
        self._initiate_scene_start(self.json_file_name, "Button pressed - starting default scene")

    def start_default_scene(self):
        """Public method to start default scene."""
        self._initiate_scene_start(self.json_file_name, "Starting default scene")

    def start_scene_by_name(self, scene_file_name):
        """Public method to start a specific scene by file name."""
        self._initiate_scene_start(scene_file_name, f"Starting named scene: {scene_file_name}")
        return True

    def _initiate_scene_start(self, scene_filename, log_message):
        """Common entry point for starting a scene."""
        with self.scene_lock:
            if self.scene_running:
                log.info(f"Scene already running, ignoring request to start: {scene_filename}")
                return False
            
            if not self.mqtt_client or not self.mqtt_client.is_connected():
                log.warning("Starting scene without MQTT connection - external devices may not respond")
            
            self.scene_running = True
            log.info(log_message)

        threading.Thread(
            target=self._run_scene_logic, 
            args=(scene_filename,), 
            daemon=True
        ).start()
        return True

    def _run_scene_logic(self, scene_filename):
        """Worker thread function containing the core logic to load and run a scene."""
        scene_path = os.path.join(self.scenes_dir, self.room_id, scene_filename)
        
        # Store current scene name for statistics
        self.current_scene_name = scene_filename
        
        try:
            log.debug(f"Attempting to load scene from: {scene_path}")
            
            if not os.path.exists(scene_path):
                log.critical(f"Scene file not found: {scene_path}")
                self.scene_running = False
                return

            if not self.scene_parser:
                log.error("Scene parser not available")
                self.scene_running = False
                return

            log.debug(f"Loading scene: {scene_path}")
            if self.scene_parser.load_scene(scene_path):
                try:
                    self.run_scene()
                except Exception as e:
                    log.error(f"An error occurred during scene execution: {e}")
                finally:
                    self.scene_running = False
            else:
                log.error(f"Failed to load scene: {scene_filename}")
                self.scene_running = False

        except Exception as e:
            log.error(f"Critical error in scene thread: {e}")
            self.scene_running = False

    def stop_scene(self):
        """Zastaví prebiehajúcu scénu a vypne všetky externé zariadenia cez MQTT."""
        log.info(f"Initiating GLOBAL STOP for {self.room_id}")
        
        # 1. Nastavenie príznaku na zastavenie slučiek
        self.scene_running = False
        
        # 2. Zastavenie Parseru (StateMachine)
        if self.scene_parser:
            try:
                self.scene_parser.stop_scene()
            except Exception as e:
                log.error(f"Error stopping parser: {e}")

        # 3. Zastavenie lokálnych médií
        if self.audio_handler:
            try:
                self.audio_handler.stop_audio()
            except Exception as e:
                log.error(f"Error stopping audio: {e}")
        
        if self.video_handler:
            try:
                self.video_handler.stop_video()
            except Exception as e:
                log.error(f"Error stopping video: {e}")

        # 4. MQTT Broadcast STOP (Kľúčový FIX)
        self.broadcast_stop()
        return True

    def broadcast_stop(self):
        """Odošle STOP správu všetkým MQTT zariadeniam v miestnosti."""
        if self.mqtt_client and self.mqtt_client.is_connected():
            stop_topic = f"{self.room_id}/STOP"
            log.info(f"Broadcasting STOP signal to MQTT: {stop_topic}")
            try:
                self.mqtt_client.publish(stop_topic, "STOP")
            except Exception as e:
                log.error(f"Failed to publish stop message: {e}")

    def run_scene(self):
        """Execute the loaded state machine scene."""
        if not self.scene_parser.scene_data:
            log.error("No scene data available")
            self.scene_running = False 
            return

        log.debug("Starting state machine scene execution")

        # 1. ZAPNUTIE TRACKINGU
        if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
            if self.mqtt_client.feedback_tracker:
                self.mqtt_client.feedback_tracker.enable_feedback_tracking()

        # 2. ŠTART SCÉNY
        if not self.scene_parser.start_scene():
            log.error("Failed to start scene state machine")
            if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
                if self.mqtt_client.feedback_tracker:
                    self.mqtt_client.feedback_tracker.disable_feedback_tracking()
            return

        # 3. HLAVNÁ SLUČKA
        while not self.shutdown_requested:
            if not self.scene_running:
                log.info("Scene execution was stopped externally.")
                break
            
            scene_continues = self.scene_parser.process_scene()
            
            if not scene_continues:
                break
            
            time.sleep(self.scene_processing_sleep)

        log.info("Scene execution finished")

        # 4. VYPNUTIE TRACKINGU
        if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
            if self.mqtt_client.feedback_tracker:
                self.mqtt_client.feedback_tracker.disable_feedback_tracking()

        if self.video_handler:
            self.video_handler.stop_video()

        # FIX: Aj po prirodzenom skončení scény pošleme STOP broadcast
        self.broadcast_stop()

        self._update_scene_statistics()

    def _update_scene_statistics(self):
        """Update scene play statistics for the web dashboard."""
        if not self.web_dashboard:
            return
        try:
            # Use current_scene_name to update both total and specific stats
            if self.current_scene_name:
                self.web_dashboard.update_scene_stats(self.current_scene_name)
                self.web_dashboard.socketio.emit('stats_update', self.web_dashboard.stats)
            else:
                log.warning("Cannot update scene stats: Unknown scene name")
                # Fallback just in case
                self.web_dashboard.stats['total_scenes_played'] += 1
                self.web_dashboard.save_stats()
                self.web_dashboard.socketio.emit('stats_update', self.web_dashboard.stats)

        except Exception as e:
            log.error(f"Error updating stats: {e}")

    
    def system_restart(self):
        """Reboots the entire Raspberry Pi."""
        log.warning("Initiating System Reboot...")
        try:
            subprocess.Popen(['sudo', 'reboot'], shell=False)
        except Exception as e:
            log.error(f"Failed to initiate reboot: {e}")

    def system_shutdown(self):
        """Shuts down the Raspberry Pi."""
        log.warning("Initiating System Shutdown...")
        try:
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'], shell=False)
        except Exception as e:
            log.error(f"Failed to initiate shutdown: {e}")

    def service_restart(self):
        """Restarts the Python service (by exiting, assuming systemd will restart it)."""
        log.warning("Initiating Service Restart (Exit)...")
        self.shutdown_requested = True
        sys.exit(0) 

    def run(self):
        """Run the main application loop."""
        log.info("Starting Museum Controller")
        
        if self.mqtt_client:
            if not self.mqtt_client.establish_initial_connection():
                if self.shutdown_requested:
                    return
                log.warning("⚠️ NETWORK ERROR: System starting in OFFLINE MODE. Will retry connection in background.")
        
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
            log.info("Received keyboard interrupt")
        except Exception as e:
            log.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up all system resources gracefully."""
        if self._cleaned_up:
            return
        
        log.info("Initiating cleanup...")
        self._cleaned_up = True
        
        if self.mqtt_client:
            self.mqtt_client.cleanup()
        
        components = [
            (self.button_handler, "Button Handler"),
            (self.audio_handler, "Audio Handler"),
            (self.video_handler, "Video Handler"),
            (self.scene_parser, "Scene Parser")
        ]
        
        for component, name in components:
            if component and hasattr(component, 'cleanup'):
                try:
                    component.cleanup()
                except Exception as e:
                    log.error(f"{name} cleanup error: {e}")
        
        log.info("Museum Controller stopped cleanly")

def main():
    controller = None
    try:
        controller = MuseumController(config_manager)
        controller.run()
    except Exception as e:
        log.error(f"Critical application error: {e}")
        sys.exit(1)
    finally:
        if controller:
            controller.cleanup()

if __name__ == "__main__":
    main()