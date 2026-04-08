#!/usr/bin/env bash
# 启动 Dashboard (端口 18888)
# 用法: ./start.sh

set -euo pipefail
cd "$(dirname "$0")"
PORT=18888
PIDFILE="/tmp/dashboard-${PORT}.pid"

# 如果已经在运行，先停掉脚本自己记录的旧进程
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE" 2>/dev/null || true)
    if [ -n "${OLD_PID}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "停止旧进程 (PID: ${OLD_PID})"
        kill "$OLD_PID" 2>/dev/null || true
        sleep 2
    fi
    rm -f "$PIDFILE"
fi

# 端口已被其他进程监听时直接失败（只检查 LISTEN，忽略残留的 ESTABLISHED 连接）
if lsof -ti:${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
    echo "端口 ${PORT} 已被其他进程占用，未启动 Dashboard"
    lsof -i :${PORT} -sTCP:LISTEN || true
    exit 1
fi

# 启动
echo "启动 Dashboard → :${PORT}"
nohup node server.js > /tmp/dashboard-${PORT}.log 2>&1 &
echo $! > "$PIDFILE"
sleep 2

# 检查
if curl -sf http://localhost:${PORT}/ -o /dev/null --max-time 5; then
    echo "  OK  Dashboard :${PORT} (PID: $!)"
else
    echo "  FAIL Dashboard :${PORT}"
    tail -5 /tmp/dashboard-${PORT}.log
    rm -f "$PIDFILE"
    exit 1
fi
