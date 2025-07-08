#!/usr/bin/env python3

import os
import sys
import signal
import json
import time
from datetime import datetime

# Add current directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Initialize configuration and logging first
from utils.config_manager import ConfigManager
from utils.logging_setup import setup_logging_from_config

# Initialize config manager (this will create default config if needed)
config_manager = ConfigManager()

# Get logging configuration and setup logging
logging_config = config_manager.get_logging_config()
log = setup_logging_from_config(logging_config)

# Import components after logging is set up
try:
    from utils.mqtt_client import MQTTClient
    from utils.scene_parser import SceneParser
    from utils.audio_handler import AudioHandler
    from utils.video_handler import VideoHandler
    from utils.system_monitor import SystemMonitor
    from utils.button_handler_improved import ButtonHandler
    from Web.web_dashboard import start_web_dashboard
    log.info("Core modules loaded successfully")
except ImportError as e:
    log.error(f"Failed to import core modules: {e}")
    sys.exit(1)

class MuseumController:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_all_config()
        
        # Extract config values
        self.room_id = self.config['room_id']
        self.json_file_name = self.config['json_file_name']
        self.scenes_dir = self.config['scenes_dir']
        self.audio_dir = self.config['audio_dir']
        self.video_dir = self.config['video_dir']
        self.ipc_socket = self.config['ipc_socket']
        self.black_image = self.config['black_image']
        self.web_dashboard_port = self.config['web_dashboard_port']
        self.mqtt_retry_attempts = self.config['mqtt_retry_attempts']
        self.mqtt_retry_sleep = self.config['mqtt_retry_sleep']
        self.mqtt_connect_timeout = self.config['mqtt_connect_timeout']
        self.mqtt_reconnect_timeout = self.config['mqtt_reconnect_timeout']
        self.mqtt_reconnect_sleep = self.config['mqtt_reconnect_sleep']
        self.scene_buffer_time = self.config['scene_buffer_time']
        
        # System timing configuration
        self.main_loop_sleep = self.config['main_loop_sleep']
        self.mqtt_check_interval = self.config['mqtt_check_interval']
        self.scene_processing_sleep = self.config['scene_processing_sleep']
        
        # Initialize system monitor
        self.system_monitor = SystemMonitor(
            health_check_interval=self.config['health_check_interval'],
            logger=log
        )
        
        # Log startup info
        self.system_monitor.log_startup_info(
            self.room_id, 
            self.config['broker_ip'], 
            self.config['button_pin']
        )
        
        # Create directories
        os.makedirs(self.scenes_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)
        
        # Signal handlers
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self._cleaned_up = False
        
        # Initialize components with error handling
        self.mqtt_client = self._safe_init(
            lambda: MQTTClient(self.config['broker_ip'], client_id=f"rpi_room_{self.room_id}", logger=log),
            "MQTT Client")
        self.audio_handler = self._safe_init(
            lambda: AudioHandler(self.audio_dir, logger=log), 
            "Audio Handler")
        self.video_handler = self._safe_init(
            lambda: VideoHandler(
                video_dir=self.video_dir,
                ipc_socket=self.ipc_socket,
                black_image=self.black_image,
                logger=log
            ),
            "Video Handler")
        self.scene_parser = self._safe_init(
            lambda: SceneParser(self.audio_handler, self.video_handler, logger=log), 
            "Scene Parser")
        self.button_handler = self._safe_init(
            lambda: ButtonHandler(self.config['button_pin'], logger=log), 
            "Button Handler")
        
        if self.button_handler:
            self.button_handler.set_callback(self.on_button_press)
        
        # State tracking
        self.scene_running = False
        self.connected_to_broker = False
        self.start_time = time.time()
        
        # Initialize web dashboard if available
        self.web_dashboard = None
        if start_web_dashboard:
            try:
                self.web_dashboard = start_web_dashboard(self, port=self.web_dashboard_port)
            except Exception as e:
                log.warning(f"Web dashboard failed to start: {e}")
    
    def _safe_init(self, init_func, name):
        try:
            component = init_func()
            return component
        except Exception as e:
            log.error(f"{name} initialization failed: {e}")
            return None
    
    def _signal_handler(self, signum, frame):
        log.warning(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_requested = True
    
    def test_mqtt_connection(self):
        if not self.mqtt_client:
            log.error("MQTT client not initialized")
            return False
        
        broker_ip = self.config['broker_ip']
        
        # Try main broker
        for attempt in range(1, self.mqtt_retry_attempts + 1):
            if self.shutdown_requested: 
                return False
            
            log.debug(f"MQTT connection attempt {attempt}/{self.mqtt_retry_attempts} to {broker_ip}")
            
            try:
                if self.mqtt_client.connect(timeout=self.mqtt_connect_timeout):
                    self.connected_to_broker = True
                    log.info(f"MQTT connected successfully on attempt {attempt}")
                    return True
            except Exception as e:
                log.warning(f"Connection attempt {attempt} failed: {e}")
            
            if attempt < self.mqtt_retry_attempts:
                time.sleep(self.mqtt_retry_sleep)
        
        # Try localhost fallback
        if broker_ip != 'localhost' and not self.shutdown_requested:
            log.info("Attempting localhost fallback connection")
            self.mqtt_client.broker_host = 'localhost'
            
            try:
                if self.mqtt_client.connect(timeout=self.mqtt_connect_timeout):
                    self.connected_to_broker = True
                    log.info("MQTT connected via localhost fallback")
                    return True
            except Exception as e:
                log.warning(f"Localhost fallback failed: {e}")
        
        log.error("MQTT connection completely failed")
        return False
    
    def on_button_press(self):
        if self.scene_running:
            log.info("Scene already running, ignoring button press")
            return
        
        if not self.connected_to_broker:
            log.error("Cannot start scene: MQTT not connected")
            return
        
        self.start_default_scene()
    
    def start_default_scene(self):
        if not self.connected_to_broker:
            log.error("Cannot start scene: MQTT not connected")
            return
        
        scene_path = os.path.join(self.scenes_dir, self.room_id, self.json_file_name)
        
        if not os.path.exists(scene_path):
            log.critical(f"Scene file not found: {scene_path}")
        
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
        if not self.scene_parser.scene_data:
            log.error("No scene data available")
            return
        
        start_time = time.time()
        max_time = max(action["timestamp"] for action in self.scene_parser.scene_data)
        log.info(f"Starting scene execution (duration: {max_time}s)")
        
        while time.time() - start_time <= max_time + self.scene_buffer_time and not self.shutdown_requested:
            actions = self.scene_parser.get_current_actions(
                self.mqtt_client if self.connected_to_broker else None
            )
            
            if actions:
                current_time = time.time() - start_time
                for action in actions:
                    status = "" if self.connected_to_broker else " (simulation)"
                    log.info(f"[{current_time:.1f}s] {action['topic']} = {action['message']}{status}")
            
            time.sleep(self.scene_processing_sleep)
        
        log.info("Scene execution completed")
        self.scene_running = False
        if self.video_handler:
            self.video_handler.stop_video()
        
        # Update statistics if web dashboard is available
        if self.web_dashboard:
            try:
                scene_name = self.json_file_name  # Default scene name from config
                self.web_dashboard.stats['total_scenes_played'] += 1
                self.web_dashboard.stats['scene_play_counts'][scene_name] = \
                    self.web_dashboard.stats['scene_play_counts'].get(scene_name, 0) + 1
                self.web_dashboard.save_stats()
                self.web_dashboard.socketio.emit('stats_update', self.web_dashboard.stats)
                log.info(f"Updated statistics for scene: {scene_name}")
            except Exception as e:
                log.error(f"Error updating stats for scene: {e}")
    
    def check_mqtt_status(self):
        if not self.mqtt_client: 
            return
        
        was_connected = self.connected_to_broker
        
        try:
            currently_connected = self.mqtt_client.is_connected()
            if hasattr(self.mqtt_client.client, 'is_connected'):
                currently_connected = currently_connected and self.mqtt_client.client.is_connected()
        except Exception as e:
            log.error(f"MQTT status check error: {e}")
            currently_connected = False
        
        self.connected_to_broker = currently_connected
        
        if was_connected and not currently_connected:
            log.warning("MQTT connection lost")
        elif not was_connected and currently_connected:
            log.info("MQTT connection restored")
        
        if not currently_connected and not self.shutdown_requested:
            try:
                self.mqtt_client.client.loop_stop()
                self.mqtt_client.client.disconnect()
                time.sleep(self.mqtt_reconnect_sleep)
                
                if self.mqtt_client.connect(timeout=self.mqtt_reconnect_timeout):
                    log.info("MQTT reconnected successfully")
                    self.connected_to_broker = True
                else:
                    log.debug("MQTT reconnection failed, will retry next check")
            except Exception as e:
                log.debug(f"MQTT reconnection error: {e}")
    
    def run(self):
        log.info("Starting Museum Controller")
        
        if not self.test_mqtt_connection():
            if self.shutdown_requested: 
                return
            log.critical("CRITICAL: Unable to establish MQTT connection")
            sys.exit(1)
        
        self.system_monitor.send_ready_notification()
        log.info(f"System ready - {self.room_id} operational")
        
        last_health_check = time.time()
        last_mqtt_check = time.time()
        
        use_polling = (hasattr(self.button_handler, 'use_polling') and 
                      self.button_handler.use_polling if self.button_handler else False)
        
        try:
            while not self.shutdown_requested:
                current_time = time.time()
                
                if current_time - last_health_check > self.system_monitor.health_check_interval:
                    self.system_monitor.perform_health_check(self.mqtt_client, self.connected_to_broker)
                    last_health_check = current_time
                
                if current_time - last_mqtt_check > self.mqtt_check_interval:
                    self.check_mqtt_status()
                    last_mqtt_check = current_time
                
                if use_polling and self.button_handler:
                    self.button_handler.check_button_polling()
                
                time.sleep(self.main_loop_sleep)
                
        except KeyboardInterrupt:
            log.info("Received keyboard interrupt")
        except Exception as e:
            log.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            self.cleanup()
    
    def cleanup(self):
        if self._cleaned_up:
            return
        
        log.info("Initiating cleanup...")
        self._cleaned_up = True
        
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
        
        if self.mqtt_client and self.connected_to_broker:
            try:
                self.mqtt_client.disconnect()
                log.info("MQTT disconnected successfully")
            except Exception as e:
                log.error(f"MQTT disconnect error: {e}")
        
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