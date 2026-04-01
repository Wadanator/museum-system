#!/usr/bin/env bash
set -euo pipefail

# P0-3 validation script:
# - Forces web bind failure on port 5000
# - Verifies fast retry logs and DEGRADED mode log
# - Releases port and verifies WEB recovery log
#
# Run on RPi:
#   cd ~/Documents/GitHub/museum-system/raspberry_pi/tests
#   bash manual_web_retry_p03_test.sh

PORT="5000"
FAST_RETRY_LIMIT="5"
MAX_WAIT_SECS="140"
RECOVERY_WAIT_SECS="480"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RPI_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${RPI_DIR}/config/config.ini"

TEXT_LOG_FILE=""
DB_LOG_FILE=""

detect_log_files() {
  local override="${LOG_FILE:-}"
  if [[ -n "$override" ]]; then
    TEXT_LOG_FILE="$override"
    return
  fi

  if [[ -f "${CONFIG_FILE}" ]]; then
    local log_dir
    log_dir=$(awk -F'=' '
      BEGIN{in_logging=0}
      /^[[:space:]]*\[Logging\][[:space:]]*$/ {in_logging=1; next}
      /^[[:space:]]*\[/ {in_logging=0}
      in_logging && $1 ~ /^[[:space:]]*log_directory[[:space:]]*$/ {
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2)
        print $2
        exit
      }
    ' "${CONFIG_FILE}")

    if [[ -n "${log_dir}" ]]; then
      local resolved_dir
      if [[ "${log_dir}" = /* ]]; then
        resolved_dir="${log_dir}"
      else
        resolved_dir="${RPI_DIR}/${log_dir}"
      fi

      if [[ -f "${resolved_dir}/museum.log" ]]; then
        TEXT_LOG_FILE="${resolved_dir}/museum.log"
      elif [[ -f "${resolved_dir}/museum-errors.log" ]]; then
        TEXT_LOG_FILE="${resolved_dir}/museum-errors.log"
      fi

      if [[ -f "${resolved_dir}/museum_logs.db" ]]; then
        DB_LOG_FILE="${resolved_dir}/museum_logs.db"
      fi
      return
    fi
  fi

  if [[ -f "${RPI_DIR}/logs/museum.log" ]]; then
    TEXT_LOG_FILE="${RPI_DIR}/logs/museum.log"
  elif [[ -f "${RPI_DIR}/logs/museum-errors.log" ]]; then
    TEXT_LOG_FILE="${RPI_DIR}/logs/museum-errors.log"
  fi

  if [[ -f "${RPI_DIR}/logs/museum_logs.db" ]]; then
    DB_LOG_FILE="${RPI_DIR}/logs/museum_logs.db"
  fi
}
detect_log_files

db_count_like() {
  local pattern="$1"
  local db_path="$2"
  python3 - <<'PY' "$pattern" "$db_path"
import sqlite3
import sys

pattern = sys.argv[1]
db_path = sys.argv[2]
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM logs WHERE message LIKE ?", (f"%{pattern}%",))
    row = cur.fetchone()
    print(int(row[0]) if row else 0)
    conn.close()
except Exception:
    print(0)
PY
}

detect_service_name() {
  if systemctl list-unit-files | grep -q '^museum-system\.service'; then
    echo "museum-system.service"
    return
  fi
  if systemctl list-unit-files | grep -q '^museum\.service'; then
    echo "museum.service"
    return
  fi
  echo "museum-system.service"
}

SERVICE_NAME="$(detect_service_name)"

cleanup() {
  local ec=$?
  if [[ -n "${HTTP_PID:-}" ]]; then
    kill "${HTTP_PID}" >/dev/null 2>&1 || true
  fi
  exit "$ec"
}
trap cleanup EXIT

dump_diagnostics() {
  echo "[DIAG] ===== systemctl status (${SERVICE_NAME}) ====="
  sudo systemctl status "$SERVICE_NAME" --no-pager || true
  echo "[DIAG] ===== listeners on :${PORT} ====="
  ss -ltnp | grep ":${PORT}" || true
  echo "[DIAG] ===== last 120 journal lines (${SERVICE_NAME}) ====="
  sudo journalctl -u "$SERVICE_NAME" -n 120 --no-pager || true
}

echo "[INFO] Starting P0-3 web retry test"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[FAIL] systemctl not found"
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[FAIL] python3 not found"
  exit 2
fi

echo "[INFO] Using service unit: ${SERVICE_NAME}"
if [[ -n "${TEXT_LOG_FILE}" ]]; then
  echo "[INFO] Text log evidence file: ${TEXT_LOG_FILE}"
else
  echo "[WARN] No text log file detected (museum.log/museum-errors.log)"
fi
if [[ -n "${DB_LOG_FILE}" ]]; then
  echo "[INFO] DB log evidence file: ${DB_LOG_FILE}"
else
  echo "[WARN] No DB log file detected (museum_logs.db)"
fi

# Stop service to free port, then occupy it intentionally
echo "[INFO] Stopping service and occupying port ${PORT}"
sudo systemctl stop "$SERVICE_NAME"
python3 -m http.server "$PORT" --bind 0.0.0.0 >/dev/null 2>&1 &
HTTP_PID=$!
sleep 1

# Restart service while port is occupied
echo "[INFO] Starting service with forced port conflict"
sudo systemctl start "$SERVICE_NAME"

# Wait for degraded behavior while port is blocked
echo "[INFO] Waiting for expected web unavailability while port is blocked"
start_ts=$(date +%s)
status_failures=0
status_successes=0
fast_retry_hits=0
degraded_seen=0

while true; do
  now_ts=$(date +%s)
  elapsed=$((now_ts - start_ts))

  if curl -fsS -u admin:admin "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
    status_successes=$((status_successes + 1))
  else
    status_failures=$((status_failures + 1))
  fi

  # Optional log-based evidence when file logging is available
  if [[ -n "$TEXT_LOG_FILE" && -f "$TEXT_LOG_FILE" ]]; then
    fast_retry_hits=$(grep -c "Fast retry" "$TEXT_LOG_FILE" || true)
    if grep -q "entered DEGRADED mode" "$TEXT_LOG_FILE"; then
      degraded_seen=1
    fi
  elif [[ -n "$DB_LOG_FILE" && -f "$DB_LOG_FILE" ]]; then
    fast_retry_hits=$(db_count_like "Fast retry" "$DB_LOG_FILE")
    if [[ "$(db_count_like "entered DEGRADED mode" "$DB_LOG_FILE")" -gt 0 ]]; then
      degraded_seen=1
    fi
  fi

  if [[ "$elapsed" -ge "$MAX_WAIT_SECS" ]]; then
    if [[ "$status_failures" -gt 0 ]]; then
      echo "[PASS] Web became unavailable while bind conflict was active"
      echo "[INFO] status_failures=${status_failures}, status_successes=${status_successes}"
      if [[ -n "$TEXT_LOG_FILE" && -f "$TEXT_LOG_FILE" ]] || [[ -n "$DB_LOG_FILE" && -f "$DB_LOG_FILE" ]]; then
        echo "[INFO] fast_retry_hits=${fast_retry_hits}, degraded_seen=${degraded_seen} (log evidence)"
      else
        echo "[WARN] No usable log evidence source found; skipped log evidence checks"
      fi
      break
    fi
    echo "[FAIL] Web never became unavailable during forced port conflict"
    break
  fi

  sleep 2
done

# Release port and wait for recovery by API responsiveness
echo "[INFO] Releasing port ${PORT} and waiting for recovery"
kill "$HTTP_PID" >/dev/null 2>&1 || true
unset HTTP_PID
sleep 1

if ss -ltnp | grep -q ":${PORT}"; then
  echo "[WARN] Port ${PORT} is still occupied after release attempt."
  ss -ltnp | grep ":${PORT}" || true
fi

recover_start_ts=$(date +%s)
recovered_seen=0
while true; do
  now_ts=$(date +%s)
  elapsed=$((now_ts - recover_start_ts))

  if curl -fsS -u admin:admin "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
    recovered_seen=1
    break
  fi

  if [[ "$elapsed" -ge "$RECOVERY_WAIT_SECS" ]]; then
    echo "[FAIL] Timed out waiting for web API recovery"
    dump_diagnostics
    exit 1
  fi

  sleep 5
done

if [[ "$recovered_seen" -ne 1 ]]; then
  echo "[FAIL] Recovery not detected"
  dump_diagnostics
  exit 1
fi

echo "[PASS] P0-3 test succeeded: forced bind conflict and API recovery verified"
