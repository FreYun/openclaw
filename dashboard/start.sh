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

# ── XHS Live View: Xvfb :99 + x11vnc + websockify/noVNC on :6081 ──
# 仅在未运行时启动，避免踩中"不要重启现有服务"的铁律
ensure_xhs_live_stack() {
    # Xvfb :99 (headed Chrome 的虚拟显示)
    # 幂等检测：用 X socket 文件存在性，避免 pgrep -f 误匹配包含 "Xvfb :99" 字符串的其他进程
    if ! [ -S /tmp/.X11-unix/X99 ]; then
        # 清理上次 SIGKILL 可能残留的 lock
        rm -f /tmp/.X99-lock 2>/dev/null || true
        echo "启动 Xvfb :99"
        setsid nohup Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp \
            </dev/null >/tmp/xvfb-99.log 2>&1 &
        disown || true
        # 等 socket 出现（最多 3 秒）
        for i in 1 2 3; do
            [ -S /tmp/.X11-unix/X99 ] && break
            sleep 1
        done
    fi

    # x11vnc: 把 :99 桥接到 localhost:5999
    if ! ss -tlnp 2>/dev/null | grep -q '127.0.0.1:5999'; then
        echo "启动 x11vnc → :5999 (display :99)"
        setsid nohup x11vnc -display :99 -rfbport 5999 -shared -forever -nopw -localhost \
            </dev/null >/tmp/x11vnc-xhs.log 2>&1 &
        disown || true
        sleep 1
    fi

    # websockify + noVNC: 对外暴露 :6081 (dashboard 前端写死用这个端口)
    if ! ss -tlnp 2>/dev/null | grep -q '0.0.0.0:6081'; then
        echo "启动 websockify/noVNC → :6081"
        setsid nohup websockify --web /usr/share/novnc/ 6081 localhost:5999 \
            </dev/null >/tmp/websockify-xhs.log 2>&1 &
        disown || true
        sleep 1
    fi

    # 健康检查
    if curl -sf --max-time 3 http://localhost:6081/vnc.html -o /dev/null; then
        echo "  OK  XHS Live View noVNC :6081"
    else
        echo "  WARN XHS Live View noVNC :6081 不可达，请查看 /tmp/websockify-xhs.log /tmp/x11vnc-xhs.log"
    fi
}
ensure_xhs_live_stack

# ── 本地 MCP 服务 ──
# 调各自的 healthcheck.sh：如果端口已健康会直接退出，未运行则拉起。
# 日志见 /tmp/<name>.log。
ensure_local_mcps() {
    local script
    for script in \
        /home/rooot/MCP/image-gen-mcp/healthcheck.sh \
        /home/rooot/MCP/media-data-pack/healthcheck.sh; do
        if [ -x "$script" ]; then
            local name
            name=$(basename "$(dirname "$script")")
            echo "ensure MCP: $name"
            "$script" >/dev/null 2>&1 || echo "  WARN $name healthcheck returned non-zero"
        fi
    done
}
ensure_local_mcps

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
