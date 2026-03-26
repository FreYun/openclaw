#!/bin/bash
# research-gateway 启动脚本
# 用法: ./run.sh [start|stop|restart|status|log]

GATEWAY_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="/home/rooot/.openclaw/.venv"
PORT=18080
PIDFILE="/tmp/research-gateway.pid"
LOGFILE="/tmp/research-gateway.log"

start() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "research-gateway 已在运行 (PID $(cat "$PIDFILE"))"
        return 1
    fi

    echo "启动 research-gateway (port=$PORT)..."
    cd "$GATEWAY_DIR"
    GATEWAY_PORT=$PORT "$VENV/bin/python" -m research_gateway.server \
        > "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    sleep 2

    if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "启动成功 (PID $(cat "$PIDFILE"))"
        # 验证健康
        curl -s "http://localhost:$PORT/health" --connect-timeout 3 -m 5 | grep -q healthy && echo "健康检查通过" || echo "警告: 健康检查未通过，查看日志 $LOGFILE"
    else
        echo "启动失败，查看日志: $LOGFILE"
        cat "$LOGFILE" | tail -20
        return 1
    fi
}

stop() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "停止 research-gateway (PID $PID)..."
            kill "$PID"
            sleep 1
            kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
            echo "已停止"
        else
            echo "进程不存在"
        fi
        rm -f "$PIDFILE"
    else
        echo "research-gateway 未在运行"
    fi
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "research-gateway 运行中 (PID $(cat "$PIDFILE")), port=$PORT"
    else
        echo "research-gateway 未运行"
    fi
}

case "${1:-start}" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 1; start ;;
    status)  status ;;
    log)     tail -f "$LOGFILE" ;;
    *)       echo "用法: $0 {start|stop|restart|status|log}" ;;
esac
