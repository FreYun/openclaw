#!/usr/bin/env bash
# 启动 Dashboard (端口 18888)
# 用法: ./start.sh

set -euo pipefail
cd "$(dirname "$0")"
PORT=18888

# 如果已经在运行，先停掉
OLD_PIDS=$(lsof -ti:${PORT} 2>/dev/null || true)
if [ -n "$OLD_PIDS" ]; then
    echo "停止旧进程 (PID: ${OLD_PIDS})"
    echo "$OLD_PIDS" | xargs kill 2>/dev/null || true
    sleep 2
fi

# 启动
echo "启动 Dashboard → :${PORT}"
nohup node server.js > /tmp/dashboard-${PORT}.log 2>&1 &
sleep 2

# 检查
if curl -sf http://localhost:${PORT}/ -o /dev/null --max-time 5; then
    echo "  OK  Dashboard :${PORT} (PID: $!)"
else
    echo "  FAIL Dashboard :${PORT}"
    tail -5 /tmp/dashboard-${PORT}.log
    exit 1
fi