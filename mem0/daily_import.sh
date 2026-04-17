#!/bin/bash
# mem0 每日增量导入脚本（由系统 cron 触发）
#
# 功能：
#   1. 增量导入新 session 到 mem0
#   2. 结果追加到 mag1 的 pending-reports.jsonl，等魏忠贤下次巡检时播报
#
# 系统 crontab 示例：
#   0 0 * * * /home/rooot/.openclaw/mem0/daily_import.sh
set -e

MEM0_DIR=/home/rooot/.openclaw/mem0
LOG_FILE=/tmp/mem0-daily-import.log
REPORT_FILE=/home/rooot/.openclaw/workspace-mag1/memory/pending-reports.jsonl
TS=$(date '+%Y-%m-%d %H:%M:%S')
TS_MS=$(date +%s)000

echo "=== $TS mem0 daily import start ===" >> "$LOG_FILE"

# 通用函数：append 一条 JSON record 到备忘录
append_report() {
    local level="$1"
    local summary="$2"
    local detail="$3"
    mkdir -p "$(dirname "$REPORT_FILE")"
    python3 -c "
import json, sys
rec = {
    'ts': '$TS',
    'ts_ms': $TS_MS,
    'source': 'mem0-daily-import',
    'level': '$level',
    'summary': '''$summary''',
    'detail': '''$detail''',
}
with open('$REPORT_FILE', 'a') as f:
    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
"
}

# 检查 mem0 服务是否存活
if ! curl -sf http://localhost:18095/health > /dev/null 2>&1; then
    echo "[ERROR] mem0 server not reachable" >> "$LOG_FILE"
    append_report "ERROR" "mem0 记忆入库失败" "mem0 服务不可达 (http://localhost:18095)，请检查 server 进程"
    exit 1
fi

# 记录导入前的总数
BEFORE_SESSIONS=$(python3 -c "
import json
try:
    p = json.load(open('$MEM0_DIR/import_progress_fast.json'))
    print(len(p))
except: print(0)
")
BEFORE_FACTS=$(python3 -c "
import json
try:
    p = json.load(open('$MEM0_DIR/import_progress_fast.json'))
    print(sum(v.get('facts', 0) for v in p.values()))
except: print(0)
")

# 执行增量导入
cd "$MEM0_DIR"
if /usr/bin/python3 import_fast.py --bot all --workers 2 >> "$LOG_FILE" 2>&1; then
    STATUS="ok"
else
    STATUS="fail"
fi

# Sync sys1 publish-queue → workspace-bot*/memory/posts/
echo "--- sync_posts ---" >> "$LOG_FILE"
BEFORE_MD=$(python3 -c "
import json
try:
    p = json.load(open('$MEM0_DIR/markdown_progress.json'))
    print(len(p))
except: print(0)
")
/usr/bin/python3 sync_posts.py >> "$LOG_FILE" 2>&1 || echo "[WARN] sync_posts failed" >> "$LOG_FILE"

# 增量导入 workspace-bot*/memory/{research,posts,diary}
echo "--- import_markdown ---" >> "$LOG_FILE"
if /usr/bin/python3 import_markdown.py >> "$LOG_FILE" 2>&1; then
    MD_STATUS="ok"
else
    MD_STATUS="fail"
    STATUS="fail"
fi
AFTER_MD=$(python3 -c "
import json
try:
    p = json.load(open('$MEM0_DIR/markdown_progress.json'))
    print(len(p))
except: print(0)
")
NEW_MD=$((AFTER_MD - BEFORE_MD))

# 记录导入后的总数
AFTER_SESSIONS=$(python3 -c "
import json
try:
    p = json.load(open('$MEM0_DIR/import_progress_fast.json'))
    print(len(p))
except: print(0)
")
AFTER_FACTS=$(python3 -c "
import json
try:
    p = json.load(open('$MEM0_DIR/import_progress_fast.json'))
    print(sum(v.get('facts', 0) for v in p.values()))
except: print(0)
")

NEW_SESSIONS=$((AFTER_SESSIONS - BEFORE_SESSIONS))
NEW_FACTS=$((AFTER_FACTS - BEFORE_FACTS))

# 按 agent 统计 top 5
TOP5=$(python3 -c "
import json
try:
    p = json.load(open('$MEM0_DIR/import_progress_fast.json'))
    by_bot = {}
    for k, v in p.items():
        bot = k.split('/')[0]
        by_bot[bot] = by_bot.get(bot, 0) + v.get('facts', 0)
    top = sorted(by_bot.items(), key=lambda x: -x[1])[:5]
    print(' | '.join(f'{b}:{n}' for b, n in top))
except: print('')
")

# 写入备忘录
if [ "$STATUS" = "ok" ]; then
    SUMMARY="mem0 记忆入库: +${NEW_SESSIONS}s/+${NEW_FACTS}f +${NEW_MD}md (总:${AFTER_SESSIONS}s/${AFTER_FACTS}f/${AFTER_MD}md)"
    DETAIL="本次增量: $NEW_SESSIONS sessions, $NEW_FACTS facts, $NEW_MD markdown | 全量: $AFTER_SESSIONS sessions, $AFTER_FACTS facts, $AFTER_MD md | Top5: $TOP5"
    append_report "INFO" "$SUMMARY" "$DETAIL"
else
    append_report "ERROR" "mem0 记忆入库失败" "import 脚本执行异常 (session=$STATUS markdown=$MD_STATUS)，见 $LOG_FILE"
fi

echo "=== $(date '+%Y-%m-%d %H:%M:%S') done: +$NEW_SESSIONS sessions / +$NEW_FACTS facts / +$NEW_MD md (status=$STATUS) ===" >> "$LOG_FILE"
exit 0
