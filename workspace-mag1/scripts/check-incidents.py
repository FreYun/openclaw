#!/usr/bin/env python3
"""检查 incidents.jsonl 是否有积压异常，有则输出告警内容并清空文件，无则静默。"""

import json
import os
import sys

INCIDENTS_FILE = "/home/rooot/.openclaw/security/incidents.jsonl"


def main():
    if not os.path.exists(INCIDENTS_FILE):
        return

    records = []
    with open(INCIDENTS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not records:
        return

    errors = [r for r in records if r.get("level") == "ERROR"]
    warnings = [r for r in records if r.get("level") == "WARNING"]

    # 输出告警内容供魏忠贤转发飞书
    lines = []
    if errors:
        lines.append(f"【异常告警】积压 {len(errors)} 条 ERROR：")
        for r in errors:
            sid = r.get('session_id', 'unknown')
            lines.append(f"  ❌ {r.get('type')} - {r.get('reporter')} [session:{sid}]: {r.get('message')}")
    if warnings:
        lines.append(f"  ⚠️ WARNING {len(warnings)} 条（已静默归档）")

    print("\n".join(lines))

    # 清空文件
    with open(INCIDENTS_FILE, "w") as f:
        pass

    print(f"\n已清理 {len(records)} 条记录")


if __name__ == "__main__":
    main()
