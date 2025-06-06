#!/usr/bin/env python3

import os
import time
import configparser
import sys

# Add the current directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from utils.mqtt_client import MQTTClient
    from utils.scene_parser import SceneParser
    from utils.audio_handler import AudioHandler
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the raspberry_pi directory")
    sys.exit(1)

# Import improved button handler or fall back to simulation
try:
    from utils.button_handler_improved import ImprovedButtonHandler as ButtonHandler
    print("✅ Using improved button handler")
except ImportError:
    print("⚠️  Button handler not available, using simulation")
    
    class MockButtonHandler:
        def __init__(self, pin):
            self.pin = pin
            self.callback = None
            print(f"Mock button handler created for GPIO {pin}")
        
        def set_callback(self, callback):
            self.callback = callback
        
        def simulate_press(self):
            if self.callback:
                print("🔘 Simulated button press")
                self.callback()
        
        def cleanup(self):
            pass
    
    ButtonHandler = MockButtonHandler

class FixedMuseumController:
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), "config", "config.ini")
        
        if not os.path.exists(config_file):
            print(f"❌ Config file not found: {config_file}")
            print("Creating default config...")
            self.create_default_config(config_file)
        
        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Get configuration values
        broker_ip = self.config['MQTT']['BrokerIP']
        button_pin = int(self.config['GPIO']['ButtonPin'])
        self.room_id = self.config['Room']['ID']
        # Use absolute path for scenes directory
        self.scenes_dir = "/home/admin/Documents/GitHub/museum-system/raspberry_pi/scenes"
        self.audio_dir = os.path.join(os.path.dirname(__file__), "audio")
        
        print(f"🏛️  Museum Controller for Room: {self.room_id}")
        print(f"📡 MQTT Broker: {broker_ip}")
        print(f"🔘 Button Pin: GPIO {button_pin}")
        print(f"🎵 Audio Directory: {self.audio_dir}")
        print(f"📂 Scenes Directory: {self.scenes_dir}")
        
        # Ensure scenes directory exists
        os.makedirs(self.scenes_dir, exist_ok=True)
        
        # Initialize components with error handling
        try:
            self.mqtt_client = MQTTClient(broker_ip, client_id=f"rpi_room_{self.room_id}", use_logging=True)
        except Exception as e:
            print(f"❌ MQTT client initialization failed: {e}")
            self.mqtt_client = None
        
        try:
            self.audio_handler = AudioHandler(self.audio_dir)
        except Exception as e:
            print(f"❌ Audio handler initialization failed: {e}")
            self.audio_handler = None
        
        try:
            self.scene_parser = SceneParser(self.audio_handler)
        except Exception as e:
            print(f"❌ Scene parser initialization failed: {e}")
            self.scene_parser = None
        
        try:
            self.button_handler = ButtonHandler(button_pin)
            self.button_handler.set_callback(self.on_button_press)
        except Exception as e:
            print(f"❌ Button handler initialization failed: {e}")
            self.button_handler = None
        
        # State
        self.scene_running = False
        self.connected_to_broker = False
    
    def create_default_config(self, config_file):
        config = configparser.ConfigParser()
        config['MQTT'] = {
            'BrokerIP': 'localhost',
            'Port': '1883'
        }
        config['GPIO'] = {
            'ButtonPin': '17'
        }
        config['Room'] = {
            'ID': 'room1'
        }
        config['Scenes'] = {
            'Directory': '/home/admin/Documents/GitHub/museum-system/raspberry_pi/scenes'
        }
        config['Audio'] = {
            'Directory': 'audio'
        }
        
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, 'w') as f:
            config.write(f)
        
        print(f"✅ Created default config: {config_file}")
    
    def test_mqtt_connection(self):
        if not self.mqtt_client:
            return False
        
        # Try current broker
        if self.mqtt_client.connect(timeout=3):
            self.connected_to_broker = True
            print("✅ Connected to MQTT broker")
            return True
        
        print("❌ Failed to connect to configured broker")
        
        # Try localhost as fallback
        if self.config['MQTT']['BrokerIP'] != 'localhost':
            print("🔄 Trying localhost as fallback...")
            self.mqtt_client.broker_host = 'localhost'
            if self.mqtt_client.connect(timeout=3):
                self.connected_to_broker = True
                print("✅ Connected to localhost broker")
                return True
        
        print("❌ No MQTT broker accessible")
        return False
    
    def on_button_press(self):
        if self.scene_running:
            print("⚠️  Scene already running, ignoring button press")
            return
        
        print("🔘 Button pressed! Starting default scene...")
        self.start_default_scene()
    
    def start_default_scene(self):
        scene_path = os.path.join(self.scenes_dir, self.room_id, "intro.json")
        
        if not os.path.exists(scene_path):
            print(f"❌ Scene file not found: {scene_path}")
            self.create_default_scene(scene_path)
        
        if not self.scene_parser:
            print("❌ Scene parser not available")
            return
        
        print(f"🎬 Loading scene: {scene_path}")
        if self.scene_parser.load_scene(scene_path):
            self.scene_running = True
            self.scene_parser.start_scene()
            self.run_scene()
        else:
            print("❌ Failed to load scene")
    
    def create_default_scene(self, scene_path):
        import json
        
        default_scene = [
            {"timestamp": 0, "topic": f"{self.room_id}/light", "message": "ON"},
            {"timestamp": 2.0, "topic": f"{self.room_id}/audio", "message": "PLAY_WELCOME"},
            {"timestamp": 5.0, "topic": f"{self.room_id}/light", "message": "BLINK"},
            {"timestamp": 8.0, "topic": f"{self.room_id}/audio", "message": "STOP"},
            {"timestamp": 10.0, "topic": f"{self.room_id}/light", "message": "OFF"}
        ]
        
        # Ensure the room-specific directory exists
        os.makedirs(os.path.dirname(scene_path), exist_ok=True)
        
        with open(scene_path, 'w') as f:
            json.dump(default_scene, f, indent=2)
        
        print(f"✅ Created default scene: {scene_path}")
    
    def run_scene(self):
        if not self.scene_parser.scene_data:
            print("❌ No scene data to run")
            return
        
        start_time = time.time()
        max_time = max(action["timestamp"] for action in self.scene_parser.scene_data)
        
        print(f"🎬 Playing scene, duration: {max_time} seconds")
        
        while time.time() - start_time <= max_time + 1:
            actions = self.scene_parser.get_current_actions(self.mqtt_client if self.connected_to_broker else None)
            
            if actions:
                current_time = time.time() - start_time
                for action in actions:
                    print(f"[{current_time:.1f}s] 🎭 {action['topic']} = {action['message']}")
                    
                    # If MQTT is not connected, just simulate the action
                    if not self.connected_to_broker:
                        print(f"    (Simulated - no MQTT connection)")
            
            time.sleep(0.1)
        
        print("✅ Scene completed")
        self.scene_running = False
    
    def run_interactive_mode(self):
        print("\n🎮 Interactive Mode")
        print("Commands:")
        print("  'b' or 'button' - Simulate button press")
        print("  's' or 'scene' - Start default scene")
        print("  'q' or 'quit' - Exit")
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                
                if cmd in ['q', 'quit', 'exit']:
                    break
                elif cmd in ['b', 'button']:
                    self.on_button_press()
                elif cmd in ['s', 'scene']:
                    self.start_default_scene()
                elif cmd == 'status':
                    print(f"MQTT Connected: {self.connected_to_broker}")
                    print(f"Scene Running: {self.scene_running}")
                    print(f"Room ID: {self.room_id}")
                elif cmd == 'help':
                    print("Available commands: button, scene, status, quit")
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
    
    def run(self):
        print("🚀 Starting Museum Controller...")
        
        # Test MQTT connection
        mqtt_ok = self.test_mqtt_connection()
        
        if mqtt_ok:
            print("✅ System ready with MQTT")
        else:
            print("⚠️  System ready without MQTT (simulation mode)")
        
        print(f"🏛️  Museum controller for {self.room_id} is running")
        
        # Check if we have a working button handler
        if hasattr(self.button_handler, 'use_polling') and self.button_handler.use_polling:
            print("🔘 Using button polling mode")
            print("💡 Press Ctrl+C to enter interactive mode")
            
            try:
                while True:
                    if self.button_handler:
                        self.button_handler.check_button_polling()
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n🎮 Switching to interactive mode...")
                self.run_interactive_mode()
        else:
            print("🔘 Using button interrupt mode")
            print("💡 Press the button or Ctrl+C for interactive mode")
            
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n🎮 Switching to interactive mode...")
                self.run_interactive_mode()
        
        # Cleanup
        if self.button_handler:
            self.button_handler.cleanup()
        if self.mqtt_client and self.connected_to_broker:
            self.mqtt_client.disconnect()
        if self.audio_handler:
            self.audio_handler.cleanup()
        
        print("👋 Museum controller stopped")

def main():
    print("🏛️  Fixed Museum Automation System")
    print("=" * 40)
    
    try:
        controller = FixedMuseumController()
        controller.run()
    except Exception as e:
        print(f"❌ Critical error: {e}")
        print("💡 Try running the diagnostic script first")

if __name__ == "__main__":
    main()