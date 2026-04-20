#!/usr/bin/env bash
# aggregate-topic-pool.sh — 跨 bot 聚合 topic-library 的带标记素材
#
# 用法:
#   bash scripts/aggregate-topic-pool.sh [--min-level 火|火火|火树] [--max-age-days N]
#
# 环境变量:
#   BASE — 扫描根目录（默认 /home/rooot/.openclaw）
# 豁免 bot: bot11（奶龙）
# FAIL-LOUD: BASE 不存在 / 命令失败 → 退出码非 0

set -euo pipefail

BASE="${BASE:-/home/rooot/.openclaw}"
MIN_LEVEL="火"
MAX_AGE_DAYS=7
EXEMPT_BOTS=("bot11")

while [[ $# -gt 0 ]]; do
  case "$1" in
    --min-level) MIN_LEVEL="$2"; shift 2 ;;
    --max-age-days) MAX_AGE_DAYS="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -d "$BASE" ]]; then
  echo "{\"error\": \"BASE directory not found: $BASE\"}" >&2
  exit 1
fi

# 级别映射：火树(🌲)=1, 火(🔥)=2, 火火(🔥🔥)=3
min_level_num=2
case "$MIN_LEVEL" in
  火树) min_level_num=1 ;;
  火) min_level_num=2 ;;
  火火) min_level_num=3 ;;
  *) echo "{\"error\": \"unknown --min-level: $MIN_LEVEL\"}" >&2; exit 2 ;;
esac

now_epoch=$(date +%s)
cutoff_epoch=$((now_epoch - MAX_AGE_DAYS * 86400))

# 拼 exempt 筛选表达式
exempt_pattern=""
for b in "${EXEMPT_BOTS[@]}"; do
  exempt_pattern="${exempt_pattern:+$exempt_pattern|}$b"
done

# 扫描 topic-library.md 文件并收集 items + bots_scanned
# 规范化 BASE 去掉末尾 /
BASE_NORM="${BASE%/}"

bots_scanned=()
items=""

while IFS= read -r file; do
  # 提取相对路径第一段作为 bot 名：先剥离 BASE 前缀，再取首段
  rel="${file#$BASE_NORM/}"
  first_seg="${rel%%/*}"
  # 如果首段以 workspace- 开头（生产：workspace-bot1），剥掉前缀
  bot="${first_seg#workspace-}"
  [[ -z "$bot" ]] && continue
  [[ "$bot" =~ ^(${exempt_pattern})$ ]] && continue

  bots_scanned+=("$bot")

  # 空文件或过旧 → 跳过解析但保留 bots_scanned 记录
  [[ ! -s "$file" ]] && continue
  file_mtime=$(stat -c '%Y' "$file")
  [[ $file_mtime -lt $cutoff_epoch ]] && continue
  file_date=$(date -d "@$file_mtime" +%Y-%m-%d)

  # awk 提取带 emoji 的段落（首行为标题，后续行搜"角度"）
  entry=$(awk -v bot="$bot" -v filepath="$file" -v mindate="$file_date" -v minlvl="$min_level_num" '
    BEGIN { RS=""; FS="\n" }
    /🔥🔥|🔥|🌲/ {
      level = ""; level_num = 0
      if ($0 ~ /🔥🔥/) { level = "🔥🔥"; level_num = 3 }
      else if ($0 ~ /🔥/) { level = "🔥"; level_num = 2 }
      else if ($0 ~ /🌲/) { level = "🌲"; level_num = 1 }
      if (level_num < minlvl) next

      title = $1
      gsub(/^#+[[:space:]]*/, "", title)
      gsub(/^(🔥🔥|🔥|🌲)[[:space:]]*/, "", title)

      angle = ""
      for (i = 2; i <= NF; i++) {
        if ($i ~ /角度/) {
          angle = $i
          sub(/^[[:space:]]*[-*][[:space:]]*角度[:：][[:space:]]*/, "", angle)
          break
        }
      }

      # JSON-escape：先处理反斜杠，再处理双引号
      gsub(/\\/, "\\\\", title); gsub(/"/, "\\\"", title)
      gsub(/\\/, "\\\\", angle); gsub(/"/, "\\\"", angle)

      printf "{\"bot\":\"%s\",\"level\":\"%s\",\"title\":\"%s\",\"angle\":\"%s\",\"file_path\":\"%s\",\"captured_at\":\"%s\"}\n", bot, level, title, angle, filepath, mindate
    }
  ' "$file")

  if [[ -n "$entry" ]]; then
    [[ -n "$items" ]] && items="$items"$'\n'"$entry" || items="$entry"
  fi
done < <(find "$BASE" -maxdepth 4 -type f -path '*/memory/topic-library.md' 2>/dev/null | sort)

# 组装 JSON
scanned_at=$(date -Iseconds)
bots_json=$(printf '%s\n' "${bots_scanned[@]}" | sort -u | awk 'BEGIN{printf "["; sep=""} NF{printf "%s\"%s\"", sep, $0; sep=","} END{printf "]"}')
items_json=$(echo "$items" | awk 'BEGIN{printf "["; sep=""} NF{printf "%s%s", sep, $0; sep=","} END{printf "]"}')
[[ -z "$items" ]] && items_json="[]"

printf '{"scanned_at":"%s","bots_scanned":%s,"items":%s}\n' "$scanned_at" "$bots_json" "$items_json"
