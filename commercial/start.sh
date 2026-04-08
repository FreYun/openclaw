#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PORT=18900
APP_ENTRY="server/src/index.js"

is_commercial_pid() {
    local pid="$1"
    local args

    args=$(ps -p "$pid" -o args= 2>/dev/null || true)
    [ -n "$args" ] || return 1

    case "$args" in
        *"node ${APP_ENTRY}"*|*"node $(pwd)/${APP_ENTRY}"*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

OLD_PIDS=$(lsof -nP -tiTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$OLD_PIDS" ]; then
    while IFS= read -r pid; do
        [ -n "$pid" ] || continue

        if is_commercial_pid "$pid"; then
            kill "$pid" 2>/dev/null || true
        else
            echo "FAIL - port ${PORT} is occupied by non-commercial process (PID: ${pid})"
            ps -p "$pid" -o pid=,ppid=,comm=,args=
            exit 1
        fi
    done <<< "$OLD_PIDS"

    sleep 1
fi

nohup node server/src/index.js > /tmp/commercial-${PORT}.log 2>&1 &
sleep 2

if curl -sf http://localhost:${PORT}/api/health -o /dev/null --max-time 5; then
    echo "OK Commercial Order System :${PORT} (PID: $!)"
else
    echo "FAIL - check /tmp/commercial-${PORT}.log"
    exit 1
fi
