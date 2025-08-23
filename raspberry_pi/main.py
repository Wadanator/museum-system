#!/usr/bin/env python3

import os
import sys
import signal
import time
from datetime import datetime

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
    from Web.web_dashboard import start_web_dashboard
    log.info("Core modules imported successfully")
except ImportError as e:
    log.critical(f"Failed to import core modules: {e}")
    sys.exit(1)

class MuseumController:
    """Main controller for the museum system, managing all components and operations."""
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_all_config()
        
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
            ('audio_handler', lambda: AudioHandler(self.audio_dir), "Audio Handler"),
            ('video_handler', lambda: VideoHandler(self.video_dir, self.ipc_socket, self.black_image), "Video Handler"),
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
            # Initialize MQTT client
            client = MQTTClient(
                broker_host=self.config['broker_ip'],
                broker_port=self.config['port'],
                client_id=f"rpi_room_{self.room_id}",
                retry_attempts=self.config['mqtt_retry_attempts'],
                retry_sleep=self.config['mqtt_retry_sleep'],
                connect_timeout=self.config['mqtt_connect_timeout'],
                reconnect_timeout=self.config['mqtt_reconnect_timeout'],
                reconnect_sleep=self.config['mqtt_reconnect_sleep'],
                check_interval=self.config['mqtt_check_interval']
            )
            
            # Initialize handlers
            self.mqtt_feedback_tracker = MQTTFeedbackTracker()
            self.mqtt_device_registry = MQTTDeviceRegistry()
            self.mqtt_message_handler = MQTTMessageHandler()
            
            # Connect handlers together
            self.mqtt_message_handler.set_handlers(
                feedback_tracker=self.mqtt_feedback_tracker,
                device_registry=self.mqtt_device_registry
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
        log.info("MQTT connection restored - full functionality available")

    def on_button_press(self):
        """Handle button press events to start the default scene."""
        if self.scene_running:
            log.info("Scene already running, ignoring button press")
            return
        
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            log.error("Cannot start scene: MQTT not connected")
            return
        
        self.start_default_scene()

    def start_default_scene(self):
        """Load and start the default scene for the current room."""
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            log.error("Cannot start scene: MQTT not connected")
            return
        
        scene_path = os.path.join(self.scenes_dir, self.room_id, self.json_file_name)
        
        if not os.path.exists(scene_path):
            log.critical(f"Scene file not found: {scene_path}")
            return
        
        if not self.scene_parser:
            log.error("Scene parser not available")
            return
        
        log.info(f"Loading scene: {scene_path}")
        if self.scene_parser.load_scene(scene_path):
            self.scene_running = True
            self.scene_parser.start_scene()
            self.run_scene()
        else:
            log.error("Failed to load scene")

    def run_scene(self):
        """Execute the loaded scene with precise timing control and MQTT feedback."""
        if not self.scene_parser.scene_data:
            log.error("No scene data available")
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
        
        self.scene_running = False
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
            log.info(f"Updated statistics for scene: {scene_name}")
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
        
        # Main loop with health checks and button polling
        use_polling = (hasattr(self.button_handler, 'use_polling') and 
                      self.button_handler.use_polling if self.button_handler else False)
        
        try:
            while not self.shutdown_requested:      
                # Poll button state if required
                if use_polling and self.button_handler:
                    self.button_handler.check_button_polling()
                
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