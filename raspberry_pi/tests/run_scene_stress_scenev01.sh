#!/usr/bin/env bash
set -euo pipefail

# Preset launcher for manual_scene_service_stress.py
# Edit values here once, then run this script repeatedly.
BASE_URL="http://127.0.0.1:5000"
USER_NAME="admin"
PASSWORD="admin"
SCENE_NAME="SceneV01.json"
CYCLES="50"
DELAY="0.15"
TIMEOUT="8"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "${SCRIPT_DIR}/manual_scene_service_stress.py" \
  --base-url "${BASE_URL}" \
  --user "${USER_NAME}" \
  --password "${PASSWORD}" \
  --scene "${SCENE_NAME}" \
  --mode "start-stop" \
  --cycles "${CYCLES}" \
  --delay "${DELAY}" \
  --timeout "${TIMEOUT}" \
  --stop-at-end \
  "$@"
