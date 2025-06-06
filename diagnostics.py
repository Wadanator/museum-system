#!/usr/bin/env python3
"""
Museum System Diagnostics & Fix Script
This script will help diagnose and fix common issues with the museum automation system.
"""

import socket
import subprocess
import os
import sys
import configparser
import time

def check_mqtt_broker(host, port=1883):
    """Check if MQTT broker is accessible"""
    print(f"🔍 Checking MQTT broker at {host}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ MQTT broker is accessible at {host}:{port}")
            return True
        else:
            print(f"❌ MQTT broker is NOT accessible at {host}:{port}")
            return False
    except Exception as e:
        print(f"❌ Error checking MQTT broker: {e}")
        return False

def check_local_broker():
    """Check if local MQTT broker is running"""
    print("🔍 Checking for local MQTT broker...")
    
    try:
        # Check if mosquitto is running
        result = subprocess.run(['pgrep', 'mosquitto'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Local mosquitto broker is running")
            return True
        else:
            print("❌ Local mosquitto broker is not running")
            return False
    except Exception as e:
        print(f"❌ Error checking local broker: {e}")
        return False

def start_local_broker():
    """Try to start local MQTT broker"""
    print("🚀 Attempting to start local MQTT broker...")
    
    try:
        # Try to start mosquitto
        subprocess.run(['sudo', 'systemctl', 'start', 'mosquitto'], check=True)
        time.sleep(2)
        
        if check_local_broker():
            print("✅ Successfully started local MQTT broker")
            return True
        else:
            print("❌ Failed to start local MQTT broker")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting broker: {e}")
        print("💡 Try: sudo apt install mosquitto mosquitto-clients")
        return False

def check_network_interfaces():
    """Check available network interfaces and IPs"""
    print("🔍 Checking network interfaces...")
    
    try:
        # Get all network interfaces
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        interfaces = {}
        current_interface = None
        
        for line in lines:
            if ': ' in line and 'state UP' in line:
                # Extract interface name
                parts = line.split(': ')
                if len(parts) >= 2:
                    current_interface = parts[1].split('@')[0]
                    interfaces[current_interface] = []
            elif 'inet ' in line and current_interface:
                # Extract IP address
                ip_part = line.strip().split('inet ')[1].split('/')[0]
                interfaces[current_interface].append(ip_part)
        
        print("📡 Active network interfaces:")
        for interface, ips in interfaces.items():
            if ips:
                print(f"  {interface}: {', '.join(ips)}")
        
        return interfaces
    except Exception as e:
        print(f"❌ Error checking network interfaces: {e}")
        return {}

def suggest_broker_ip(interfaces):
    """Suggest a suitable broker IP based on network interfaces"""
    print("💡 Broker IP suggestions:")
    
    # Check localhost first
    if check_mqtt_broker('localhost'):
        print("  ✅ Use: localhost (recommended)")
        return 'localhost'
    
    # Check each interface IP
    for interface, ips in interfaces.items():
        for ip in ips:
            if ip != '127.0.0.1' and not ip.startswith('169.254'):
                if check_mqtt_broker(ip):
                    print(f"  ✅ Use: {ip} (interface: {interface})")
                    return ip
    
    print("  ❌ No accessible MQTT broker found")
    return None

def update_config_file(new_broker_ip):
    """Update the configuration file with new broker IP"""
    config_file = "raspberry_pi/config/config.ini"
    
    if not os.path.exists(config_file):
        print(f"❌ Config file not found: {config_file}")
        return False
    
    try:
        config = configparser.ConfigParser()
        config.read(config_file)
        
        old_ip = config['MQTT']['BrokerIP']
        config['MQTT']['BrokerIP'] = new_broker_ip
        
        with open(config_file, 'w') as f:
            config.write(f)
            
        print(f"✅ Updated broker IP: {old_ip} → {new_broker_ip}")
        return True
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False

def create_fixed_button_handler():
    """Create an improved button handler that works better with different systems"""
    
    button_handler_code = '''#!/usr/bin/env python3
import time
import atexit

# Try to import RPi.GPIO, fall back to mock if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("Warning: RPi.GPIO not available, using mock GPIO")
    GPIO_AVAILABLE = False
    
    # Mock GPIO for testing
    class MockGPIO:
        BCM = "BCM"
        IN = "IN"
        HIGH = 1
        LOW = 0
        PUD_UP = "PUD_UP"
        FALLING = "FALLING"
        
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode, pull_up_down=None): pass
        @staticmethod
        def input(pin): return MockGPIO.HIGH
        @staticmethod
        def add_event_detect(pin, edge, callback=None, bouncetime=None): pass
        @staticmethod
        def remove_event_detect(pin): pass
        @staticmethod
        def cleanup(): pass
    
    GPIO = MockGPIO()

class ImprovedButtonHandler:
    def __init__(self, pin, debounce_time=300):
        self.pin = pin
        self.debounce_time = debounce_time
        self.last_press_time = 0
        self.callback = None
        self.use_polling = False
        self.running = True
        
        if not GPIO_AVAILABLE:
            print(f"Warning: GPIO not available, button on pin {pin} will be simulated")
            self.use_polling = True
            return
        
        try:
            # Clean setup
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Try edge detection first
            try:
                GPIO.remove_event_detect(pin)  # Remove any existing detection
            except:
                pass
            
            time.sleep(0.1)  # Small delay
            
            GPIO.add_event_detect(pin, GPIO.FALLING, 
                                 callback=self._button_callback, 
                                 bouncetime=debounce_time)
            print(f"✅ Button handler setup with edge detection on GPIO {pin}")
            
        except Exception as e:
            print(f"⚠️  Edge detection failed ({e}), using polling method")
            self.use_polling = True
            self._last_state = GPIO.HIGH
        
        atexit.register(self.cleanup)
    
    def _button_callback(self, channel):
        current_time = time.time() * 1000
        if (current_time - self.last_press_time) > self.debounce_time:
            self.last_press_time = current_time
            if self.callback:
                print(f"🔘 Button pressed on GPIO {self.pin}")
                self.callback()
    
    def check_button_polling(self):
        """Call this method in your main loop if using polling"""
        if not self.use_polling or not GPIO_AVAILABLE:
            return
            
        try:
            current_state = GPIO.input(self.pin)
            
            # Button pressed (transition from HIGH to LOW)
            if hasattr(self, '_last_state') and self._last_state == GPIO.HIGH and current_state == GPIO.LOW:
                current_time = time.time() * 1000
                if (current_time - self.last_press_time) > self.debounce_time:
                    self.last_press_time = current_time
                    if self.callback:
                        print(f"🔘 Button pressed on GPIO {self.pin} (polling)")
                        self.callback()
            
            self._last_state = current_state
        except Exception as e:
            print(f"Error in button polling: {e}")
    
    def set_callback(self, callback_function):
        self.callback = callback_function
    
    def cleanup(self):
        self.running = False
        if GPIO_AVAILABLE:
            try:
                GPIO.remove_event_detect(self.pin)
                GPIO.cleanup()
            except:
                pass

# Test function
if __name__ == "__main__":
    def on_button_press():
        print("🎉 Button press detected!")
    
    button = ImprovedButtonHandler(17)
    button.set_callback(on_button_press)
    
    print("Testing button handler...")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            if button.use_polling:
                button.check_button_polling()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\\nTest completed")
    finally:
        button.cleanup()
'''
    
    # Write the improved button handler
    button_file = "raspberry_pi/utils/button_handler_improved.py"
    with open(button_file, 'w') as f:
        f.write(button_handler_code)
    
    os.chmod(button_file, 0o755)
    print(f"✅ Created improved button handler: {button_file}")

def main():
    """Main diagnostic function"""
    print("🔧 Museum System Diagnostics & Fix Tool")
    print("=" * 50)
    
    # Check current config
    config_file = "raspberry_pi/config/config.ini"
    current_broker = "Unknown"
    
    if os.path.exists(config_file):
        try:
            config = configparser.ConfigParser()
            config.read(config_file)
            current_broker = config['MQTT']['BrokerIP']
            print(f"📋 Current broker IP in config: {current_broker}")
        except:
            print("⚠️  Could not read current config")
    
    # Check network interfaces
    interfaces = check_network_interfaces()
    
    # Check if current broker is accessible
    broker_accessible = check_mqtt_broker(current_broker)
    
    if not broker_accessible:
        print("\\n🔧 FIXING BROKER CONNECTION...")
        
        # Try to start local broker
        if not check_local_broker():
            start_local_broker()
        
        # Suggest new broker IP
        suggested_ip = suggest_broker_ip(interfaces)
        
        if suggested_ip and suggested_ip != current_broker:
            response = input(f"\\n❓ Update config to use {suggested_ip}? (y/n): ")
            if response.lower() == 'y':
                update_config_file(suggested_ip)
    
    # Create improved button handler
    print("\\n🔧 CREATING IMPROVED BUTTON HANDLER...")
    create_fixed_button_handler()
    
    print("\\n✨ DIAGNOSTIC COMPLETE!")
    print("\\n📝 Next steps:")
    print("1. Test the improved button handler:")
    print("   python raspberry_pi/utils/button_handler_improved.py")
    print("\\n2. Test MQTT connection:")
    print("   python raspberry_pi/utils/mqtt_client.py")
    print("\\n3. Run the main system:")
    print("   python raspberry_pi/main.py")
    
    # Quick MQTT test
    print("\\n🧪 Quick MQTT test...")
    try:
        from raspberry_pi.utils.mqtt_client import MQTTClient
        
        config = configparser.ConfigParser()
        config.read(config_file)
        broker_ip = config['MQTT']['BrokerIP']
        
        client = MQTTClient(broker_ip, "diagnostic_test", use_logging=True)
        if client.connect():
            print("✅ MQTT connection test PASSED!")
            client.publish("test/diagnostic", "System diagnostic complete")
            client.disconnect()
        else:
            print("❌ MQTT connection test FAILED!")
    except Exception as e:
        print(f"⚠️  Could not run MQTT test: {e}")

if __name__ == "__main__":
    main()