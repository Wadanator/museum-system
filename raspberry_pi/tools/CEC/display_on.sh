#!/bin/bash
set -u

TARGET="${1:-${CEC_TARGET:-0}}"
CEC_CLIENT="${CEC_CLIENT:-cec-client}"
CEC_TIMEOUT_SECONDS="${CEC_TIMEOUT_SECONDS:-4}"

if ! command -v "$CEC_CLIENT" >/dev/null 2>&1; then
    echo "[ERROR] cec-client sa nenašiel."
    exit 127
fi

echo "[INFO] Posielam HDMI-CEC power ON na cieľ: $TARGET"

send_cec_on() {
    local port="$1"
    # Výstup z cec-client presmerujeme do /dev/null, aby nezapĺňal logy chybami z nezapojených portov
    if command -v timeout >/dev/null 2>&1; then
        printf 'on %s\n' "$TARGET" | timeout "${CEC_TIMEOUT_SECONDS}s" "$CEC_CLIENT" -s -d 1 $port >/dev/null 2>&1
    else
        printf 'on %s\n' "$TARGET" | "$CEC_CLIENT" -s -d 1 $port >/dev/null 2>&1
    fi
}

# Pridanie znaku "&" na konci zabezpečí, že sa príkazy spustia súčasne (paralelne)
pids=()
if [ -c "/dev/cec0" ]; then
    send_cec_on "/dev/cec0" &
    pids+=("$!")
fi

if [ -c "/dev/cec1" ]; then
    send_cec_on "/dev/cec1" &
    pids+=("$!")
fi

if [ ! -c "/dev/cec0" ] && [ ! -c "/dev/cec1" ]; then
    send_cec_on "" &
    pids+=("$!")
fi

# Počkáme, kým sa všetky paralelné procesy (zapnutie na všetkých portoch) dokončia
# Jeden dostupny adapter staci; chybu vratime, ak zlyhali vsetky.
success=false
for pid in "${pids[@]}"; do
    if wait "$pid"; then
        success=true
    fi
done
if [ "$success" = true ]; then
    echo "[INFO] Príkaz odoslaný."
else
    echo "[ERROR] CEC prikaz zlyhal na vsetkych adapteroch." >&2
    exit 1
fi
