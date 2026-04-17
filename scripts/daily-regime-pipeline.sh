#!/bin/bash
# 每日 regime 数据管道 (工作日 16:00 cron)
#
# 流程:
#   1. daily_review.py  → 采集行情, 写入 daily/stk_limit/regime_raw_daily/index_daily
#   2. replay.py        → 从 2015 起完整回放, 写入 regime_classify_daily(v2)
#                          (保证 3 日确认链完整一致, ~40 秒)
#
# 为什么用 replay 而不是 classify.py:
#   classify.py 读 regime-log.md 做 3 日确认, 历史链可能跟 DB 不一致
#   replay.py 从 regime_raw_daily 完整回放, 链条永远一致
#
# crontab:
#   0 16 * * 1-5 /bin/bash /home/rooot/.openclaw/scripts/daily-regime-pipeline.sh >> /home/rooot/.openclaw/logs/daily-regime-pipeline.log 2>&1

set -euo pipefail

LOG_PREFIX="[regime-pipeline $(date +%Y-%m-%d_%H:%M:%S)]"
REVIEW_DIR="/home/rooot/.openclaw/workspace-bot11/scripts"
BACKFILL_DIR="/home/rooot/.openclaw/workspace/skills/strategy/market-regime-classifier/scripts/backfill"

TODAY=$(date +%Y-%m-%d)
TODAY_FMT=$(date +%Y%m%d)

echo ""
echo "$LOG_PREFIX ========== 开始 =========="

# Step 1: daily_review.py — 采集 + 落库
echo "$LOG_PREFIX [1/2] daily_review.py"
cd "$REVIEW_DIR"
python3 review/daily_review.py "$TODAY" 2>&1 || {
    echo "$LOG_PREFIX daily_review.py 失败 (rc=$?), 但继续尝试 replay" >&2
}

# Step 2: replay.py — 完整回放 regime 链
echo "$LOG_PREFIX [2/2] replay.py (全量回放)"
cd "$BACKFILL_DIR"
python3 replay.py --rules v2 --start 20150105 --end "$TODAY_FMT" --csv /tmp/regime_replay_full.csv 2>&1

# Step 3: 导入 DB
echo "$LOG_PREFIX 导入 regime_classify_daily"
python3 load_to_db.py --v2 /tmp/regime_replay_full.csv 2>&1

# Step 4: 打印今日结果
echo "$LOG_PREFIX 今日结果:"
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/rooot/database/market.db')
conn.row_factory = sqlite3.Row
r = conn.execute('''
    SELECT trade_date, total_score, regime_name, switched, emergency_switch
    FROM regime_classify_daily WHERE rules_version=\"v2\"
    ORDER BY trade_date DESC LIMIT 1
''').fetchone()
if r:
    sw = 'switched=1 ' if r['switched'] else ''
    emg = 'emergency! ' if r['emergency_switch'] else ''
    regime = r['regime_name']
    boosted = r['switched'] and regime in ('强牛','强势震荡')
    pos = '90% ⚡' if boosted else '50%'
    print(f'  {r[\"trade_date\"]} | 总分={r[\"total_score\"]} | {regime} | {sw}{emg}| 仓位={pos}')
conn.close()
"

echo "$LOG_PREFIX ========== 完成 =========="
