#!/usr/bin/env python3
"""
sync-fund-pool.py — 从腾讯文档同步基金池到 bot9 本地文件

原理：通过 CDP (Chrome DevTools Protocol) 连接 bot9 的 Chrome，
打开腾讯文档表格，用 Ctrl+A → Ctrl+C → 读剪贴板 提取数据。
腾讯文档表格是 canvas 渲染，DOM 里没有数据，只能用这种方式。

同步三个 sheet：主题-核心池、市值-核心池、风格-核心池。

用法：
    python3 sync-fund-pool.py           # 同步三个核心池
    python3 sync-fund-pool.py --dry-run # 只预览，不写文件

前置条件：bot9 的 Chrome 中需要已打开腾讯文档链接。

输出：workspace-bot9/skills/daily-market-recap/基金池.md
"""

import argparse
import csv
import io
import json
import sys
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

try:
    import websocket
except ImportError:
    print("需要安装 websocket-client: pip install websocket-client")
    sys.exit(1)

# ── 配置 ──────────────────────────────────────────────
CDP_PORT = 18809  # bot9 Chrome CDP 端口
DOC_URL = "https://docs.qq.com/sheet/DWmVodVJ4TEN2aEZQ"
DOC_ID = "WmVodVJ4TEN2aEZQ"

# 三个核心池 sheet
SHEETS = {
    "主题-核心池": {"tab": "000001", "group_col": "主题(最新)", "group_labels": True},
    "市值-核心池": {"tab": "000003", "group_col": "市值(最新)", "group_labels": True},
    "风格-核心池": {"tab": "000005", "group_col": "风格(最新)", "group_labels": True},
}

# 市值/风格标签的中文映射
LABEL_MAP = {
    # 市值
    "B": "大盘", "M": "中盘", "S": "小盘",
    # 风格
    "G": "成长", "V": "价值", "N": "均衡",
}

OUTPUT_FILE = Path("/home/rooot/.openclaw/workspace-bot9/skills/daily-market-recap/基金池.md")

# 主题显示顺序
THEME_ORDER = ["科技", "全市场", "新能源", "医药", "消费", "周期", "金融", "制造", "基建地产"]


