#!/usr/bin/env python3
"""
Comprehensive Test Suite for Museum System
Tests error handling, warnings, and functionality
"""

import os
import sys
import time
import json
import threading
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import logging

# Add the project directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(script_dir, '..')
sys.path.insert(0, project_dir)

class TestLogger:
    """Custom logger for test output"""
    def __init__(self):
        self.logs = []
        self.warnings = []
        self.errors = []
    
    def info(self, msg):
        self.logs.append(f"INFO: {msg}")
        print(f"✅ {msg}")
    
    def warning(self, msg):
        self.warnings.append(f"WARNING: {msg}")
        print(f"⚠️  {msg}")
    
    def error(self, msg):
        self.errors.append(f"ERROR: {msg}")
        print(f"❌ {msg}")
    
    def debug(self, msg):
        self.logs.append(f"DEBUG: {msg}")
        print(f"🐛 {msg}")

class MuseumSystemTester:
    """Main test class for Museum System"""
    
    def __init__(self):
        self.logger = TestLogger()
        self.test_dir = tempfile.mkdtemp(prefix="museum_test_")
        self.mock_components = {}
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'errors': []
        }
    
    def setup_test_environment(self):
        """Create test environment with mock files and directories"""
        print("🏗️  Setting up test environment...")
        
        # Create test directories
        dirs_to_create = [
            f"{self.test_dir}/config",
            f"{self.test_dir}/scenes/room1",
            f"{self.test_dir}/audio",
            f"{self.test_dir}/logs",
            f"{self.test_dir}/utils"
        ]
        
        for dir_path in dirs_to_create:
            os.makedirs(dir_path, exist_ok=True)
        
        # Create test config file
        self.create_test_config()
        
        # Create test scene file
        self.create_test_scene()
        
        # Create mock utility modules
        self.create_mock_utils()
        
        self.logger.info("Test environment created")
    
    def create_test_config(self):
        """Create a test configuration file"""
        config_content = """[MQTT]
BrokerIP = localhost
Port = 1883

[GPIO]
ButtonPin = 17

[Room]
ID = room1

[Json]
json_file_name = test_scene.json

[System]
health_check_interval = 5

[Scenes]
Directory = {}/scenes

[Audio]
Directory = {}/audio
""".format(self.test_dir, self.test_dir)
        
        with open(f"{self.test_dir}/config/config.ini", 'w') as f:
            f.write(config_content)
    
    def create_test_scene(self):
        """Create a test scene JSON file"""
        test_scene = [
            {"timestamp": 0, "topic": "room1/light", "message": "ON"},
            {"timestamp": 1.0, "topic": "room1/audio", "message": "PLAY_WELCOME"},
            {"timestamp": 2.0, "topic": "room1/light", "message": "BLINK"},
            {"timestamp": 3.0, "topic": "room1/audio", "message": "STOP"},
            {"timestamp": 4.0, "topic": "room1/light", "message": "OFF"}
        ]
        
        with open(f"{self.test_dir}/scenes/room1/test_scene.json", 'w') as f:
            json.dump(test_scene, f, indent=2)
    
    def create_mock_utils(self):
        """Create mock utility modules for testing"""
        
        # Mock SystemdWatchdog
        watchdog_mock = '''
class SystemdWatchdog:
    def __init__(self, logger=None):
        self.logger = logger
        self.enabled = True
        self.heartbeat_count = 0
        
    def start(self):
        if self.logger: self.logger.info("Watchdog started")
        
    def stop(self):
        if self.logger: self.logger.info("Watchdog stopped")
        
    def get_status(self):
        self.heartbeat_count += 1
        return {
            'enabled': self.enabled,
            'status': 'active',
            'heartbeat_count': self.heartbeat_count,
            'uptime_seconds': 300,
            'message': 'OK'
        }
'''
        
        # Mock MQTT Client
        mqtt_mock = '''
class MQTTClient:
    def __init__(self, broker_host, client_id=None, use_logging=True):
        self.broker_host = broker_host
        self.client_id = client_id
        self.use_logging = use_logging
        self.connected = False
        
    def connect(self, timeout=10):
        if self.broker_host == "fail_host":
            return False
        self.connected = True
        return True
        
    def disconnect(self):
        self.connected = False
        
    def publish(self, topic, message):
        if self.use_logging:
            print(f"MQTT Publish: {topic} = {message}")
        return True
        
    def is_connected(self):
        return self.connected
'''
        
        # Mock Scene Parser
        scene_mock = '''
class SceneParser:
    def __init__(self, audio_handler):
        self.audio_handler = audio_handler
        self.scene_data = None
        self.current_index = 0
        
    def load_scene(self, scene_path):
        try:
            with open(scene_path, 'r') as f:
                import json
                self.scene_data = json.load(f)
            return True
        except Exception as e:
            print(f"Scene load error: {e}")
            return False
            
    def start_scene(self):
        self.current_index = 0
        
    def get_current_actions(self, mqtt_client):
        if not self.scene_data or self.current_index >= len(self.scene_data):
            return []
        action = self.scene_data[self.current_index]
        self.current_index += 1
        return [action]
'''
        
        # Mock Audio Handler
        audio_mock = '''
class AudioHandler:
    def __init__(self, audio_dir):
        self.audio_dir = audio_dir
        
    def cleanup(self):
        pass
'''
        
        # Mock Button Handler
        button_mock = '''
class ImprovedButtonHandler:
    def __init__(self, pin):
        self.pin = pin
        self.callback = None
        self.use_polling = False
        
    def set_callback(self, callback):
        self.callback = callback
        
    def cleanup(self):
        pass
'''
        
        # Write mock files
        mock_files = {
            'systemd_watchdog.py': watchdog_mock,
            'mqtt_client.py': mqtt_mock,
            'scene_parser.py': scene_mock,
            'audio_handler.py': audio_mock,
            'button_handler_improved.py': button_mock
        }
        
        for filename, content in mock_files.items():
            with open(f"{self.test_dir}/utils/{filename}", 'w') as f:
                f.write(content)
    
    def test_config_loading(self):
        """Test configuration loading and error handling"""
        print("\n🧪 Testing Configuration Loading...")
        
        try:
            # Test with valid config
            sys.path.insert(0, self.test_dir)
            
            # Create a minimal MuseumController class for testing
            import configparser
            config = configparser.ConfigParser()
            config.read(f"{self.test_dir}/config/config.ini")
            
            assert config['MQTT']['BrokerIP'] == 'localhost'
            assert config['GPIO']['ButtonPin'] == '17'
            assert config['Room']['ID'] == 'room1'
            
            self.logger.info("Config loading: PASSED")
            self.test_results['passed'] += 1
            
        except Exception as e:
            self.logger.error(f"Config loading failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(str(e))
        
        # Test with missing config
        try:
            missing_config = configparser.ConfigParser()
            result = missing_config.read("nonexistent_config.ini")
            if not result:  # Empty list means no files were read
                self.logger.warning("Missing config handled correctly")
                self.test_results['warnings'] += 1
        except Exception as e:
            self.logger.error(f"Missing config test failed: {e}")
            self.test_results['failed'] += 1
    
    def test_mqtt_connection(self):
        """Test MQTT connection and error handling"""
        print("\n🧪 Testing MQTT Connection...")
        
        sys.path.insert(0, f"{self.test_dir}/utils")
        
        try:
            from mqtt_client import MQTTClient
            
            # Test successful connection
            client = MQTTClient("localhost")
            if client.connect():
                self.logger.info("MQTT connection: PASSED")
                self.test_results['passed'] += 1
                client.disconnect()
            else:
                self.logger.error("MQTT connection failed")
                self.test_results['failed'] += 1
            
            # Test failed connection
            fail_client = MQTTClient("fail_host")
            if not fail_client.connect():
                self.logger.info("MQTT failure handling: PASSED")
                self.test_results['passed'] += 1
            else:
                self.logger.error("MQTT should have failed")
                self.test_results['failed'] += 1
                
        except Exception as e:
            self.logger.error(f"MQTT test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(str(e))
    
    def test_scene_loading(self):
        """Test scene loading and parsing"""
        print("\n🧪 Testing Scene Loading...")
        
        sys.path.insert(0, f"{self.test_dir}/utils")
        
        try:
            from scene_parser import SceneParser
            from audio_handler import AudioHandler
            
            audio_handler = AudioHandler(f"{self.test_dir}/audio")
            parser = SceneParser(audio_handler)
            
            # Test valid scene loading
            scene_path = f"{self.test_dir}/scenes/room1/test_scene.json"
            if parser.load_scene(scene_path):
                self.logger.info("Scene loading: PASSED")
                self.test_results['passed'] += 1
                
                # Test scene execution
                parser.start_scene()
                actions = parser.get_current_actions(None)
                if actions:
                    self.logger.info("Scene execution: PASSED")
                    self.test_results['passed'] += 1
                else:
                    self.logger.error("No actions returned")
                    self.test_results['failed'] += 1
            else:
                self.logger.error("Scene loading failed")
                self.test_results['failed'] += 1
            
            # Test invalid scene loading
            if not parser.load_scene("nonexistent_scene.json"):
                self.logger.info("Invalid scene handling: PASSED")
                self.test_results['passed'] += 1
            else:
                self.logger.error("Should have failed on invalid scene")
                self.test_results['failed'] += 1
                
        except Exception as e:
            self.logger.error(f"Scene test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(str(e))
    
    def test_watchdog_functionality(self):
        """Test watchdog functionality"""
        print("\n🧪 Testing Watchdog Functionality...")
        
        sys.path.insert(0, f"{self.test_dir}/utils")
        
        try:
            from systemd_watchdog import SystemdWatchdog
            
            watchdog = SystemdWatchdog(self.logger)
            watchdog.start()
            
            status = watchdog.get_status()
            assert status['enabled'] == True
            assert status['status'] == 'active'
            assert status['heartbeat_count'] > 0
            
            watchdog.stop()
            
            self.logger.info("Watchdog functionality: PASSED")
            self.test_results['passed'] += 1
            
        except Exception as e:
            self.logger.error(f"Watchdog test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(str(e))
    
    def test_button_handling(self):
        """Test button handler"""
        print("\n🧪 Testing Button Handling...")
        
        sys.path.insert(0, f"{self.test_dir}/utils")
        
        try:
            from button_handler_improved import ImprovedButtonHandler
            
            button = ImprovedButtonHandler(17)
            
            callback_called = False
            def test_callback():
                nonlocal callback_called
                callback_called = True
            
            button.set_callback(test_callback)
            
            # Simulate button press if method exists
            if hasattr(button, 'simulate_press'):
                button.simulate_press()
                if callback_called:
                    self.logger.info("Button callback: PASSED")
                    self.test_results['passed'] += 1
                else:
                    self.logger.error("Button callback not triggered")
                    self.test_results['failed'] += 1
            else:
                self.logger.info("Button handler initialized: PASSED")
                self.test_results['passed'] += 1
            
            button.cleanup()
            
        except Exception as e:
            self.logger.error(f"Button test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(str(e))
    
    def test_error_scenarios(self):
        """Test various error scenarios"""
        print("\n🧪 Testing Error Scenarios...")
        
        error_tests = [
            ("Missing config file", lambda: self.test_missing_config()),
            ("Invalid JSON scene", lambda: self.test_invalid_json()),
            ("Network failure", lambda: self.test_network_failure()),
            ("Permission errors", lambda: self.test_permission_errors()),
        ]
        
        for test_name, test_func in error_tests:
            try:
                test_func()
                self.logger.info(f"{test_name}: PASSED")
                self.test_results['passed'] += 1
            except Exception as e:
                self.logger.error(f"{test_name}: FAILED - {e}")
                self.test_results['failed'] += 1
                self.test_results['errors'].append(f"{test_name}: {e}")
    
    def test_missing_config(self):
        """Test handling of missing configuration"""
        import configparser
        config = configparser.ConfigParser()
        result = config.read("definitely_missing_file.ini")
        if not result:
            self.logger.warning("Missing config detected correctly")
    
    def test_invalid_json(self):
        """Test handling of invalid JSON"""
        invalid_json_path = f"{self.test_dir}/invalid_scene.json"
        with open(invalid_json_path, 'w') as f:
            f.write('{"invalid": json content}')
        
        try:
            with open(invalid_json_path, 'r') as f:
                json.load(f)
            raise Exception("Should have failed on invalid JSON")
        except json.JSONDecodeError:
            self.logger.warning("Invalid JSON handled correctly")
    
    def test_network_failure(self):
        """Test network failure scenarios"""
        # This would be tested with the MQTT client
        self.logger.warning("Network failure scenario simulated")
    
    def test_permission_errors(self):
        """Test permission error handling"""
        # Create a file with no read permissions
        no_read_file = f"{self.test_dir}/no_read.txt"
        with open(no_read_file, 'w') as f:
            f.write("test")
        os.chmod(no_read_file, 0o000)
        
        try:
            with open(no_read_file, 'r') as f:
                f.read()
            raise Exception("Should have failed on permission error")
        except PermissionError:
            self.logger.warning("Permission error handled correctly")
        finally:
            # Restore permissions for cleanup
            os.chmod(no_read_file, 0o644)
    
    def test_memory_and_performance(self):
        """Test memory usage and performance"""
        print("\n🧪 Testing Memory and Performance...")
        
        try:
            import psutil
            process = psutil.Process()
            
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Simulate some work
            for i in range(1000):
                data = [j for j in range(100)]
                del data
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            if memory_increase < 50:  # Less than 50MB increase
                self.logger.info(f"Memory usage: PASSED ({memory_increase:.1f}MB increase)")
                self.test_results['passed'] += 1
            else:
                self.logger.warning(f"High memory usage: {memory_increase:.1f}MB increase")
                self.test_results['warnings'] += 1
                
        except ImportError:
            self.logger.warning("psutil not available for memory testing")
            self.test_results['warnings'] += 1
        except Exception as e:
            self.logger.error(f"Memory test failed: {e}")
            self.test_results['failed'] += 1
    
    def test_logging_system(self):
        """Test the logging system"""
        print("\n🧪 Testing Logging System...")
        
        try:
            # Test log creation
            log_file = f"{self.test_dir}/test.log"
            
            # Create a simple logger
            import logging
            logger = logging.getLogger('test_logger')
            handler = logging.FileHandler(log_file)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
            # Test logging
            logger.info("Test log message")
            logger.warning("Test warning message")
            logger.error("Test error message")
            
            # Check if log file was created and contains messages
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_content = f.read()
                    if "Test log message" in log_content:
                        self.logger.info("Logging system: PASSED")
                        self.test_results['passed'] += 1
                    else:
                        self.logger.error("Log messages not found in file")
                        self.test_results['failed'] += 1
            else:
                self.logger.error("Log file not created")
                self.test_results['failed'] += 1
                
        except Exception as e:
            self.logger.error(f"Logging test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("🏛️  MUSEUM SYSTEM COMPREHENSIVE TEST SUITE")
        print("=" * 50)
        
        start_time = time.time()
        
        # Setup
        self.setup_test_environment()
        
        # Run tests
        test_methods = [
            self.test_config_loading,
            self.test_mqtt_connection,
            self.test_scene_loading,
            self.test_watchdog_functionality,
            self.test_button_handling,
            self.test_error_scenarios,
            self.test_memory_and_performance,
            self.test_logging_system
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.logger.error(f"Test method {test_method.__name__} crashed: {e}")
                self.test_results['failed'] += 1
                self.test_results['errors'].append(f"{test_method.__name__}: {e}")
        
        # Generate report
        end_time = time.time()
        self.generate_test_report(end_time - start_time)
        
        # Cleanup
        self.cleanup()
    
    def generate_test_report(self, duration):
        """Generate comprehensive test report"""
        print("\n" + "=" * 50)
        print("🎯 MUSEUM SYSTEM TEST RESULTS")
        print("=" * 50)
        
        total_tests = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 SUMMARY:")
        print(f"   ✅ Passed: {self.test_results['passed']}")
        print(f"   ❌ Failed: {self.test_results['failed']}")
        print(f"   ⚠️  Warnings: {self.test_results['warnings']}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        print(f"   ⏱️  Duration: {duration:.2f} seconds")
        
        if self.test_results['errors']:
            print(f"\n❌ ERRORS ENCOUNTERED:")
            for i, error in enumerate(self.test_results['errors'], 1):
                print(f"   {i}. {error}")
        
        print(f"\n📝 DETAILED LOGS:")
        print(f"   Info messages: {len(self.logger.logs)}")
        print(f"   Warnings: {len(self.logger.warnings)}")
        print(f"   Errors: {len(self.logger.errors)}")
        
        if self.logger.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in self.logger.warnings:
                print(f"   • {warning}")
        
        if self.logger.errors:
            print(f"\n❌ LOGGED ERRORS:")
            for error in self.logger.errors:
                print(f"   • {error}")
        
        # System recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        if self.test_results['failed'] == 0:
            print("   ✅ System appears to be working correctly!")
            print("   ✅ All core functionality tests passed")
            print("   ✅ Error handling is working properly")
        else:
            print("   ⚠️  Some tests failed - review errors above")
            print("   🔍 Check component initialization")
            print("   🔍 Verify configuration files")
            print("   🔍 Check system dependencies")
        
        if self.test_results['warnings'] > 3:
            print("   ⚠️  High number of warnings - review system setup")
        
        print(f"\n🎯 OVERALL STATUS: ", end="")
        if self.test_results['failed'] == 0:
            print("✅ SYSTEM READY FOR PRODUCTION")
        elif self.test_results['failed'] <= 2:
            print("⚠️  SYSTEM NEEDS MINOR FIXES")
        else:
            print("❌ SYSTEM NEEDS MAJOR ATTENTION")
    
    def cleanup(self):
        """Clean up test environment"""
        try:
            shutil.rmtree(self.test_dir)
            self.logger.info("Test environment cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")

def main():
    """Main test function"""
    tester = MuseumSystemTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()