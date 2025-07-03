#!/usr/bin/env python3

import os, time, sys, logging, signal, json
from datetime import datetime

# Add current directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.logging_setup import setup_logging
log = setup_logging()

# Import components
try:
    from utils.mqtt_client import MQTTClient
    from utils.scene_parser import SceneParser
    from utils.audio_handler import AudioHandler
    from utils.config_manager import ConfigManager
    from utils.system_monitor import SystemMonitor
    try:
        from Web.web_dashboard import start_web_dashboard
        log.info("Web dashboard module loaded")
    except ImportError as e:
        log.warning(f"Web dashboard not available: {e}")
        start_web_dashboard = None
    log.info("Core modules loaded")
except ImportError as e:
    log.error(f"Import failed: {e}")
    sys.exit(1)

# Button handler
try:
    from utils.button_handler_improved import ButtonHandler
    log.info("Button handler loaded")
except ImportError as e:
    log.error(f"Button handler import failed: {e}")
    sys.exit(1)

class MuseumController:
    def __init__(self, config_file=None):
        # Initialize configuration manager
        self.config_manager = ConfigManager(config_file, logger=log)
        config = self.config_manager.get_all_config()
        
        # Extract config values
        self.room_id = config['room_id']
        self.json_file_name = config['json_file_name']
        self.scenes_dir = config['scenes_dir']
        self.audio_dir = config['audio_dir']
        
        # System timing configuration
        self.main_loop_sleep = config['main_loop_sleep']
        self.mqtt_check_interval = config['mqtt_check_interval']
        self.scene_processing_sleep = config['scene_processing_sleep']
        
        # Initialize system monitor
        self.system_monitor = SystemMonitor(
            health_check_interval=config['health_check_interval'],
            logger=log
        )
        
        # Log startup info
        self.system_monitor.log_startup_info(
            self.room_id, 
            config['broker_ip'], 
            config['button_pin']
        )
        
        # Create directories
        os.makedirs(self.scenes_dir, exist_ok=True)
        
        # Signal handlers
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self._cleaned_up = False  # Flag to track cleanup status
        
        # Initialize components with error handling
        self.mqtt_client = self._safe_init(
            lambda: MQTTClient(config['broker_ip'], client_id=f"rpi_room_{self.room_id}", use_logging=False, logger=log),
            "MQTT")
        self.audio_handler = self._safe_init(lambda: AudioHandler(self.audio_dir, logger=log), "Audio")
        self.scene_parser = self._safe_init(lambda: SceneParser(self.audio_handler), "Scene parser")
        self.button_handler = self._safe_init(lambda: ButtonHandler(config['button_pin'], logger=log), "Button")
        
        if self.button_handler:
            self.button_handler.set_callback(self.on_button_press)
        
        # State tracking
        self.scene_running = False
        self.connected_to_broker = False
        # Dashboard
        self.start_time = time.time()
        self.web_dashboard = None
        if start_web_dashboard:
            try:
                self.web_dashboard = start_web_dashboard(self, port=5000)
                log.info("Web dashboard started on port 5000")
            except Exception as e:
                log.warning(f"Web dashboard failed to start: {e}")
    
    def _safe_init(self, init_func, name):
        try:
            return init_func()
        except Exception as e:
            log.error(f"{name} init failed: {e}")
            return None
    
    def _signal_handler(self, signum, frame):
        log.info(f"Signal {signum} received, shutting down...")
        self.shutdown_requested = True
    
    def test_mqtt_connection(self):
        if not self.mqtt_client:
            log.error("MQTT client missing")
            return False
        
        broker_ip = self.config_manager.get_mqtt_config()['broker_ip']
        
        # Try main broker
        for attempt in range(1, 11):
            if self.shutdown_requested: return False
            log.info(f"MQTT attempt {attempt}/10 to {broker_ip}")
            
            try:
                if self.mqtt_client.connect(timeout=10):
                    self.connected_to_broker = True
                    log.info(f"MQTT connected on attempt {attempt}")
                    return True
            except Exception as e:
                log.warning(f"Attempt {attempt} failed: {e}")
            
            if attempt < 10:
                for _ in range(5):
                    if self.shutdown_requested: return False
                    time.sleep(1)
        
        # Try localhost fallback
        if broker_ip != 'localhost' and not self.shutdown_requested:
            log.info("Trying localhost fallback")
            self.mqtt_client.broker_host = 'localhost'
            
            for attempt in range(1, 11):
                if self.shutdown_requested: return False
                try:
                    if self.mqtt_client.connect(timeout=10):
                        self.connected_to_broker = True
                        log.info(f"Localhost connected on attempt {attempt}")
                        return True
                except Exception as e:
                    log.warning(f"Localhost attempt {attempt} failed: {e}")
                
                if attempt < 10:
                    for _ in range(5):
                        if self.shutdown_requested: return False
                        time.sleep(1)
        
        log.error("MQTT completely unavailable")
        return False
    
    def on_button_press(self):
        if self.scene_running:
            log.warning("Scene running, ignoring button")
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
            log.warning(f"Scene missing: {scene_path}")
            self.create_default_scene(scene_path)
        
        if not self.scene_parser:
            log.error("Scene parser unavailable")
            return
        
        log.info(f"Loading: {scene_path}")
        if self.scene_parser.load_scene(scene_path):
            self.scene_running = True
            self.scene_parser.start_scene()
            self.run_scene()
        else:
            log.error("Scene load failed")
    
    def create_default_scene(self, scene_path):
        default_scene = [
            {"timestamp": 0, "topic": f"{self.room_id}/light", "message": "ON"},
            {"timestamp": 2.0, "topic": f"{self.room_id}/audio", "message": "PLAY_WELCOME"},
            {"timestamp": 5.0, "topic": f"{self.room_id}/light", "message": "BLINK"},
            {"timestamp": 8.0, "topic": f"{self.room_id}/audio", "message": "STOP"},
            {"timestamp": 10.0, "topic": f"{self.room_id}/light", "message": "OFF"}
        ]
        
        os.makedirs(os.path.dirname(scene_path), exist_ok=True)
        with open(scene_path, 'w') as f:
            json.dump(default_scene, f, indent=2)
        log.info(f"Default scene created: {scene_path}")
    
    def run_scene(self):
        if not self.scene_parser.scene_data:
            log.error("No scene data")
            return
        
        start_time = time.time()
        max_time = max(action["timestamp"] for action in self.scene_parser.scene_data)
        log.info(f"Scene duration: {max_time}s")
        
        while time.time() - start_time <= max_time + 1 and not self.shutdown_requested:
            actions = self.scene_parser.get_current_actions(self.mqtt_client if self.connected_to_broker else None)
            
            if actions:
                current_time = time.time() - start_time
                for action in actions:
                    status = "" if self.connected_to_broker else " (sim)"
                    log.info(f"[{current_time:.1f}s] {action['topic']} = {action['message']}{status}")
            
            time.sleep(self.scene_processing_sleep)
        
        log.info("Scene completed")
        self.scene_running = False
    
    def run(self):
        log.info("Starting Museum Controller")
        
        if not self.test_mqtt_connection():
            if self.shutdown_requested: return
            log.error("CRITICAL: No MQTT connection")
            sys.exit(1)
        
        self.system_monitor.send_ready_notification()
        log.info(f"System ready - {self.room_id} operational")
        
        last_health = time.time()
        last_mqtt = time.time()
        
        # Check for polling mode
        use_polling = hasattr(self.button_handler, 'use_polling') and self.button_handler.use_polling
        
        try:
            while not self.shutdown_requested:
                current_time = time.time()
                
                # Health checks
                if current_time - last_health > self.system_monitor.health_check_interval:
                    self.system_monitor.perform_health_check(self.mqtt_client, self.connected_to_broker)
                    last_health = current_time
                
                # MQTT checks
                if current_time - last_mqtt > self.mqtt_check_interval:
                    self.check_mqtt_status()
                    last_mqtt = current_time
                
                # Button polling if needed
                if use_polling and self.button_handler:
                    self.button_handler.check_button_polling()
                
                time.sleep(self.main_loop_sleep)
        except Exception as e:
            log.error(f"Run loop error: {e}")
            raise  # Re-raise to be caught by main()
        finally:
            self.cleanup()
    
    def cleanup(self):
        if self._cleaned_up:
            log.debug("Cleanup already performed, skipping")
            return
        log.info("Cleanup started")
        self._cleaned_up = True
        
        for component, name in [(self.button_handler, "Button"), 
                               (self.audio_handler, "Audio")]:
            if component:
                try:
                    component.cleanup()
                    log.info(f"{name} cleaned")
                except Exception as e:
                    log.error(f"{name} cleanup error: {e}")
        
        if self.mqtt_client and self.connected_to_broker:
            try:
                self.mqtt_client.disconnect()
                log.info("MQTT disconnected")
            except Exception as e:
                log.error(f"MQTT disconnect error: {e}")
        
        log.info("Controller stopped cleanly")
    
    def check_mqtt_status(self):
        if not self.mqtt_client: return
        
        was_connected = self.connected_to_broker
        
        try:
            currently_connected = self.mqtt_client.is_connected()
            if hasattr(self.mqtt_client.client, 'is_connected'):
                currently_connected = currently_connected and self.mqtt_client.client.is_connected()
        except Exception as e:
            log.error(f"MQTT status check error: {e}")
            currently_connected = False
        
        self.connected_to_broker = currently_connected
        
        # Log only changes
        if was_connected and not currently_connected:
            log.warning("MQTT lost")
        elif not was_connected and currently_connected:
            log.info("MQTT restored")
        
        # Reconnect if needed
        if not currently_connected and not self.shutdown_requested:
            try:
                # Clean disconnect first
                self.mqtt_client.client.loop_stop()
                self.mqtt_client.client.disconnect()
                time.sleep(0.5)
                
                # Attempt reconnection
                if self.mqtt_client.connect(timeout=5):
                    log.info("MQTT reconnected")
                    self.connected_to_broker = True
                else:
                    log.debug("MQTT reconnection failed, will retry next check")
            except Exception as e:
                log.debug(f"MQTT reconnection error: {e}")

def main():
    controller = None
    try:
        controller = MuseumController()
        controller.run()
    except Exception as e:
        log.error(f"Critical error: {e}")
        sys.exit(1)
    finally:
        if controller:
            controller.cleanup()

if __name__ == "__main__":
    main()