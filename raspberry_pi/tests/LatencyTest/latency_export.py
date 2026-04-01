#!/usr/bin/env python3
"""
latency_export.py - Extract latency data from museum_logs.db and save to CSV.
Zero dependencies - Python standard library only.
"""

import sqlite3
import csv
import re
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH    = SCRIPT_DIR / "logs" / "museum_logs.db"
OUT_RAW    = SCRIPT_DIR / "latency_raw.csv"
OUT_STATS  = SCRIPT_DIR / "latency_stats.csv"

PATTERN = re.compile(r"Feedback OK: (.+?) \((\d+\.\d+)s\)")


def read_data(db_path):
    if not db_path.exists():
        print(f"[ERR] Database not found: {db_path}")
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    cur.execute("""
        SELECT timestamp, module, message
        FROM   logs
        WHERE  message LIKE 'Feedback OK:%'
        ORDER  BY timestamp
    """)
    rows = cur.fetchall()
    conn.close()
    records = []
    for ts, module, msg in rows:
        m = PATTERN.search(msg)
        if not m:
            continue
        topic      = m.group(1).strip()
        latency_ms = round(float(m.group(2)) * 1000, 1)
        device     = topic.split("/")[1] if topic.count("/") >= 1 else topic
        records.append({"timestamp": ts, "module": module, "topic": topic,
                        "device": device, "latency_ms": latency_ms})
    return records


def stats_for(values):
    if not values:
        return {}
    s = sorted(values)
    n = len(s)
    return {
        "count":  n,
        "avg":    round(sum(s) / n, 1),
        "min":    round(s[0], 1),
        "max":    round(s[-1], 1),
        "median": round(s[n // 2], 1),
        "p95":    round(s[int(n * 0.95)], 1),
        "p99":    round(s[min(int(n * 0.99), n - 1)], 1),
    }


def write_raw(records, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Timestamp", "Module", "Topic", "Device", "Latency_ms"])
        for r in records:
            w.writerow([r["timestamp"], r["module"], r["topic"],
                        r["device"], r["latency_ms"]])
    print(f"  Raw data   -> {path}")


def write_stats(records, path):
    all_lat = [r["latency_ms"] for r in records]
    s = stats_for(all_lat)
    devices = {}
    for r in records:
        devices.setdefault(r["device"], []).append(r["latency_ms"])

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)

        w.writerow(["=== OVERALL SUMMARY ==="])
        w.writerow(["Metric", "Value (ms)"])
        for k, label in [("count", "Measurement count"), ("avg", "Average"),
                          ("median", "Median"), ("min", "Min"), ("max", "Max"),
                          ("p95","P95"),("p99","P99")]:
            w.writerow([label, s.get(k)])
        w.writerow([])

        w.writerow(["=== PER DEVICE ==="])
        w.writerow(["Device", "Count", "Avg (ms)", "Min", "Max", "Median", "P95"])
        for dev, vals in sorted(devices.items()):
            ds = stats_for(vals)
            w.writerow([dev, ds["count"], ds["avg"], ds["min"],
                        ds["max"], ds["median"], ds["p95"]])
        w.writerow([])

        w.writerow(["=== DISTRIBUTION ==="])
        w.writerow(["Range", "Count", "Share %"])
        total = len(all_lat)
        for label, lo, hi in [("0-100 ms", 0, 100), ("100-200 ms", 100, 200),
                               ("200-300 ms", 200, 300), ("300-500 ms", 300, 500),
                               ("500-800 ms", 500, 800), ("800-1000 ms", 800, 1000),
                               ("1000+ ms", 1000, 9e9)]:
            cnt = sum(1 for v in all_lat if lo <= v < hi)
            w.writerow([label, cnt, round(cnt / total * 100, 1) if total else 0])
        w.writerow([])

        w.writerow(["=== INFO ==="])
        w.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Database file", str(DB_PATH)])
        w.writerow(["First measurement", records[0]["timestamp"] if records else "-"])
        w.writerow(["Last measurement", records[-1]["timestamp"] if records else "-"])

    print(f"  Statistics -> {path}")


def main():
    print(f"Reading database: {DB_PATH}")
    records = read_data(DB_PATH)
    if not records:
        print("No 'Feedback OK' entries found in database.")
        sys.exit(0)

    all_lat = [r["latency_ms"] for r in records]
    s = stats_for(all_lat)
    print(f"Found {len(records)} measurements.")
    print(f"{'-' * 38}")
    print(f"  Average : {s['avg']} ms  |  Median: {s['median']} ms")
    print(f"  Min     : {s['min']} ms  |  Max   : {s['max']} ms")
    print(f"  P95     : {s['p95']} ms  |  P99   : {s['p99']} ms")
    print(f"{'-' * 38}\n")

    write_raw(records, OUT_RAW)
    write_stats(records, OUT_STATS)

    print("\nDownload to PC:")
    print(f"  scp admin@<ip>:{OUT_RAW} .")
    print(f"  scp admin@<ip>:{OUT_STATS} .")

if __name__ == "__main__":
    main()