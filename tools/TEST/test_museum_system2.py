
#!/usr/bin/env python3
"""
Raspberry Pi CPU and RAM Stress Test
- RAM: 500MB usage for 30 seconds
- CPU: 90% usage for 100 seconds
"""

import threading
import time
import psutil
import os
from datetime import datetime

def ram_stress_test(target_mb=500, duration=30):
    """
    Allocate and hold memory for specified duration
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting RAM test: {target_mb}MB for {duration} seconds")
    
    target_bytes = target_mb * 1024 * 1024
    memory_blocks = []
    chunk_size = 1024 * 1024  # 1MB chunks
    
    try:
        for i in range(target_mb):
            block = bytearray(chunk_size)
            for j in range(0, chunk_size, 1024):
                block[j:j+1024] = os.urandom(1024)
            memory_blocks.append(block)
            if (i + 1) % 50 == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] RAM allocated: {i + 1}MB")
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] RAM test: {target_mb}MB allocated successfully")
        time.sleep(duration)
        
    except MemoryError:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: Could not allocate full {target_mb}MB")
    
    finally:
        memory_blocks.clear()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] RAM test completed and memory released")

def cpu_stress_worker():
    """
    CPU intensive worker function
    """
    while True:
        for i in range(200000):  # Further increased for intensity
            _ = (i ** 3) * 3.14159 / 2.718 + sum([j ** 2 for j in range(200)])
        if threading.current_thread().stop_flag:
            break

def cpu_stress_test(target_percent=90, duration=100):
    """
    CPU stress test targeting specific utilization
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting CPU test: {target_percent}% for {duration} seconds")
    
    cpu_count = psutil.cpu_count()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Detected {cpu_count} CPU cores")
    
    num_threads = cpu_count * 2  # Overprovision threads to ensure high load
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting {num_threads} CPU stress threads")
    
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=cpu_stress_worker)
        thread.stop_flag = False
        thread.daemon = True
        threads.append(thread)
        thread.start()
    
    start_time = time.time()
    monitor_interval = 5
    
    try:
        while time.time() - start_time < duration:
            cpu_usage = psutil.cpu_percent(interval=1)
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed
            print(f"[{datetime.now().strftime('%H:%M:%S')}] CPU usage: {cpu_usage:.1f}% | "
                  f"Elapsed: {elapsed}s | Remaining: {remaining}s")
            time.sleep(monitor_interval)
    
    finally:
        for thread in threads:
            thread.stop_flag = True
        for thread in threads:
            thread.join(timeout=1)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] CPU test completed")

def monitor_system():
    """
    Display system information during tests
    """
    print("\n" + "="*60)
    print("RASPBERRY PI STRESS TEST")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"CPU cores: {psutil.cpu_count()}")
    print(f"Total RAM: {psutil.virtual_memory().total / (1024**3):.2f} GB")
    print(f"Available RAM: {psutil.virtual_memory().available / (1024**3):.2f} GB")
    print("="*60)

def main():
    """
    Main function to run both tests
    """
    monitor_system()
    
    try:
        print("\n--- PHASE 1: RAM STRESS TEST ---")
        ram_stress_test(target_mb=500, duration=30)
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Waiting 5 seconds before CPU test...")
        time.sleep(5)
        
        print("\n--- PHASE 2: CPU STRESS TEST ---")
        cpu_stress_test(target_percent=90, duration=100)
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] All stress tests completed successfully!")
        
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Test interrupted by user")
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Error during test: {e}")
    finally:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Final system status:")
        print(f"CPU usage: {psutil.cpu_percent(interval=1):.1f}%")
        print(f"RAM usage: {psutil.virtual_memory().percent:.1f}%")
        print(f"Available RAM: {psutil.virtual_memory().available / (1024**3):.2f} GB")

if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        print("Error: psutil module required. Install with: pip install psutil")
        exit(1)
    
    main()