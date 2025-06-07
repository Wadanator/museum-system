#!/usr/bin/env python3

import os, time, configparser, sys, logging, signal, threading
from datetime import datetime
from watchdog import subprocess

# Add current directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Clean logging setup
def setup_logging():
    class CleanFormatter(logging.Formatter):
        def format(self, record):
            timestamp = datetime.now().strftime('%H:%M:%S')
            level = record.levelname.ljust(7)
            return f"[{timestamp}] {level} {record.getMessage()}"
    
    logger = logging.getLogger('museum')
    logger.setLevel(logging.DEBUG)
    
    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CleanFormatter())
    logger.addHandler(console_handler)
    
    # Log files
    log_dir = os.path.expanduser("~/Documents/GitHub/museum-system/logs")
    os.makedirs(log_dir, exist_ok=True)
    
    for level, filename in [(logging.INFO, 'museum-info.log'), 
                           (logging.WARNING, 'museum-warnings.log'), 
                           (logging.ERROR, 'museum-errors.log')]:
        handler = logging.FileHandler(f"{log_dir}/{filename}")
        handler.setLevel(level)
        handler.setFormatter(CleanFormatter())
        logger.addHandler(handler)
    
    return logger

log = setup_logging()

# Import components
try:
    from utils.systemd_watchdog import SystemdWatchdog
    from utils.mqtt_client import MQTTClient
    from utils.scene_parser import SceneParser
    from utils.audio_handler import AudioHandler
    log.info("Core modules loaded")
except ImportError as e:
    log.error(f"Import failed: {e}")
    sys.exit(1)

# Button handler with fallback
try:
    from utils.button_handler_improved import ImprovedButtonHandler as ButtonHandler
    log.info("Button handler loaded")
except ImportError:
    log.warning("Using mock button")
    class MockButtonHandler:
        def __init__(self, pin):
            self.pin = pin
            self.callback = None
        def set_callback(self, callback): self.callback = callback
        def simulate_press(self): 
            if self.callback: self.callback()
        def cleanup(self): pass
    ButtonHandler = MockButtonHandler

