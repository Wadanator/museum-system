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

# EARLY LOG LEVEL SETUP - Apply component-specific levels BEFORE importing modules
def apply_early_log_levels():
    """Apply log levels early to suppress startup noise"""
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO, 
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    # Get component levels from config
    component_levels = logging_config.get('component_levels', {})
    
    # Apply early to prevent startup message noise
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
    
    # Merge with user config, user config takes precedence
    all_levels = {**early_suppressions, **component_levels}
    
    for logger_name, level_str in all_levels.items():
        level = level_map.get(level_str.upper(), logging.INFO)
        logging.getLogger(logger_name).setLevel(level)

# Apply early log filtering
apply_early_log_levels()

# Now get the properly configured logger
log = get_logger('main')

# Import core system modules (now with proper log levels applied)
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
    # Only log this if main logger is at INFO level or below
    if log.isEnabledFor(logging.INFO):
        log.debug("Core modules imported successfully")
except ImportError as e:
    log.critical(f"Failed to import core modules: {e}")
    sys.exit(1)

class MuseumController:
    """Main controller for the museum system, managing all components and operations."""
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_all_config()
        self.scene_lock = threading.Lock()
        # Extract commonly used configuration values
        self._extract_config_values()
        
        # Initialize system monitor and log startup details
        self.system_monitor = SystemMonitor(health_check_interval=self.config['health_check_interval'])
        self.system_monitor.log_startup_info(self.room_id, self.config['broker_ip'], self.config['button_pin'])
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Initialize all system components
        self._initialize_components()
        
        # Track system state
        self.scene_running = False
        self.start_time = time.monotonic()
        
        # Start the web dashboard
        self._setup_web_dashboard()

    def _extract_config_values(self):
        """Extract frequently used configuration values for convenient access."""
        config_keys = [
            'room_id', 'json_file_name', 'scenes_dir', 'audio_dir', 'video_dir',
            'ipc_socket', 'black_image', 'web_dashboard_port', 'scene_buffer_time',
            'scene_processing_sleep', 'main_loop_sleep', 'debounce_time'
        ]
        for key in config_keys:
            setattr(self, key, self.config[key])

    def _setup_signal_handlers(self):
        """Configure signal handlers for SIGTERM and SIGINT to ensure graceful shutdown."""
        self.shutdown_requested = False
        self._cleaned_up = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _initialize_components(self):
            """Initialize system components with error handling."""
            # Set up MQTT client
            self.mqtt_client = self._init_mqtt_client()
            
            # Initialize other components
            components = [
                ('audio_handler', lambda: AudioHandler(
                    self.audio_dir,
                    max_init_attempts=self.config['audio_max_init_attempts'],
                    init_retry_delay=self.config['audio_init_retry_delay']
                ), "Audio Handler"),
                ('video_handler', lambda: VideoHandler(
                    self.video_dir, 
                    self.ipc_socket, 
                    self.black_image,
                    health_check_interval=self.config['video_health_check_interval'],
                    max_restart_attempts=self.config['video_max_restart_attempts'],
                    restart_cooldown=self.config['video_restart_cooldown']
                ), "Video Handler"),
                ('scene_parser', lambda: SceneParser(self.audio_handler, self.video_handler), "Scene Parser"),
                ('button_handler', lambda: ButtonHandler(self.config['button_pin'], debounce_time=self.debounce_time), "Button Handler")
            ]
            
            for attr_name, init_func, name in components:
                setattr(self, attr_name, self._safe_init(init_func, name))
            
            # Configure button callback if available
            if self.button_handler:
                self.button_handler.set_callback(self.on_button_press)

    def _init_mqtt_client(self):
            """Initialize the MQTT client with all handlers."""
            try:
                # Initialize MQTT client s room_id
                client = MQTTClient(
                    broker_host=self.config['broker_ip'],
                    broker_port=self.config['port'],
                    client_id=f"rpi_room_{self.room_id}",
                    room_id=self.room_id,
                    retry_attempts=self.config['mqtt_retry_attempts'],
                    retry_sleep=self.config['mqtt_retry_sleep'],
                    connect_timeout=self.config['mqtt_connect_timeout'],
                    reconnect_timeout=self.config['mqtt_reconnect_timeout'],
                    reconnect_sleep=self.config['mqtt_reconnect_sleep'],
                    check_interval=self.config['mqtt_check_interval']
                )
                
                # Initialize handlers
                self.mqtt_feedback_tracker = MQTTFeedbackTracker(
                    feedback_timeout=self.config['feedback_timeout']
                )
                self.mqtt_device_registry = MQTTDeviceRegistry(
                    device_timeout=self.config['device_timeout']
                )
                self.mqtt_message_handler = MQTTMessageHandler()
                
                # Connect handlers together
                self.mqtt_message_handler.set_handlers(
                    feedback_tracker=self.mqtt_feedback_tracker,
                    device_registry=self.mqtt_device_registry,
                    button_callback=self.on_button_press
                )
                
                client.set_handlers(
                    message_handler=self.mqtt_message_handler,
                    feedback_tracker=self.mqtt_feedback_tracker,
                    device_registry=self.mqtt_device_registry
                )
                
                client.set_connection_callbacks(
                    lost_callback=self._on_mqtt_connection_lost,
                    restored_callback=self._on_mqtt_connection_restored
                )
                
                return client
            except Exception as e:
                log.error(f"MQTT Client initialization failed: {e}")
                return None

    def _safe_init(self, init_func, name):
        """Safely initialize a component, logging any errors."""
        try:
            return init_func()
        except Exception as e:
            log.error(f"{name} initialization failed: {e}")
            return None

    def _setup_web_dashboard(self):
        """Start the web dashboard if available."""
        self.web_dashboard = None
        if start_web_dashboard:
            try:
                self.web_dashboard = start_web_dashboard(self, port=self.web_dashboard_port)
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
        # Thread-safe check and set scene_running
        with self.scene_lock:
            if self.scene_running:
                log.info("Scene already running, ignoring button press")
                return
            
            # Check MQTT connection before setting scene_running
            if not self.mqtt_client or not self.mqtt_client.is_connected():
                log.error("Cannot start scene: MQTT not connected")
                return
            
            # Set scene_running only after all checks pass
            self.scene_running = True
            log.info("Button pressed - starting default scene")

        # Start scene in new thread (scene_running is already set)
        scene_thread = threading.Thread(target=self.start_default_scene, daemon=True)
        scene_thread.start()

    def start_default_scene(self):
        """Load and start the default scene for the current room."""
        # Remove the problematic scene_running check - it's already set by on_button_press()
        
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            log.error("Cannot start scene: MQTT not connected")
            self.scene_running = False  # Reset on error
            return

        scene_path = os.path.join(self.scenes_dir, self.room_id, self.json_file_name)

        if not os.path.exists(scene_path):
            log.critical(f"Scene file not found: {scene_path}")
            self.scene_running = False  # Reset on error
            return

        if not self.scene_parser:
            log.error("Scene parser not available")
            self.scene_running = False  # Reset on error
            return

        log.info(f"Loading scene: {scene_path}")
        if self.scene_parser.load_scene(scene_path):
            # scene_running is already True from on_button_press()
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
        """Execute the loaded scene with precise timing control and MQTT feedback."""
        if not self.scene_parser.scene_data:
            log.error("No scene data available")
            self.scene_running = False 
            return

        start_time = time.time()
        max_time = max(action["timestamp"] for action in self.scene_parser.scene_data)
        log.info(f"Starting scene execution (duration: {max_time}s)")

        # Enable MQTT feedback tracking for the scene
        if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
            if self.mqtt_client.feedback_tracker:
                self.mqtt_client.feedback_tracker.enable_feedback_tracking()

        # Process scene actions within the specified time window
        while time.time() - start_time <= max_time + self.scene_buffer_time and not self.shutdown_requested:
            if not self.scene_running:
                log.info("Scene execution was stopped externally.")
                break

            actions = self.scene_parser.get_current_actions(
                self.mqtt_client if self.mqtt_client and self.mqtt_client.is_connected() else None
            )

            if actions:
                current_time = time.time() - start_time
                for action in actions:
                    status = "" if self.mqtt_client and self.mqtt_client.is_connected() else " (simulation)"
                    log.info(f"[{current_time:.1f}s] {action['topic']} = {action['message']}{status}")

            time.sleep(self.scene_processing_sleep)

        # Clean up after scene completion
        log.info("Scene execution completed")

        # Disable MQTT feedback tracking
        if self.mqtt_client and hasattr(self.mqtt_client, 'feedback_tracker'):
            if self.mqtt_client.feedback_tracker:
                self.mqtt_client.feedback_tracker.disable_feedback_tracking()

        # self.scene_running = False 
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