#!/usr/bin/env python3
"""检查 mem0-daily-import 备忘录，有则输出汇报内容并清空。

魏忠贤巡检时调用。输出格式与 check-incidents.py 保持一致。
"""

import json
import os

REPORT_FILE = "/home/rooot/.openclaw/workspace-mag1/memory/pending-reports.jsonl"


def main():
    if not os.path.exists(REPORT_FILE):
        return

    records = []
    with open(REPORT_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # 只处理 mem0-daily-import 来源的记录
    mem0_records = [r for r in records if r.get("source") == "mem0-daily-import"]
    other_records = [r for r in records if r.get("source") != "mem0-daily-import"]

    if not mem0_records:
        return

    errors = [r for r in mem0_records if r.get("level") == "ERROR"]
    infos = [r for r in mem0_records if r.get("level") == "INFO"]

    lines = []
    if errors:
        lines.append(f"【mem0 入库异常】{len(errors)} 条")
        for r in errors:
            lines.append(f"  ❌ {r.get('ts', '')} - {r.get('summary', '')}")
            if r.get("detail"):
                lines.append(f"     {r['detail']}")
    if infos:
        latest = infos[-1]  # 取最新一条
        lines.append(f"【mem0 记忆入库日报】{latest.get('ts', '')}")
        lines.append(f"  ✅ {latest.get('summary', '')}")
        if latest.get("detail"):
            lines.append(f"  {latest['detail']}")
        if len(infos) > 1:
            lines.append(f"  （备忘录中共 {len(infos)} 条 INFO，已合并，仅展示最新）")

    print("\n".join(lines))

    # 清空已处理的 mem0 记录，保留其他来源
    with open(REPORT_FILE, "w") as f:
        for r in other_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
