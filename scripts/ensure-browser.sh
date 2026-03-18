#!/usr/bin/env bash
# ensure-browser.sh — 确保指定 profile 的 Chrome 浏览器在运行
# 用法: ensure-browser.sh <profile>
# 示例: ensure-browser.sh bot7
#
# 如果该 profile 的 Chrome 已在运行，静默退出。
# 如果未运行，自动启动并等待 CDP 端口就绪。

set -euo pipefail

PROFILE="${1:?用法: ensure-browser.sh <profile>}"
BROWSER_DIR="/home/rooot/.openclaw/browser"
CHROME_BIN="/opt/google/chrome/chrome"

# profile → CDP 端口映射（从 openclaw.json 读取）
get_cdp_port() {
    local p="$1"
    python3 -c "
import json, sys
with open('/home/rooot/.openclaw/openclaw.json') as f:
    cfg = json.load(f)
profiles = cfg.get('browser', {}).get('profiles', {})
if '$p' not in profiles:
    print('ERROR: profile \"$p\" not found in openclaw.json', file=sys.stderr)
    sys.exit(1)
print(profiles['$p']['cdpPort'])
"
}

CDP_PORT=$(get_cdp_port "$PROFILE")

# 检查端口是否已在监听
if ss -tlnp 2>/dev/null | grep -q ":${CDP_PORT} "; then
    echo "OK: ${PROFILE} already running on port ${CDP_PORT}"
    exit 0
fi

# 确保 user-data 目录存在
USER_DATA="${BROWSER_DIR}/${PROFILE}/user-data"
mkdir -p "$USER_DATA"

# 清理可能残留的 SingletonLock（Chrome 崩溃后残留）
rm -f "${USER_DATA}/SingletonLock" 2>/dev/null || true

# 启动 Chrome（headless 模式，与 bot5 成功启动的参数一致）
"$CHROME_BIN" \
    --remote-debugging-port="$CDP_PORT" \
    --remote-allow-origins=* \
    --user-data-dir="$USER_DATA" \
    --no-first-run \
    --no-default-browser-check \
    --disable-sync \
    --disable-background-networking \
    --disable-component-update \
    --disable-features=Translate,MediaRouter \
    --disable-session-crashed-bubble \
    --hide-crash-restore-bubble \
    --password-store=basic \
    --disable-dev-shm-usage \
    --disable-blink-features=AutomationControlled \
    --headless=new \
    --noerrdialogs \
    --ozone-platform=headless \
    --ozone-override-screen-size=800,600 \
    --use-angle=swiftshader-webgl \
    about:blank \
    > "/tmp/chrome-${PROFILE}.log" 2>&1 &

CHROME_PID=$!

# 等待 CDP 端口就绪（最多 10 秒）
for i in $(seq 1 20); do
    if ss -tlnp 2>/dev/null | grep -q ":${CDP_PORT} "; then
        echo "OK: ${PROFILE} started on port ${CDP_PORT} (pid ${CHROME_PID})"
        exit 0
    fi
    sleep 0.5
done

echo "FAIL: ${PROFILE} Chrome failed to start on port ${CDP_PORT} within 10s" >&2
echo "Check /tmp/chrome-${PROFILE}.log for details" >&2
exit 1