class MuseumController:
    def __init__(self, config_file=None):
        # Config loading
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), "config", "config.ini")
        
        if not os.path.exists(config_file):
            log.error(f"Config missing: {config_file}")
            self.create_default_config(config_file)
        
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Config values
        broker_ip = self.config['MQTT']['BrokerIP']
        button_pin = int(self.config['GPIO']['ButtonPin'])
        self.room_id = self.config['Room']['ID']
        self.json_file_name = self.config['Json']['json_file_name']
        self.scenes_dir = "/home/admin/Documents/GitHub/museum-system/raspberry_pi/scenes"
        self.audio_dir = os.path.join(os.path.dirname(__file__), "audio")
        
        log.info(f"Room: {self.room_id}, MQTT: {broker_ip}, GPIO: {button_pin}")
        os.makedirs(self.scenes_dir, exist_ok=True)
        
        # Components init
        self.watchdog = SystemdWatchdog(logger=log)
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Init with error handling
        self.mqtt_client = self._safe_init(lambda: MQTTClient(broker_ip, client_id=f"rpi_room_{self.room_id}", use_logging=True), "MQTT")
        self.audio_handler = self._safe_init(lambda: AudioHandler(self.audio_dir), "Audio")
        self.scene_parser = self._safe_init(lambda: SceneParser(self.audio_handler), "Scene parser")
        self.button_handler = self._safe_init(lambda: ButtonHandler(button_pin), "Button")
        
        if self.button_handler:
            self.button_handler.set_callback(self.on_button_press)
        
        # State
        self.scene_running = False
        self.connected_to_broker = False
        self.last_heartbeat = time.time()
        self.health_check_interval = int(self.config['System'].get('health_check_interval', '30'))
    
    def _safe_init(self, init_func, name):
        try:
            return init_func()
        except Exception as e:
            log.error(f"{name} init failed: {e}")
            return None
    
    def _signal_handler(self, signum, frame):
        log.info(f"Signal {signum} received, shutting down...")
        self.shutdown_requested = True
    
    def create_default_config(self, config_file):
        config = configparser.ConfigParser()
        config['MQTT'] = {'BrokerIP': 'localhost', 'Port': '1883'}
        config['GPIO'] = {'ButtonPin': '17'}
        config['Room'] = {'ID': 'room1'}
        config['Scenes'] = {'Directory': '/home/admin/Documents/GitHub/museum-system/raspberry_pi/scenes'}
        config['Audio'] = {'Directory': 'audio'}
        
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as f:
            config.write(f)
        log.info(f"Default config created: {config_file}")
    
    def test_mqtt_connection(self):
        if not self.mqtt_client:
            log.error("MQTT client missing")
            return False
        
        broker_ip = self.config['MQTT']['BrokerIP']
        
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
    
    def send_ready_notification(self):
        try:
            os.system('systemd-notify READY=1')
            log.info("Systemd READY sent")
        except Exception as e:
            log.warning(f"Systemd notify failed: {e}")
    
    def perform_health_check(self):
        try:
            self.last_heartbeat = time.time()
            issues = []
            
            if not self.connected_to_broker: issues.append("MQTT down")
            if not self.mqtt_client: issues.append("MQTT missing")
            
            # Watchdog check
            ws = self.watchdog.get_status()
            if ws['enabled']:
                if ws['status'] == 'stalled':
                    issues.append(f"WD stalled: {ws['message']}")
                elif ws['status'] == 'degraded':
                    issues.append(f"WD degraded: {ws['message']}")
            
            # Memory check
            try:
                import psutil
                if psutil.virtual_memory().percent > 90:
                    issues.append(f"High mem")
            except ImportError:
                pass
            
            if issues:
                log.warning(f"Health: {len(issues)} issues: {', '.join(issues)}")
                return False
            else:
                if not hasattr(self, '_hc_count'): self._hc_count = 0
                self._hc_count += 1
                if self._hc_count % 10 == 0:
                    if ws['enabled']:
                        log.info(f"Health #{self._hc_count}: OK (WD: {ws['heartbeat_count']} beats)")
                    else:
                        log.info(f"Health #{self._hc_count}: OK")
                return True
                
        except Exception as e:
            log.error(f"Health check failed: {e}")
            return False
    
    def on_button_press(self):
        if self.scene_running:
            log.warning("Scene running, ignoring button")
            return
        log.info("Button pressed, starting scene")
        self.start_default_scene()
    
    def start_default_scene(self):
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
        import json
        
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
            
            time.sleep(0.1)
        
        log.info("Scene completed")
        self.scene_running = False
    
    def run_interactive_mode(self):
        log.info("Interactive mode: 'b'=button, 's'=scene, 'status', 'watchdog', 'q'=quit")
        
        while not self.shutdown_requested:
            try:
                cmd = input("\n> ").strip().lower()
                
                if cmd in ['q', 'quit', 'exit']: break
                elif cmd in ['b', 'button']: self.on_button_press()
                elif cmd in ['s', 'scene']: self.start_default_scene()
                elif cmd == 'status':
                    ws = self.watchdog.get_status()
                    log.info(f"MQTT: {self.connected_to_broker}, Scene: {self.scene_running}, Room: {self.room_id}")
                    log.info(f"Watchdog: {'enabled' if ws['enabled'] else 'disabled'}")
                elif cmd == 'watchdog':
                    ws = self.watchdog.get_status()
                    if ws['enabled']:
                        log.info(f"WD: {ws['status']}, Beats: {ws['heartbeat_count']}, Uptime: {ws['uptime_seconds']/60:.1f}m")
                elif cmd == 'health':
                    healthy = self.perform_health_check()
                    log.info(f"Health: {'OK' if healthy else 'ISSUES'}")
                elif cmd == 'help':
                    log.info("Commands: button/b, scene/s, status, watchdog, health, quit/q")
                else:
                    log.warning("Unknown cmd. Type 'help'")
                    
            except (KeyboardInterrupt, EOFError): break
    
    def run(self):
        log.info("Starting Enhanced Museum Controller")
        
        self.watchdog.start()
        
        if not self.test_mqtt_connection():
            if self.shutdown_requested: return
            log.error("CRITICAL: No MQTT connection")
            sys.exit(1)
        
        self.send_ready_notification()
        log.info(f"System ready - {self.room_id} operational")
        
        last_health = time.time()
        last_mqtt = time.time()
        
        # Check for polling mode
        use_polling = hasattr(self.button_handler, 'use_polling') and self.button_handler.use_polling
        
        try:
            while not self.shutdown_requested:
                current_time = time.time()
                
                # Health checks
                if current_time - last_health > self.health_check_interval:
                    self.perform_health_check()
                    last_health = current_time
                
                # MQTT checks
                if current_time - last_mqtt > 15:
                    self.check_mqtt_status()
                    last_mqtt = current_time
                
                # Button polling if needed
                if use_polling and self.button_handler:
                    self.button_handler.check_button_polling()
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            if not self.shutdown_requested:
                log.info("Interactive mode")
                self.run_interactive_mode()
        
        self.cleanup()
    
    def cleanup(self):
        log.info("Cleanup started")
        self.watchdog.stop()
        
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
            if self.mqtt_client.connect(timeout=5):
                log.info("MQTT reconnected")
                self.connected_to_broker = True

def main():
    log.info("Enhanced Museum System Starting")
    log.info("="*40)
    
    controller = None
    try:
        controller = MuseumController()
        controller.run()
    except Exception as e:
        log.error(f"Critical error: {e}")
        if controller: controller.cleanup()
        sys.exit(1)
    finally:
        if controller: controller.cleanup()

if __name__ == "__main__":
    main()