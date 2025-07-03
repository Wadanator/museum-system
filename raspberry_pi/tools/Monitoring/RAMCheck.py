#!/usr/bin/env python3
import psutil

def check_ram_usage():
    # Get memory information
    memory = psutil.virtual_memory()
    
    # Convert bytes to GB for easier reading
    total_gb = memory.total / (1024**3)
    used_gb = memory.used / (1024**3)
    available_gb = memory.available / (1024**3)
    
    print("=" * 40)
    print("RAM Usage on Raspberry Pi 4")
    print("=" * 40)
    print(f"Total RAM:     {total_gb:.2f} GB")
    print(f"Used RAM:      {used_gb:.2f} GB")
    print(f"Available RAM: {available_gb:.2f} GB")
    print(f"Usage:         {memory.percent:.1f}%")
    print("=" * 40)

def get_top_processes(limit=10):
    # Get all processes with their memory usage
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            # Get memory usage in MB
            memory_mb = proc.info['memory_info'].rss / (1024 * 1024)
            processes.append({
                'pid': proc.info['pid'],
                'name': proc.info['name'],
                'memory_mb': memory_mb
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Skip processes that are no longer running or can't be accessed
            continue
    
    # Sort by memory usage (highest first)
    processes.sort(key=lambda x: x['memory_mb'], reverse=True)
    
    print(f"\nTop {limit} Memory-Using Processes:")
    print("-" * 50)
    print(f"{'PID':<8} {'Memory (MB)':<12} {'Process Name'}")
    print("-" * 50)
    
    for i, proc in enumerate(processes[:limit]):
        print(f"{proc['pid']:<8} {proc['memory_mb']:<12.1f} {proc['name']}")
    
    print("-" * 50)

if __name__ == "__main__":
    check_ram_usage()
    get_top_processes()