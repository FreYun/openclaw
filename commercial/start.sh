#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PORT=18900
APP_ENTRY="server/src/index.js"

# paths.js 默认指向 ./deps (sync-deps.sh 生成)，本机无 deps 时显式指回 .openclaw
export OPENCLAW_DIR="${OPENCLAW_DIR:-/home/rooot/.openclaw}"

# --- Auto-rebuild client if sources are newer than dist -----------------------
# Server serves client/dist/ as static assets. If the .vue / .js / .css sources
# under client/src/ (or config files) are newer than dist/index.html, rebuild
# before (re)starting the server. Prevents the classic "restarted server but
# browser still loads old bundle" footgun.
#
# Build runs BEFORE killing the old server — if build fails, old server keeps
# running so we don't end up with nothing live.
NEEDS_BUILD=0
if [ ! -f client/dist/index.html ]; then
    echo "[client] dist/ missing, building..."
    NEEDS_BUILD=1
elif find \
        client/src \
        client/index.html \
        client/package.json \
        client/vite.config.js client/vite.config.ts \
        -newer client/dist/index.html \
        -print -quit 2>/dev/null | grep -q .; then
    echo "[client] source changed since last build, rebuilding..."
    NEEDS_BUILD=1
fi

if [ "$NEEDS_BUILD" = "1" ]; then
    if [ ! -d client/node_modules ]; then
        echo "[client] node_modules missing, running npm install first..."
        (cd client && npm install) || { echo "FAIL - client npm install failed"; exit 1; }
    fi
    (cd client && npm run build) || { echo "FAIL - client build failed"; exit 1; }
    echo "[client] build OK"
fi
# -----------------------------------------------------------------------------

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
