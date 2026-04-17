#!/usr/bin/env bash
# 跑 sector-heat.mjs，结果写入 hot_shot.md 热点看板
# cron 每 15 分钟调用一次

SCRIPT_DIR="/home/rooot/.openclaw/scripts"
HOT_FILE="/home/rooot/.openclaw/workspace/skills/armor/xhs-op/hot_shot.md"

# 运行 sector-heat.mjs，超时 60 秒
OUTPUT=$(cd "$SCRIPT_DIR" && timeout 60 node sector-heat.mjs --xueqiu 2>/dev/null | grep -v '^✅')

# 如果没有输出就跳过
if [ -z "$OUTPUT" ]; then
  echo "[$(date '+%F %T')] sector-heat: no output, skipping"
  exit 0
fi

TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

cat > "$HOT_FILE" <<EOF
# 热点看板

> 自动更新：${TIMESTAMP}（每 15 分钟刷新）

\`\`\`
${OUTPUT}
\`\`\`
EOF

echo "[$(date '+%F %T')] sector-heat: written to hot_shot.md"
