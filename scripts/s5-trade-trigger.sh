#!/usr/bin/env bash
# S5 龙回头交易触发器 — cron 调用, 唤醒 bot6 执行买入或卖出
#
# 用法:
#   s5-trade-trigger.sh buy    # 9:27 集合竞价后, 触发买入
#   s5-trade-trigger.sh sell   # 14:50 尾盘, 触发持仓管理/卖出
#
# crontab:
#   27 9  * * 1-5  /home/rooot/.openclaw/scripts/s5-trade-trigger.sh buy
#   50 14 * * 1-5  /home/rooot/.openclaw/scripts/s5-trade-trigger.sh sell

set -euo pipefail

ACTION="${1:-}"
LOG="/home/rooot/.openclaw/logs/s5-trade.log"
mkdir -p "$(dirname "$LOG")"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [s5-trigger] $*" >> "$LOG"; }

if [ -z "$ACTION" ]; then
    echo "用法: $0 buy|sell" >&2
    exit 1
fi

case "$ACTION" in
    buy)
        MSG="[S5 买入指令] 现在是集合竞价后，请执行 S5 龙回头买入流程：
1. 查询昨日候选: sqlite3 /home/rooot/database/market.db \"SELECT code, name, entry_zone_low, entry_zone_high, stop_loss_price, target_1_price, target_2_price, position_pct FROM s5_candidates WHERE date = (SELECT MAX(date) FROM s5_candidates)\"
2. 如果无候选则跳过
3. 查账户资金: bash skills/mx-moni/run.sh \"我的资金\"
4. 按 position_pct 计算买入股数, 用 entry_zone_high 限价买入
5. 记录到当日日记"
        ;;
    sell)
        MSG="[S5 卖出指令] 现在是尾盘时段，请执行 S5 龙回头持仓管理：
1. 查持仓: bash skills/mx-moni/run.sh \"我的持仓\"
2. 对每只 S5 持仓股, 查询其止损/止盈价: sqlite3 /home/rooot/database/market.db \"SELECT code, stop_loss_price, target_1_price, target_2_price FROM s5_candidates WHERE code = 'XXXXXX' ORDER BY date DESC LIMIT 1\"
3. 按优先级判断: 止损 > 止盈2 > 止盈1 > 涨停持有 > 跌停锁仓 > 收盘退出
4. 需要卖出的执行: bash skills/mx-moni/run.sh \"市价卖出 XXXXXX XXX 股\"
5. 记录到当日日记"
        ;;
    *)
        echo "未知动作: $ACTION (只支持 buy|sell)" >&2
        exit 1
        ;;
esac

log "$ACTION — 发送指令给 bot6"
openclaw agent --agent bot6 --message "$MSG" --timeout 300 >> "$LOG" 2>&1 &
log "$ACTION — 已触发 (pid=$!)"
