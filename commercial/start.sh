#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PORT=18900

OLD_PID=$(lsof -ti:${PORT} 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
    kill "$OLD_PID" 2>/dev/null || true
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
