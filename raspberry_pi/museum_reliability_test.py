#!/usr/bin/env python3

import os, time, configparser, sys, json, subprocess, signal
from datetime import datetime, timedelta
import threading
from collections import defaultdict

class MuseumReliabilityTest:
    def __init__(self):
        self.running = False
        self.start_time = None
        self.test_duration = 48 * 60 * 60  # 48 hours in seconds
        self.button_interval = 60  # 60 seconds
        
        # Load config
        config_file = os.path.join(os.path.dirname(__file__), "config", "config.ini")
        if not os.path.exists(config_file):
            print(f"ERROR: Config file not found: {config_file}")
            sys.exit(1)
            
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        self.button_pin = int(self.config['GPIO']['ButtonPin'])
        self.room_id = self.config['Room']['ID']
        
        # Log file paths
        self.log_dir = os.path.expanduser("~/Documents/GitHub/museum-system/logs")
        self.log_files = {
            'info': f"{self.log_dir}/museum-info.log",
            'warnings': f"{self.log_dir}/museum-warnings.log", 
            'errors': f"{self.log_dir}/museum-errors.log"
        }
        
        # Test statistics
        self.stats = {
            'button_presses': 0,
            'scenes_started': 0,
            'scenes_completed': 0,
            'errors': 0,
            'warnings': 0,
            'mqtt_disconnections': 0,
            'mqtt_reconnections': 0,
            'health_checks': 0,
            'memory_warnings': 0,
            'service_restarts': 0,
            'max_memory_mb': 0,
            'max_cpu_percent': 0,
            'log_entries': defaultdict(int)
        }
        
        # GPIO setup
        self.gpio_available = self.setup_gpio()
        
        # File positions for log monitoring
        self.log_positions = {}
        self.init_log_positions()
        
        # Shutdown handling
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def setup_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.button_pin, GPIO.OUT)
            GPIO.output(self.button_pin, GPIO.HIGH)  # Default high
            print(f"GPIO initialized - Button pin: {self.button_pin}")
            return True
        except ImportError:
            print("WARNING: RPi.GPIO not available, using simulation mode")
            return False
        except Exception as e:
            print(f"ERROR: GPIO setup failed: {e}")
            return False
    
    def init_log_positions(self):
        """Initialize log file positions to current end"""
        for name, path in self.log_files.items():
            if os.path.exists(path):
                with open(path, 'r') as f:
                    f.seek(0, 2)  # Seek to end
                    self.log_positions[name] = f.tell()
            else:
                self.log_positions[name] = 0
    
    def signal_handler(self, signum, frame):
        print(f"\nReceived signal {signum}, stopping test...")
        self.running = False
    
    def simulate_button_press(self):
        """Simulate button press via GPIO"""
        if self.gpio_available:
            try:
                import RPi.GPIO as GPIO
                # Simulate button press (pull low then high)
                GPIO.output(self.button_pin, GPIO.LOW)
                time.sleep(0.1)
                GPIO.output(self.button_pin, GPIO.HIGH)
                self.stats['button_presses'] += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Button press #{self.stats['button_presses']} simulated")
                return True
            except Exception as e:
                print(f"ERROR: Button simulation failed: {e}")
                return False
        else:
            # Simulation mode
            self.stats['button_presses'] += 1
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Button press #{self.stats['button_presses']} simulated (mock)")
            return True
    
    def monitor_logs(self):
        """Monitor log files for new entries"""
        for name, path in self.log_files.items():
            if not os.path.exists(path):
                continue
                
            try:
                with open(path, 'r') as f:
                    f.seek(self.log_positions[name])
                    new_lines = f.readlines()
                    self.log_positions[name] = f.tell()
                    
                    for line in new_lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        self.stats['log_entries'][name] += 1
                        
                        # Parse specific events
                        if 'Button pressed, starting scene' in line:
                            self.stats['scenes_started'] += 1
                        elif 'Scene completed' in line:
                            self.stats['scenes_completed'] += 1
                        elif 'MQTT lost' in line:
                            self.stats['mqtt_disconnections'] += 1
                        elif 'MQTT restored' in line or 'MQTT reconnected' in line:
                            self.stats['mqtt_reconnections'] += 1
                        elif 'Health #' in line and 'OK' in line:
                            self.stats['health_checks'] += 1
                        elif 'High mem' in line:
                            self.stats['memory_warnings'] += 1
                        
                        if name == 'errors':
                            self.stats['errors'] += 1
                        elif name == 'warnings':
                            self.stats['warnings'] += 1
                            
            except Exception as e:
                print(f"ERROR: Log monitoring failed for {name}: {e}")
    
    def get_system_stats(self):
        """Get current system resource usage"""
        try:
            # Memory usage
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                total_kb = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
                available_kb = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1])
                used_mb = (total_kb - available_kb) / 1024
                
            # CPU usage (simple approach)
            cpu_cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | sed 's/%us,//'"
            try:
                cpu_result = subprocess.run(cpu_cmd, shell=True, capture_output=True, text=True, timeout=5)
                cpu_percent = float(cpu_result.stdout.strip()) if cpu_result.stdout.strip() else 0
            except:
                cpu_percent = 0
            
            # Update maximums
            self.stats['max_memory_mb'] = max(self.stats['max_memory_mb'], used_mb)
            self.stats['max_cpu_percent'] = max(self.stats['max_cpu_percent'], cpu_percent)
            
            return used_mb, cpu_percent
            
        except Exception as e:
            print(f"ERROR: System stats failed: {e}")
            return 0, 0
    
    def check_service_status(self):
        """Check if museum service is running"""
        try:
            result = subprocess.run(['systemctl', 'is-active', 'museum-system'], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout.strip() == 'active'
        except:
            return False
    
    def button_press_thread(self):
        """Thread for simulating button presses"""
        next_press = time.time() + self.button_interval
        
        while self.running:
            if time.time() >= next_press:
                self.simulate_button_press()
                next_press = time.time() + self.button_interval
            
            time.sleep(1)
    
    def monitoring_thread(self):
        """Thread for monitoring system and logs"""
        last_stats_print = time.time()
        stats_interval = 300  # Print stats every 5 minutes
        
        while self.running:
            # Monitor logs
            self.monitor_logs()
            
            # Get system stats
            memory_mb, cpu_percent = self.get_system_stats()
            
            # Check service status
            service_active = self.check_service_status()
            if not service_active:
                self.stats['service_restarts'] += 1
                print(f"WARNING: Museum service not active at {datetime.now()}")
            
            # Print periodic stats
            if time.time() - last_stats_print > stats_interval:
                elapsed = time.time() - self.start_time
                remaining = self.test_duration - elapsed
                
                print(f"\n--- Stats Update ({elapsed/3600:.1f}h elapsed, {remaining/3600:.1f}h remaining) ---")
                print(f"Button presses: {self.stats['button_presses']}")
                print(f"Scenes: {self.stats['scenes_started']} started, {self.stats['scenes_completed']} completed")
                print(f"Errors: {self.stats['errors']}, Warnings: {self.stats['warnings']}")
                print(f"MQTT: {self.stats['mqtt_disconnections']} disconnects, {self.stats['mqtt_reconnections']} reconnects")
                print(f"Memory: {memory_mb:.1f}MB current, {self.stats['max_memory_mb']:.1f}MB max")
                print(f"Service active: {service_active}")
                print("---")
                
                last_stats_print = time.time()
            
            time.sleep(10)  # Monitor every 10 seconds
    
    def generate_final_report(self):
        """Generate final test report"""
        elapsed = time.time() - self.start_time
        
        report = f"""
=== 48-Hour Museum System Reliability Test Report ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Test Duration: {elapsed/3600:.2f} hours
Room ID: {self.room_id}
Button Pin: {self.button_pin}

=== BUTTON & SCENE STATISTICS ===
Total Button Presses: {self.stats['button_presses']}
Expected Button Presses: {int(elapsed / self.button_interval)}
Scenes Started: {self.stats['scenes_started']}
Scenes Completed: {self.stats['scenes_completed']}
Scene Success Rate: {(self.stats['scenes_completed']/max(1,self.stats['scenes_started'])*100):.1f}%

=== ERROR & WARNING STATISTICS ===
Total Errors: {self.stats['errors']}
Total Warnings: {self.stats['warnings']}
Memory Warnings: {self.stats['memory_warnings']}
Service Restarts: {self.stats['service_restarts']}

=== CONNECTIVITY STATISTICS ===
MQTT Disconnections: {self.stats['mqtt_disconnections']}
MQTT Reconnections: {self.stats['mqtt_reconnections']}
Health Checks Passed: {self.stats['health_checks']}

=== SYSTEM RESOURCE STATISTICS ===
Peak Memory Usage: {self.stats['max_memory_mb']:.1f} MB
Peak CPU Usage: {self.stats['max_cpu_percent']:.1f}%

=== LOG ACTIVITY ===
Info Log Entries: {self.stats['log_entries']['info']}
Warning Log Entries: {self.stats['log_entries']['warnings']}
Error Log Entries: {self.stats['log_entries']['errors']}

=== RELIABILITY ASSESSMENT ===
"""
        
        # Calculate reliability score
        reliability_score = 100
        
        if self.stats['errors'] > 0:
            reliability_score -= min(20, self.stats['errors'] * 2)
        
        if self.stats['service_restarts'] > 0:
            reliability_score -= min(30, self.stats['service_restarts'] * 10)
        
        if self.stats['scenes_started'] > 0:
            scene_failure_rate = (self.stats['scenes_started'] - self.stats['scenes_completed']) / self.stats['scenes_started']
            reliability_score -= scene_failure_rate * 25
        
        if self.stats['mqtt_disconnections'] > 5:
            reliability_score -= min(15, (self.stats['mqtt_disconnections'] - 5) * 2)
        
        reliability_score = max(0, reliability_score)
        
        report += f"Overall Reliability Score: {reliability_score:.1f}/100\n"
        
        if reliability_score >= 95:
            report += "STATUS: EXCELLENT - System is highly reliable\n"
        elif reliability_score >= 85:
            report += "STATUS: GOOD - System is reliable with minor issues\n"
        elif reliability_score >= 70:
            report += "STATUS: FAIR - System has some reliability concerns\n"
        else:
            report += "STATUS: POOR - System has significant reliability issues\n"
        
        report += "\n=== RECOMMENDATIONS ===\n"
        
        if self.stats['errors'] > 10:
            report += "- High error count detected, review error logs\n"
        
        if self.stats['service_restarts'] > 0:
            report += "- Service restarts detected, investigate service stability\n"
        
        if self.stats['mqtt_disconnections'] > 10:
            report += "- Frequent MQTT disconnections, check network stability\n"
        
        if self.stats['memory_warnings'] > 0:
            report += "- Memory warnings detected, monitor for memory leaks\n"
        
        if self.stats['scenes_started'] != self.stats['scenes_completed']:
            report += "- Some scenes did not complete, investigate scene execution\n"
        
        print(report)
        
        # Save report
        report_file = f"museum_reliability_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_file}")
    
    def run(self):
        """Run the 48-hour test"""
        print("=== Museum System 48-Hour Reliability Test ===")
        print(f"Room ID: {self.room_id}")
        print(f"Button Pin: {self.button_pin}")
        print(f"Test Duration: {self.test_duration/3600} hours")
        print(f"Button Press Interval: {self.button_interval} seconds")
        print(f"GPIO Available: {self.gpio_available}")
        print("=" * 50)
        
        self.running = True
        self.start_time = time.time()
        
        # Start threads
        button_thread = threading.Thread(target=self.button_press_thread, daemon=True)
        monitor_thread = threading.Thread(target=self.monitoring_thread, daemon=True)
        
        button_thread.start()
        monitor_thread.start()
        
        print("Test started! Press Ctrl+C to stop early.")
        
        try:
            # Main loop
            while self.running and (time.time() - self.start_time) < self.test_duration:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        
        self.running = False
        print("\nTest completed, generating report...")
        
        # Wait for threads to finish
        time.sleep(2)
        
        # Cleanup GPIO
        if self.gpio_available:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
                print("GPIO cleaned up")
            except:
                pass
        
        # Generate final report
        self.generate_final_report()

def main():
    if os.geteuid() != 0:
        print("WARNING: Not running as root, GPIO access may fail")
    
    test = MuseumReliabilityTest()
    test.run()

if __name__ == "__main__":
    main()