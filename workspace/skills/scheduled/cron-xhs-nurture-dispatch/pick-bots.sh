#!/usr/bin/env bash
# pick-bots.sh — 为 cron-xhs-nurture-dispatch 挑选本轮养号 bot
#
# 逻辑:
#   1. 读取 last-nurture-bots.txt(逗号分隔的上一轮选中 bot)
#   2. 从 POOL 中排除上轮选中,剩下的里面随机挑 3 个
#   3. 把本轮选中写回 last-nurture-bots.txt(覆盖)
#   4. 向 stdout 输出本轮 3 个 bot id,逗号分隔(供 dispatcher 使用)
#
# 可覆盖环境变量:
#   NURTURE_POOL      候选池,空格分隔 (默认 "bot1 bot2 bot3 bot4 bot5 bot6 bot7")
#   NURTURE_PICK_N    每轮选几个       (默认 3)
#   LAST_ROUND_FILE   状态文件路径     (默认 workspace-mag1/memory/last-nurture-bots.txt)
#
# 退出码:
#   0 成功,stdout 为逗号分隔的 bot id 列表
#   1 参数/环境异常(如剩余池不足)

set -euo pipefail

POOL="${NURTURE_POOL:-bot1 bot2 bot3 bot4 bot5 bot6 bot7 bot12 bot13 bot16 bot17}"
PICK_N="${NURTURE_PICK_N:-3}"
LAST_ROUND_FILE="${LAST_ROUND_FILE:-/home/rooot/.openclaw/workspace-mag1/memory/last-nurture-bots.txt}"

# 读上一轮,可能不存在或为空
last=""
if [[ -s "$LAST_ROUND_FILE" ]]; then
  last=$(tr -d '[:space:]' < "$LAST_ROUND_FILE")
fi

# 构造排除集合(逗号分隔 → 空格分隔便于 grep)
excluded=$(echo "$last" | tr ',' ' ')

# 从 POOL 中排除上轮
remaining=()
for b in $POOL; do
  skip=false
  for e in $excluded; do
    if [[ "$b" == "$e" ]]; then
      skip=true
      break
    fi
  done
  $skip || remaining+=("$b")
done

# 如果剩余池不足(例如上一轮选了 5 个),回退到从完整 POOL 选
if (( ${#remaining[@]} < PICK_N )); then
  remaining=($POOL)
fi

# 随机挑 PICK_N 个
picked=$(printf '%s\n' "${remaining[@]}" | shuf -n "$PICK_N" | paste -sd ',' -)

if [[ -z "$picked" ]]; then
  echo "pick-bots: failed to pick any bot" >&2
  exit 1
fi

# 原子写回状态文件
mkdir -p "$(dirname "$LAST_ROUND_FILE")"
tmp="${LAST_ROUND_FILE}.tmp.$$"
printf '%s\n' "$picked" > "$tmp"
mv "$tmp" "$LAST_ROUND_FILE"

# 输出本轮选中
printf '%s\n' "$picked"
