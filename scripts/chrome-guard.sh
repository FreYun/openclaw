#!/usr/bin/env bash
# chrome-guard.sh — 定期清理冗余 Chrome 进程，防止资源耗尽导致网络崩溃
#
# 三类清理目标：
#   1. Rod (XHS MCP) 孤儿/超时实例 → /tmp/rod/user-data/*
#   2. Gateway browser: 超 1 小时的 tab 定向关闭，全空闲超 2 小时关浏览器
#   3. 总进程数告警
#
# 用法:
#   chrome-guard.sh              # 正常执行
#   chrome-guard.sh --dry-run    # 只报告不动手
#
# crontab 示例:
#   */5 * * * * /home/rooot/.openclaw/scripts/chrome-guard.sh >> /tmp/chrome-guard.log 2>&1

set -euo pipefail

# ── 配置 ──────────────────────────────────────────
ROD_DIR="/tmp/rod/user-data"
ROD_MAX_AGE_SEC=1800              # Rod 实例最大存活 30 分钟
TAB_MAX_AGE_SEC=3600              # Gateway tab 最大存活 1 小时
GATEWAY_IDLE_MAX_SEC=7200         # Gateway browser 全空闲后最大 2 小时
GATEWAY_PORT_MIN=18800
GATEWAY_PORT_MAX=18819
CHROME_WARN_THRESHOLD=70
LOCALHOST_CONN_WARN=200
TAB_STATE_FILE="/tmp/chrome-guard-tabs.json"
DRY_RUN=false

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# ── 工具函数 ──────────────────────────────────────
log() { echo "[chrome-guard $(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# 将 ps etime (格式: [[DD-]HH:]MM:SS) 转换为秒数
etime_to_sec() {
    local t="$1"
    local days=0 hours=0 mins=0 secs=0

    # DD-HH:MM:SS
    if [[ "$t" =~ ^([0-9]+)-([0-9]+):([0-9]+):([0-9]+)$ ]]; then
        days=${BASH_REMATCH[1]}; hours=${BASH_REMATCH[2]}
        mins=${BASH_REMATCH[3]}; secs=${BASH_REMATCH[4]}
    # HH:MM:SS
    elif [[ "$t" =~ ^([0-9]+):([0-9]+):([0-9]+)$ ]]; then
        hours=${BASH_REMATCH[1]}; mins=${BASH_REMATCH[2]}; secs=${BASH_REMATCH[3]}
    # MM:SS
    elif [[ "$t" =~ ^([0-9]+):([0-9]+)$ ]]; then
        mins=${BASH_REMATCH[1]}; secs=${BASH_REMATCH[2]}
    fi

    echo $(( days*86400 + hours*3600 + mins*60 + secs ))
}

# 精确 kill 一个进程树（先子后父），绝不用 pkill/killall
kill_tree() {
    local pid="$1"
    local children
    children=$(pgrep -P "$pid" 2>/dev/null || true)
    for child in $children; do
        kill_tree "$child"
    done
    if kill -0 "$pid" 2>/dev/null; then
        if $DRY_RUN; then
            log "  [DRY-RUN] would kill PID $pid ($(ps -o comm= -p "$pid" 2>/dev/null || echo '?'))"
        else
            kill "$pid" 2>/dev/null || true
        fi
    fi
}

killed_rod=0
killed_gateway=0
closed_tabs=0
cleaned_dirs=0

# ── 1. 清理 Rod (XHS MCP) 实例 ───────────────────
log "=== Rod 实例检查 ==="

MCP_PID=$(pgrep -x xiaohongshu-mcp 2>/dev/null | head -1 || echo "")
if [ -z "$MCP_PID" ]; then
    log "xiaohongshu-mcp 未运行"
fi

if [ -d "$ROD_DIR" ]; then
    for dir in "$ROD_DIR"/*/; do
        [ -d "$dir" ] || continue
        hash=$(basename "$dir")

        # 找到使用该 user-data 的 Chrome 主进程（有 --user-data-dir 且无 --type= 的是主进程）
        chrome_pid=""
        while IFS= read -r pid; do
            if ps -o args= -p "$pid" 2>/dev/null | grep -q "\-\-user-data-dir=.*${hash}" && \
               ! ps -o args= -p "$pid" 2>/dev/null | grep -q '\-\-type='; then
                chrome_pid="$pid"
                break
            fi
        done < <(pgrep chrome 2>/dev/null || true)

        if [ -z "$chrome_pid" ]; then
            log "孤儿目录: $hash (无活跃进程)"
            if $DRY_RUN; then
                log "  [DRY-RUN] would rm -rf $dir"
            else
                rm -rf "$dir"
            fi
            cleaned_dirs=$((cleaned_dirs + 1))
            continue
        fi

        # 检查祖先进程链是否包含 MCP（Rod 链路: MCP → leakless → chrome）
        is_orphan=true
        if [ -n "$MCP_PID" ]; then
            check_pid="$chrome_pid"
            for _ in 1 2 3 4 5; do
                ancestor=$(ps -o ppid= -p "$check_pid" 2>/dev/null | tr -d ' ')
                [ -z "$ancestor" ] || [ "$ancestor" = "1" ] && break
                if [ "$ancestor" = "$MCP_PID" ]; then
                    is_orphan=false
                    break
                fi
                check_pid="$ancestor"
            done
        fi

        if $is_orphan; then
            log "孤儿进程: $hash PID=$chrome_pid (祖先链中无 MCP PID $MCP_PID)"
            kill_tree "$chrome_pid"
            if ! $DRY_RUN; then rm -rf "$dir"; fi
            killed_rod=$((killed_rod + 1))
            cleaned_dirs=$((cleaned_dirs + 1))
            continue
        fi

        # 检查运行时间
        etime=$(ps -o etime= -p "$chrome_pid" 2>/dev/null | tr -d ' ')
        if [ -n "$etime" ]; then
            age_sec=$(etime_to_sec "$etime")
            if [ "$age_sec" -gt "$ROD_MAX_AGE_SEC" ]; then
                log "超时实例: $hash PID=$chrome_pid 运行 ${etime} (>${ROD_MAX_AGE_SEC}s)"
                kill_tree "$chrome_pid"
                if ! $DRY_RUN; then rm -rf "$dir"; fi
                killed_rod=$((killed_rod + 1))
                cleaned_dirs=$((cleaned_dirs + 1))
                continue
            fi
        fi

        log "正常: $hash PID=$chrome_pid 运行 ${etime:-unknown}"
    done
fi

# ── 2. Gateway browser: 关超时 tab + 关空闲浏览器 ──
log "=== Gateway browser 检查 ==="

NOW_EPOCH=$(date +%s)

# 加载 tab 状态文件（记录每个 tab 首次出现时间）
declare -A tab_first_seen
if [ -f "$TAB_STATE_FILE" ]; then
    while IFS='=' read -r key val; do
        [ -n "$key" ] && tab_first_seen["$key"]="$val"
    done < <(python3 -c "
import json, sys
try:
    with open('$TAB_STATE_FILE') as f:
        data = json.load(f)
    for k, v in data.items():
        print(f'{k}={v}')
except:
    pass
" 2>/dev/null)
fi

# 收集本轮所有活跃 tab 的 key（用于清理状态文件中已消失的 tab）
declare -A current_tabs

for port in $(seq $GATEWAY_PORT_MIN $GATEWAY_PORT_MAX); do
    if ! ss -tlnp 2>/dev/null | grep -q ":${port} "; then
        continue
    fi

    bot_num=$((port - GATEWAY_PORT_MIN))
    [ "$bot_num" -eq 0 ] && bot_name="openclaw" || bot_name="bot${bot_num}"

    # 通过 CDP /json 查询所有 tab
    tabs_json=$(curl -sf --connect-timeout 2 "http://127.0.0.1:${port}/json" 2>/dev/null || echo "")
    if [ -z "$tabs_json" ]; then
        log "port=$port ($bot_name): CDP 无响应，跳过"
        continue
    fi

    # 用 python 处理 tab 列表：关闭超时 tab，返回剩余非空 tab 数
    result=$(echo "$tabs_json" | python3 -c "
import json, sys

now = $NOW_EPOCH
tab_max_age = $TAB_MAX_AGE_SEC
port = $port
dry_run = $($DRY_RUN && echo 'True' || echo 'False')

# 从 stdin 读 tab 列表
tabs = json.load(sys.stdin)

# 从环境读已知的 first_seen
first_seen = {}
$(for key in "${!tab_first_seen[@]}"; do echo "first_seen['$key'] = ${tab_first_seen[$key]}"; done)

blank_urls = {'about:blank', '', 'chrome://newtab/'}
remaining_non_blank = 0
tabs_to_close = []
active_keys = []

for tab in tabs:
    url = tab.get('url', '')
    tid = tab.get('id', '')
    if not tid:
        continue
    tab_key = f'{port}:{tid}'
    active_keys.append(tab_key)

    if url in blank_urls:
        continue

    # 检查该 tab 首次出现时间
    if tab_key not in first_seen:
        first_seen[tab_key] = now

    age = now - first_seen[tab_key]
    if age > tab_max_age:
        tabs_to_close.append((tid, url, age))
    else:
        remaining_non_blank += 1

# 输出需要关闭的 tab
for tid, url, age in tabs_to_close:
    mins = age // 60
    print(f'CLOSE:{tid}:{mins}m:{url}')

# 输出活跃 key（用于更新状态文件）
for key in active_keys:
    ts = first_seen.get(key, now)
    print(f'STATE:{key}={ts}')

print(f'REMAINING:{remaining_non_blank}')
" 2>/dev/null || echo "ERROR")

    if [ "$result" = "ERROR" ]; then
        log "port=$port ($bot_name): tab 解析失败，跳过"
        continue
    fi

    # 处理需要关闭的 tab
    while IFS= read -r line; do
        if [[ "$line" == CLOSE:* ]]; then
            tid=$(echo "$line" | cut -d: -f2)
            age_info=$(echo "$line" | cut -d: -f3)
            tab_url=$(echo "$line" | cut -d: -f4-)
            if $DRY_RUN; then
                log "  [DRY-RUN] would close tab $bot_name: $tab_url ($age_info)"
            else
                # CDP 关闭指定 tab
                close_result=$(curl -sf --connect-timeout 2 "http://127.0.0.1:${port}/json/close/${tid}" 2>/dev/null || echo "fail")
                log "  关闭 tab $bot_name: $tab_url ($age_info) → $close_result"
                closed_tabs=$((closed_tabs + 1))
            fi
        elif [[ "$line" == STATE:* ]]; then
            kv="${line#STATE:}"
            key="${kv%%=*}"
            val="${kv#*=}"
            current_tabs["$key"]="$val"
        fi
    done <<< "$result"

    # 提取剩余非空 tab 数
    remaining=$(echo "$result" | grep '^REMAINING:' | cut -d: -f2)
    remaining=${remaining:-0}

    if [ "$remaining" -gt 0 ]; then
        log "port=$port ($bot_name): 剩余 $remaining 个活跃 tab"
        continue
    fi

    # 所有 tab 都是 blank 或已关闭 — 检查浏览器是否该整体关闭
    chrome_pid=$(ss -tlnp 2>/dev/null | grep ":${port} " | grep -oP 'pid=\K[0-9]+' | head -1)
    if [ -z "$chrome_pid" ]; then
        continue
    fi

    etime=$(ps -o etime= -p "$chrome_pid" 2>/dev/null | tr -d ' ')
    if [ -z "$etime" ]; then
        continue
    fi

    age_sec=$(etime_to_sec "$etime")
    if [ "$age_sec" -gt "$GATEWAY_IDLE_MAX_SEC" ]; then
        log "空闲超时: $bot_name port=$port PID=$chrome_pid 运行 ${etime} 所有 tab 已空"
        if $DRY_RUN; then
            log "  [DRY-RUN] would kill browser $bot_name"
        else
            kill_tree "$chrome_pid"
        fi
        killed_gateway=$((killed_gateway + 1))
    else
        log "port=$port ($bot_name): 全空闲，未超时 (${etime})"
    fi
done

# 保存 tab 状态文件（只保留本轮仍存在的 tab）
python3 -c "
import json
data = {$(for key in "${!current_tabs[@]}"; do echo "'$key': ${current_tabs[$key]},"; done)}
with open('$TAB_STATE_FILE', 'w') as f:
    json.dump(data, f)
" 2>/dev/null || true

# ── 3. 总数监控 ──────────────────────────────────
total_chrome=$(pgrep -c chrome 2>/dev/null || echo 0)
log "=== 总计: Chrome=$total_chrome 关tab=$closed_tabs 关Rod=$killed_rod 关Gateway=$killed_gateway 清目录=$cleaned_dirs ==="

if [ "$total_chrome" -gt "$CHROME_WARN_THRESHOLD" ]; then
    log "WARN: Chrome 进程数 $total_chrome 超过阈值 $CHROME_WARN_THRESHOLD"
fi

# ── 4. 本地连接数监控 ────────────────────────────
localhost_conns=$(ss -tn 2>/dev/null | grep '127.0.0.1' | wc -l)
if [ "$localhost_conns" -gt "$LOCALHOST_CONN_WARN" ]; then
    log "WARN: 127.0.0.1 连接数 $localhost_conns 超过阈值 $LOCALHOST_CONN_WARN"
fi
