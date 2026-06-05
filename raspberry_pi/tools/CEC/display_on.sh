#!/bin/bash
set -u

TARGET="${1:-${CEC_TARGET:-0}}"
CEC_CLIENT="${CEC_CLIENT:-cec-client}"
CEC_TIMEOUT_SECONDS="${CEC_TIMEOUT_SECONDS:-5}"

if ! command -v "$CEC_CLIENT" >/dev/null 2>&1; then
    echo "[ERROR] cec-client not found."
    echo "Install it on Raspberry Pi with: sudo apt-get install -y cec-utils"
    exit 127
fi

echo "[INFO] Sending HDMI-CEC power ON to target: $TARGET"

if command -v timeout >/dev/null 2>&1; then
    printf 'on %s\n' "$TARGET" | timeout "${CEC_TIMEOUT_SECONDS}s" "$CEC_CLIENT" -s -d 1
else
    printf 'on %s\n' "$TARGET" | "$CEC_CLIENT" -s -d 1
fi

