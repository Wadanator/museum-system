#!/usr/bin/env python3

import os
import sys
import signal
import time
import logging
import threading

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

# EARLY LOG LEVEL SETUP
def apply_early_log_levels():
    """Apply log levels early to suppress startup noise"""
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO, 
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    component_levels = logging_config.get('component_levels', {})
    
    early_suppressions = {
        'museum.main': 'WARNING',
        'museum.audio': 'WARNING', 
        'museum.video': 'WARNING',
        'museum.mqtt': 'WARNING',
        'museum.scene_parser': 'WARNING',
        'museum.btn_handler': 'WARNING',
        'museum.sys_monitor': 'ERROR',
        'museum.config': 'ERROR',
        'museum.setup': 'ERROR',
    }
    
    all_levels = {**early_suppressions, **component_levels}
    
    for logger_name, level_str in all_levels.items():
        level = level_map.get(level_str.upper(), logging.INFO)
        logging.getLogger(logger_name).setLevel(level)

apply_early_log_levels()
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
        self.scene_buffer_time = self.config['scene_buffer_time']
        self.web_dashboard_port = self.config['web_dashboard_port']
        
        # Scene execution state
        self.scene_running = False
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
            self.video_handler = VideoHandler(self.config['video_dir'])
        except Exception as e:
            log.warning(f"Video handler initialization failed: {e}")
            self.video_handler = None
        
        # MQTT Components
        self.mqtt_device_registry = MQTTDeviceRegistry(
            device_timeout=self.config.get('device_timeout', 180)
        )
        
        self.mqtt_feedback_tracker = MQTTFeedbackTracker(
            feedback_timeout=self.config.get('feedback_timeout', 2)
        )
        
        # Create message handler (scene_parser will be set later)
        self.mqtt_message_handler = MQTTMessageHandler()
        self.mqtt_message_handler.set_handlers(
            device_registry=self.mqtt_device_registry,
            feedback_tracker=self.mqtt_feedback_tracker,
            button_callback=self.on_button_press
        )
        
        self.mqtt_client = MQTTClient(
            broker_host=self.config['broker_ip'],
            broker_port=self.config['port'],
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
        
        # Set connection callbacks
        self.mqtt_client.connection_lost_callback = self._on_mqtt_connection_lost
        self.mqtt_client.connection_restored_callback = self._on_mqtt_connection_restored
        
        # Scene Parser - NEW: State Machine version
        self.scene_parser = SceneParser(
            mqtt_client=self.mqtt_client,
            audio_handler=self.audio_handler,
            video_handler=self.video_handler
        )
        
        # NEW: Connect scene parser to MQTT message handler for MQTT transitions
        self.mqtt_message_handler.scene_parser = self.scene_parser
        log.debug("Scene parser connected to MQTT message handler for transitions")
        
        # System Monitor
        self.system_monitor = SystemMonitor(
            health_check_interval=self.config.get('health_check_interval', 120)
        )
        
        # Log startup info
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
        """Handle shutdown signals to initiate graceful cleanup."""
        log.warning(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_requested = True
        if self.mqtt_client:
            self.mqtt_client.shutdown_requested = True

    def _on_mqtt_connection_lost(self):
        """Handle loss of MQTT connection."""
        log.warning("MQTT connection lost - system will continue with limited functionality")

    def _on_mqtt_connection_restored(self):
        """Handle restoration of MQTT connection."""
        self.system_monitor.send_ready_notification()
        log.info(f"System ready - {self.room_id} operational")
        log.debug("MQTT connection restored - full functionality available")

    def on_button_press(self):
        """Handle button press events to start the default scene in a new thread."""
        with self.scene_lock:
            if self.scene_running:
                log.info("Scene already running, ignoring button press")
                return
            
            if not self.mqtt_client or not self.mqtt_client.is_connected():
                log.error("Cannot start scene: MQTT not connected")
                return
            
            self.scene_running = True
            log.info("Button pressed - starting default scene")

        scene_thread = threading.Thread(target=self.start_default_scene, daemon=True)
        scene_thread.start()

    def start_default_scene(self):
        """Load and start the default scene for the current room."""
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            log.error("Cannot start scene: MQTT not connected")
            self.scene_running = False
            return

        # Build full path: scenes_dir/room_id/json_file_name
        scene_path = os.path.join(self.scenes_dir, self.room_id, self.json_file_name)
        
        # DEBUG: Log the path we're trying to load
        log.debug(f"Attempting to load scene from: {scene_path}")
        log.debug(f"File exists: {os.path.exists(scene_path)}")

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
                self.scene_parser.start_scene()
                self.run_scene()
            except Exception as e:
                log.error(f"An error occurred during scene execution: {e}")
            finally:
                self.scene_running = False
        else:
            log.error("Failed to load scene")
            self.scene_running = False

    def run_scene(self):
        """
        Execute the loaded state machine scene.
        NEW: Replaces timestamp-based execution with state machine logic.
        """
        if not self.scene_parser.scene_data:
            log.error("No scene data available")
            self.scene_running = False 
            return

        log.debug("Starting state machine scene execution")

        # Enable MQTT feedback tracking for the scene
        if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
            if self.mqtt_client.feedback_tracker:
                self.mqtt_client.feedback_tracker.enable_feedback_tracking()

        # Main state machine loop
        while not self.shutdown_requested:
            if not self.scene_running:
                log.info("Scene execution was stopped externally.")
                break
            
            # Process current state (returns False when scene ends)
            scene_continues = self.scene_parser.process_scene()
            
            if not scene_continues:
                break
            
            # Sleep to prevent CPU overload
            time.sleep(self.scene_processing_sleep)

        # Clean up after scene completion
        log.info("Scene execution finished")

        # Disable MQTT feedback tracking
        if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
            if self.mqtt_client.feedback_tracker:
                self.mqtt_client.feedback_tracker.disable_feedback_tracking()

        if self.video_handler:
            self.video_handler.stop_video()

        self._update_scene_statistics()

    def _update_scene_statistics(self):
        """Update scene play statistics for the web dashboard."""
        if not self.web_dashboard:
            return
            
        try:
            scene_name = self.json_file_name
            self.web_dashboard.stats['total_scenes_played'] += 1
            self.web_dashboard.stats['scene_play_counts'][scene_name] = \
                self.web_dashboard.stats['scene_play_counts'].get(scene_name, 0) + 1
            self.web_dashboard.save_stats()
            self.web_dashboard.socketio.emit('stats_update', self.web_dashboard.stats)
            log.debug(f"Updated statistics for scene: {scene_name}")
        except Exception as e:
            log.error(f"Error updating stats for scene: {e}")

    def run(self):
        """Run the main application loop with periodic health checks."""
        log.info("Starting Museum Controller")
        
        # Establish MQTT connection
        if not self.mqtt_client or not self.mqtt_client.establish_initial_connection():
            if self.shutdown_requested:
                return
            log.critical("CRITICAL: Unable to establish MQTT connection")
            sys.exit(1)
        
        # Track time for periodic tasks
        last_device_cleanup = time.time()
        device_cleanup_interval = self.config['device_cleanup_interval']
        
        # Main loop with health checks and button polling
        use_polling = (hasattr(self.button_handler, 'use_polling') and 
                    self.button_handler.use_polling if self.button_handler else False)
        
        try:
            while not self.shutdown_requested:      
                current_time = time.time()
                
                # Poll button state if required
                if use_polling and self.button_handler:
                    self.button_handler.check_button_polling()
                
                # Periodic device cleanup (check for stale devices)
                if current_time - last_device_cleanup >= device_cleanup_interval:
                    if self.mqtt_device_registry:
                        self.mqtt_device_registry.cleanup_stale_devices()
                    last_device_cleanup = current_time
                
                # Adjust sleep time based on scene activity
                sleep_time = self.main_loop_sleep if self.scene_running else (self.main_loop_sleep + 0.5)
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
        
        # Stop MQTT client
        if self.mqtt_client:
            self.mqtt_client.cleanup()
        
        # Clean up other components
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
    """Main entry point for the museum controller application."""
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