# ── CDP 通信 ──────────────────────────────────────────
class CDPConnection:
    def __init__(self, ws_url, timeout=15):
        self.ws = websocket.create_connection(ws_url, timeout=timeout)
        self.msg_id = 0

    def send(self, method, params=None):
        self.msg_id += 1
        msg = {"id": self.msg_id, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.msg_id:
                if "error" in r:
                    raise RuntimeError(f"CDP error: {r['error']}")
                return r.get("result", {})

    def close(self):
        self.ws.close()


def find_tab(cdp_port, doc_id):
    """找一个已打开的腾讯文档 tab，避免重复开"""
    import urllib.request
    tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{cdp_port}/json").read())
    for t in tabs:
        if doc_id in t.get("url", "") and t.get("webSocketDebuggerUrl"):
            return t["webSocketDebuggerUrl"]
    return None


def extract_sheet_data(cdp, tab_id, wait=5):
    """导航到指定 tab 并提取剪贴板数据"""
    url = f"{DOC_URL}?tab={tab_id}"
    cdp.send("Page.navigate", {"url": url})
    time.sleep(wait)

    # 授权剪贴板
    cdp.send("Browser.grantPermissions",
             {"permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})

    # 点击聚焦
    cdp.send("Runtime.evaluate", {"expression": "document.body.click()"})
    time.sleep(0.5)

    # Ctrl+A 全选
    for evt in ["keyDown", "keyUp"]:
        cdp.send("Input.dispatchKeyEvent", {
            "type": evt, "modifiers": 2,
            "key": "a", "code": "KeyA", "windowsVirtualKeyCode": 65
        })
    time.sleep(1)

    # Ctrl+C 复制
    for evt in ["keyDown", "keyUp"]:
        cdp.send("Input.dispatchKeyEvent", {
            "type": evt, "modifiers": 2,
            "key": "c", "code": "KeyC", "windowsVirtualKeyCode": 67
        })
    time.sleep(2)

    # 读剪贴板
    r = cdp.send("Runtime.evaluate", {
        "expression": "navigator.clipboard.readText()",
        "awaitPromise": True
    })
    text = r.get("result", {}).get("value", "")
    return text


def parse_pool(tsv_text, group_col):
    """解析基金池 TSV，按 group_col 分组，返回 (headers, {group: [fund_dict, ...]})"""
    reader = csv.DictReader(io.StringIO(tsv_text), delimiter='\t')
    # 保留原始表头（去掉第一列的空白分组列）
    raw_headers = reader.fieldnames or []
    headers = [h for h in raw_headers if h.strip()]
    by_group = OrderedDict()

    current_group = ""
    for row in reader:
        # 第一列可能是分组标签
        first_col = list(row.values())[0].strip() if row else ""
        name = row.get("基金简称", "").strip()
        status = row.get("申购状态", "").strip()
        group_val = row.get(group_col, "").strip()
        score_str = row.get("分数", "").strip()

        if not name:
            continue

        # 跳过暂停申购的
        if "暂停" in status:
            continue

        # 第一列非空非数字 → 分组标签
        if first_col and not first_col.isdigit() and len(first_col) <= 10:
            current_group = first_col

        # 用指定列的值分组，多值取第一个
        display_group = group_val.split(",")[0] if group_val else current_group
        if not display_group:
            display_group = "其他"

        try:
            score = float(score_str) if score_str else 0
        except ValueError:
            score = 0

        # 保留所有列的值
        fund = {h: row.get(h, "").strip() for h in headers}
        fund["_group"] = display_group
        fund["_score"] = score
        by_group.setdefault(display_group, []).append(fund)

    # 每组内按分数降序（得分高的排前面，bot9 优先选排前面的）
    for g in by_group:
        by_group[g].sort(key=lambda f: -f["_score"])

    return headers, by_group


def sort_groups(groups_dict, is_theme=False):
    """排序分组：主题按预定义顺序，其他按字母"""
    ordered = OrderedDict()
    if is_theme:
        for t in THEME_ORDER:
            if t in groups_dict:
                ordered[t] = groups_dict[t]
    for g in sorted(groups_dict.keys()):
        if g not in ordered:
            ordered[g] = groups_dict[g]
    return ordered


def format_fund_table(funds, headers):
    """格式化基金列表为 markdown 表格，保留全部列，按分数降序"""
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = [header_line, sep_line]
    for f in funds:
        cells = [f.get(h, "") for h in headers]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def group_display_name(group_key, sheet_name):
    """生成分组的显示名"""
    mapped = LABEL_MAP.get(group_key)
    if mapped:
        return f"{mapped}({group_key})"
    return group_key


def generate_markdown(all_data):
    """生成 基金池.md 内容"""
    now = datetime.now()
    month_str = now.strftime("%Y%m")
    date_str = now.strftime("%Y-%m-%d")

    lines = [
        "---",
        "name: 基金池",
        "description: >",
        "  天天基金研究部基金池本地副本。由 sync-fund-pool.py 从腾讯文档自动同步。",
        f"updated: {date_str}",
        f"month: {month_str}",
        "---",
        "",
        f"# 天天基金研究部基金池（{month_str}）",
        "",
        f"> 自动同步时间：{date_str}。数据来源：腾讯文档权益基金池。",
        "> 每个分组内按「分数」从高到低排序，推荐时优先选排名靠前的。",
        "",
    ]

    for sheet_name, sheet_data in all_data.items():
        pool_data = sheet_data["data"]
        headers = sheet_data["headers"]
        total = sum(len(v) for v in pool_data.values())
        is_theme = "主题" in sheet_name

        lines.extend(["---", "", f"## {sheet_name}（共{total}只）", ""])

        sorted_groups = sort_groups(pool_data, is_theme=is_theme)
        for group_key, funds in sorted_groups.items():
            display = group_display_name(group_key, sheet_name)
            lines.append(f"### {display}（{len(funds)}只）")
            lines.append("")
            lines.append(format_fund_table(funds, headers))
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="从腾讯文档同步基金池到 bot9 本地文件")
    parser.add_argument("--dry-run", action="store_true", help="只预览统计，不写文件")
    args = parser.parse_args()

    total_sheets = len(SHEETS)

    # 1. 找 tab
    print(f"[1/{total_sheets+2}] 查找 bot9 Chrome (CDP:{CDP_PORT}) 中的腾讯文档 tab...")
    ws_url = find_tab(CDP_PORT, DOC_ID)
    if not ws_url:
        print("❌ 未找到已打开的腾讯文档 tab。请先在 bot9 的 Chrome 中打开：")
        print(f"   {DOC_URL}")
        sys.exit(1)
    print(f"   ✓ 找到 tab: {ws_url[:60]}...")

    cdp = CDPConnection(ws_url)
    all_data = OrderedDict()

    # 2. 逐个 sheet 提取
    for i, (sheet_name, sheet_cfg) in enumerate(SHEETS.items(), start=2):
        print(f"[{i}/{total_sheets+2}] 提取 {sheet_name} (tab={sheet_cfg['tab']})...")
        text = extract_sheet_data(cdp, sheet_cfg["tab"])
        headers, data = parse_pool(text, sheet_cfg["group_col"])
        total = sum(len(v) for v in data.values())
        print(f"   ✓ {total} 只基金，{len(data)} 个分组，{len(headers)} 列")
        for group, funds in data.items():
            label = LABEL_MAP.get(group, group)
            print(f"     - {label}: {len(funds)}只")
        all_data[sheet_name] = {"data": data, "headers": headers, "cfg": sheet_cfg}

    cdp.close()

    # 3. 生成并写入
    md = generate_markdown(all_data)
    step = total_sheets + 2
    print(f"[{step}/{step}] 生成 markdown（{len(md.splitlines())} 行，{len(md)} 字符）...")

    if args.dry_run:
        print("\n--- DRY RUN：预览前 60 行 ---")
        for line in md.splitlines()[:60]:
            print(line)
        print(f"\n（共 {len(md.splitlines())} 行，--dry-run 不写文件）")
    else:
        OUTPUT_FILE.write_text(md, encoding="utf-8")
        print(f"   ✓ 已写入 {OUTPUT_FILE}")
        print(f"   文件大小：{OUTPUT_FILE.stat().st_size:,} 字节")

    print("\n✅ 完成")


if __name__ == "__main__":
    main()
