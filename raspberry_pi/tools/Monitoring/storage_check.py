#!/usr/bin/env python3
"""Raspberry Pi Storage / SD Card Monitor"""

import os
import shutil
import subprocess
import time
from pathlib import Path


CHECK_PATH = "/"            # hlavný filesystem
WRITE_TEST_PATH = Path.home()  # zápisový test v /home/admin
BIG_SCAN_PATH = "/home"     # kde hľadať veľké súbory
TOP_COUNT = 10


def bytes_to_gb(value):
    return value / (1024 ** 3)


def check_disk_usage(path="/"):
    """Check total, used and free storage."""
    total, used, free = shutil.disk_usage(path)
    used_percent = used / total * 100

    print("=" * 50)
    print("STORAGE USAGE")
    print("=" * 50)
    print(f"Path:       {path}")
    print(f"Total:      {bytes_to_gb(total):.2f} GB")
    print(f"Used:       {bytes_to_gb(used):.2f} GB")
    print(f"Free:       {bytes_to_gb(free):.2f} GB")
    print(f"Usage:      {used_percent:.1f} %")

    if used_percent >= 95:
        print("Status:     CRITICAL - disk skoro plný")
    elif used_percent >= 85:
        print("Status:     WARNING - málo voľného miesta")
    elif used_percent >= 75:
        print("Status:     OK, ale už sledovať")
    else:
        print("Status:     OK")

    print("=" * 50)
    print()


def check_write_test():
    """Test if storage is writable in user's home directory."""
    test_file = WRITE_TEST_PATH / "storage_write_test.tmp"

    print("=" * 50)
    print("WRITE TEST")
    print("=" * 50)
    print(f"Test path:  {test_file}")

    try:
        with open(test_file, "w") as f:
            f.write(f"storage test {time.time()}\n")
            f.flush()
            os.fsync(f.fileno())

        test_file.unlink()

        print("Writable:   YES")
        print("Status:     OK")

    except Exception as e:
        print("Writable:   NO")
        print("Status:     PROBLEM")
        print(f"Error:      {e}")

    print("=" * 50)
    print()


def show_mount_info():
    """Show mounted filesystem info for root path."""
    print("=" * 50)
    print("MOUNT INFO")
    print("=" * 50)

    try:
        result = subprocess.run(
            ["findmnt", "-T", CHECK_PATH],
            capture_output=True,
            text=True
        )

        if result.stdout.strip():
            print(result.stdout.strip())
        else:
            print("Unable to read mount info.")

        if result.stderr.strip():
            print(result.stderr.strip())

    except Exception as e:
        print(f"Error: {e}")

    print("=" * 50)
    print()


def show_big_directories(path="/"):
    """Show biggest first-level directories."""
    print("=" * 50)
    print(f"BIGGEST DIRECTORIES IN {path}")
    print("=" * 50)

    try:
        result = subprocess.run(
            ["du", "-x", "-m", "--max-depth=1", path],
            capture_output=True,
            text=True
        )

        entries = []

        for line in result.stdout.strip().splitlines():
            parts = line.split(maxsplit=1)

            if len(parts) == 2:
                try:
                    size_mb = int(parts[0])
                    folder = parts[1]
                    entries.append((size_mb, folder))
                except ValueError:
                    pass

        entries.sort(reverse=True)

        if entries:
            for size_mb, folder in entries[:TOP_COUNT]:
                if size_mb >= 1024:
                    size_text = f"{size_mb / 1024:.2f} GB"
                else:
                    size_text = f"{size_mb} MB"

                print(f"{size_text:>10}  {folder}")
        else:
            print("No directory data found.")

        if result.stderr.strip():
            print()
            print("Note: Some folders could not be read without sudo.")

    except Exception as e:
        print(f"Error: {e}")

    print("=" * 50)
    print()


def find_big_files(path="/home", top_count=10):
    """Find biggest files under selected path."""
    print("=" * 50)
    print(f"BIGGEST FILES IN {path}")
    print("=" * 50)

    files = []

    skip_dirs = {
        ".cache",
        ".npm",
        "__pycache__",
        ".git",
        ".vscode-server"
    }

    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for name in filenames:
            file_path = os.path.join(root, name)

            try:
                size = os.path.getsize(file_path)
                files.append((size, file_path))
            except Exception:
                pass

    files.sort(reverse=True)

    if files:
        for size, file_path in files[:top_count]:
            size_mb = size / (1024 ** 2)

            if size_mb >= 1024:
                size_text = f"{size_mb / 1024:.2f} GB"
            else:
                size_text = f"{size_mb:.1f} MB"

            print(f"{size_text:>10}  {file_path}")
    else:
        print("No files found or path could not be read.")

    print("=" * 50)
    print()


def check_dmesg_storage_errors():
    """Look for possible SD card / disk errors in kernel log."""
    print("=" * 50)
    print("STORAGE ERRORS FROM DMESG")
    print("=" * 50)

    try:
        result = subprocess.run(
            ["dmesg", "--color=never"],
            capture_output=True,
            text=True
        )

        suspicious_lines = []

        for line in result.stdout.splitlines():
            line_lower = line.lower()

            storage_related = any(keyword in line_lower for keyword in [
                "mmc",
                "ext4",
                "i/o error",
                "buffer i/o",
                "read-only",
                "filesystem",
                "blk_update_request"
            ])

            problem_related = any(keyword in line_lower for keyword in [
                "error",
                "fail",
                "read-only",
                "i/o",
                "corrupt"
            ])

            if storage_related and problem_related:
                suspicious_lines.append(line)

        if suspicious_lines:
            print("Possible storage problems found:")
            print()
            for line in suspicious_lines[-20:]:
                print(line)
        else:
            print("No obvious storage errors found in dmesg.")

        if result.stderr.strip():
            print()
            print("Note:")
            print(result.stderr.strip())
            print("Try running with sudo if dmesg is restricted.")

    except Exception as e:
        print(f"Error reading dmesg: {e}")

    print("=" * 50)
    print()


def main():
    check_disk_usage(CHECK_PATH)
    check_write_test()
    show_mount_info()
    show_big_directories("/")
    find_big_files(BIG_SCAN_PATH, TOP_COUNT)
    check_dmesg_storage_errors()


if __name__ == "__main__":
    main()