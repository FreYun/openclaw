#!/usr/bin/env bash
# mx-moni wrapper — per-bot key loader
#
# 调用链：bot workspace (cwd = ~/.openclaw/workspace-botN) -> bash skills/mx-moni/run.sh "..."
# 查找顺序：
#   1. $MX_APIKEY 环境变量（若已设置，直接用，方便临时覆盖）
#   2. $PWD/.mx_apikey（bot 当前 workspace 下的独立 key 文件，推荐方式）
#   3. 否则报错退出
#
# key 文件格式：纯文本，单行，仅 key 本身，不带 export / 引号 / 换行。
# 建议 chmod 600 避免被其他进程读到。

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${MX_APIKEY:-}" ]; then
  if [ -f "$PWD/.mx_apikey" ]; then
    MX_APIKEY="$(tr -d '[:space:]' < "$PWD/.mx_apikey")"
    export MX_APIKEY
  fi
fi

if [ -z "${MX_APIKEY:-}" ]; then
  echo "错误: 未找到 MX_APIKEY。" >&2
  echo "请在当前 bot 的 workspace 目录下创建 .mx_apikey 文件（单行 key），或设置 MX_APIKEY 环境变量。" >&2
  echo "当前 PWD: $PWD" >&2
  exit 1
fi

exec python3 "$SKILL_DIR/mx_moni.py" "$@"
