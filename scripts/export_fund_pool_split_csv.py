#!/usr/bin/env python3
"""
export_fund_pool_split_csv.py - 从腾讯文档导出基金池到两个 CSV 文件

通过 CDP (Chrome DevTools Protocol) 连接 bot9 的 Chrome，
打开腾讯文档表格，用 Ctrl+A -> Ctrl+C -> 读剪贴板提取数据。

输出：
- 权益基金池.csv
- 指数基金池.csv

每个 CSV 都保留该池子的全部原始列，并额外保留：
- 列表名称
- tab
"""

import argparse
import csv
import io
import json
import sys
import time
from collections import OrderedDict
from pathlib import Path
from urllib.request import urlopen

try:
    import websocket
except ImportError:
    print("需要安装 websocket-client: pip install websocket-client")
    sys.exit(1)


CDP_PORT = 18809
DEFAULT_OUTPUT_DIR = Path("/home/rooot/.openclaw/workspace-bot9/skills/daily-market-recap")

SOURCES = OrderedDict({
    "权益基金池": {
        "doc_url": "https://docs.qq.com/sheet/DWktnQ3ZEQnhFUGp0",
        "doc_id": "WktnQ3ZEQnhFUGp0",
        "sheets": OrderedDict({
            "主题-核心池": {"tab": "000001"},
            "主题-优选池": {"tab": "000002"},
            "市值-核心池": {"tab": "000003"},
            "市值-优选池": {"tab": "000004"},
            "风格-核心池": {"tab": "000005"},
            "风格-优选池": {"tab": "000006"},
        }),
    },
    "指数基金池": {
        "doc_url": "https://docs.qq.com/sheet/DWkJzR1pNVUVIenZV",
        "doc_id": "WkJzR1pNVUVIenZV",
        "sheets": OrderedDict({
            "指数型基金-核心池": {"tab": "000001"},
            "指数型基金-优选池": {"tab": "000002"},
        }),
    },
})

META_HEADERS = ["列表名称", "tab"]


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
            response = json.loads(self.ws.recv())
            if response.get("id") == self.msg_id:
                if "error" in response:
                    raise RuntimeError(f"CDP error: {response['error']}")
                return response.get("result", {})

    def close(self):
        self.ws.close()


def find_tab(cdp_port, doc_id):
    tabs = json.loads(urlopen(f"http://127.0.0.1:{cdp_port}/json").read())
    for tab in tabs:
        if doc_id in tab.get("url", "") and tab.get("webSocketDebuggerUrl"):
            return tab["webSocketDebuggerUrl"]
    return None


def extract_sheet_data(cdp, doc_url, tab_id, wait=5):
    url = f"{doc_url}?tab={tab_id}"
    cdp.send("Page.navigate", {"url": url})
    time.sleep(wait)

    cdp.send(
        "Browser.grantPermissions",
        {"permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]},
    )

    cdp.send("Runtime.evaluate", {"expression": "document.body.click()"})
    time.sleep(0.5)

    for evt in ["keyDown", "keyUp"]:
        cdp.send(
            "Input.dispatchKeyEvent",
            {
                "type": evt,
                "modifiers": 2,
                "key": "a",
                "code": "KeyA",
                "windowsVirtualKeyCode": 65,
            },
        )
    time.sleep(1)

    for evt in ["keyDown", "keyUp"]:
        cdp.send(
            "Input.dispatchKeyEvent",
            {
                "type": evt,
                "modifiers": 2,
                "key": "c",
                "code": "KeyC",
                "windowsVirtualKeyCode": 67,
            },
        )
    time.sleep(2)

    result = cdp.send(
        "Runtime.evaluate",
        {
            "expression": "navigator.clipboard.readText()",
            "awaitPromise": True,
        },
    )
    return result.get("result", {}).get("value", "")


def parse_tsv_rows(tsv_text):
    reader = csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
    raw_headers = reader.fieldnames or []
    headers = [header.strip() for header in raw_headers if header and header.strip()]

    rows = []
    for row in reader:
        clean_row = OrderedDict()
        has_value = False

        for header in headers:
            value = (row.get(header) or "").strip()
            clean_row[header] = value
            if value:
                has_value = True

        if not has_value:
            continue

        if "基金简称" in clean_row and not clean_row["基金简称"]:
            continue

        rows.append(clean_row)

    return headers, rows


def collect_records():
    total_sheets = sum(len(source_cfg["sheets"]) for source_cfg in SOURCES.values())
    all_data = OrderedDict()

    print(f"[准备] 查找 bot9 Chrome (CDP:{CDP_PORT}) 中的腾讯文档 tab...")
    for source_name, source_cfg in SOURCES.items():
        ws_url = find_tab(CDP_PORT, source_cfg["doc_id"])
        if not ws_url:
            print(f"❌ 未找到已打开的 {source_name} tab。请先在 bot9 的 Chrome 中打开：")
            print(f"   {source_cfg['doc_url']}")
            sys.exit(1)
        print(f"   ✓ {source_name} 已打开")

    step_idx = 1
    for source_name, source_cfg in SOURCES.items():
        print(f"\n[来源] 连接 {source_name}...")
        ws_url = find_tab(CDP_PORT, source_cfg["doc_id"])
        cdp = CDPConnection(ws_url)
        source_headers = []
        seen_headers = set()
        source_records = []
        try:
            for sheet_name, sheet_cfg in source_cfg["sheets"].items():
                print(f"[{step_idx}/{total_sheets}] 提取 {sheet_name} (tab={sheet_cfg['tab']})...")
                text = extract_sheet_data(cdp, source_cfg["doc_url"], sheet_cfg["tab"])
                headers, rows = parse_tsv_rows(text)

                for header in headers:
                    if header not in seen_headers:
                        seen_headers.add(header)
                        source_headers.append(header)

                for row in rows:
                    source_records.append({
                        "列表名称": sheet_name,
                        "tab": sheet_cfg["tab"],
                        "row": row,
                    })

                print(f"   ✓ {len(rows)} 行，{len(headers)} 列")
                step_idx += 1
        finally:
            cdp.close()

        all_data[source_name] = {
            "headers": source_headers,
            "records": source_records,
        }

    return all_data


def write_source_csv(output_dir, source_name, source_data):
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{source_name}.csv"
    fieldnames = META_HEADERS + source_data["headers"]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for record in source_data["records"]:
            row = {
                "列表名称": record["列表名称"],
                "tab": record["tab"],
            }
            for header in source_data["headers"]:
                row[header] = record["row"].get(header, "")
            writer.writerow(row)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="从腾讯文档导出基金池到两个 CSV 文件")
    parser.add_argument("--dry-run", action="store_true", help="只预览统计，不写文件")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="CSV 输出目录")
    args = parser.parse_args()

    all_data = collect_records()
    total_rows = sum(len(source_data["records"]) for source_data in all_data.values())

    print(f"\n[汇总] 共提取 {total_rows} 行")
    if args.dry_run:
        print("[预览] 各 CSV 统计：")
        for source_name, source_data in all_data.items():
            print(
                f"- {source_name}: "
                f"{len(source_data['records'])} 行，"
                f"{len(source_data['headers'])} 个原始列"
            )
        print("\n--dry-run 未写文件")
        return

    for source_name, source_data in all_data.items():
        output_path = write_source_csv(args.output_dir, source_name, source_data)
        print(f"[输出] 已写入 {output_path}")
        print(f"[输出] 文件大小：{output_path.stat().st_size:,} 字节")


if __name__ == "__main__":
    main()
