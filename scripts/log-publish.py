#!/usr/bin/env python3
"""追加发帖记录到 memory/发帖记录.md 表格。

用法：
  python3 log-publish.py --bot bot7 --title "存储芯片今天太火了" --opinion "通过合规" --status "✅ 已发布"
  python3 log-publish.py --bot bot1 --title "测试帖" --opinion "合规未通过：红线三" --status "❌ 失败"
  python3 log-publish.py --bot bot5 --title "黄金投资" --opinion "频率限制，15分钟内重复" --status "❌ 失败"

可选：
  --time "2026-03-16 15:41"   手动指定时间，默认当前时间
"""

import argparse
import os
from datetime import datetime

LOG_FILE = "/home/rooot/.openclaw/workspace-mcp-publisher/memory/发帖记录.md"

HEADER = """# 发帖记录

_所有通过印务局收到的投稿。最新记录在最上方。_

| 时间 | 来源方 | 帖子标题 | 处理意见 | 发表状态 |
|------|--------|----------|----------|----------|"""


def main():
    parser = argparse.ArgumentParser(description="追加发帖记录")
    parser.add_argument("--bot", required=True, help="来源方，如 bot1")
    parser.add_argument("--title", required=True, help="帖子标题")
    parser.add_argument("--opinion", required=True, help="处理意见")
    parser.add_argument("--status", required=True, help="发表状态")
    parser.add_argument("--time", default=None, help="时间，默认当前时间")
    args = parser.parse_args()

    ts = args.time or datetime.now().strftime("%Y-%m-%d %H:%M")
    new_row = f"| {ts} | {args.bot} | {args.title} | {args.opinion} | {args.status} |"

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write(HEADER + "\n" + new_row + "\n")
        print(f"创建 {LOG_FILE}，已写入第一条记录")
        return

    with open(LOG_FILE, "r") as f:
        content = f.read()

    # Find the table header separator line (|---|...)
    lines = content.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.startswith("|---") or line.startswith("| ---"):
            insert_idx = i + 1
            break

    if insert_idx is not None:
        lines.insert(insert_idx, new_row)
    else:
        # No table yet, rewrite with header
        lines = HEADER.split("\n") + [new_row]

    with open(LOG_FILE, "w") as f:
        f.write("\n".join(lines))

    print(f"已追加: {new_row}")


if __name__ == "__main__":
    main()
