#!/usr/bin/env python3
"""
enrich_fund_pool_c_share.py - 用 research-mcp 批量补全基金池里的 C 类份额

输入:
    workspace-bot9/skills/daily-market-recap/基金池.csv

输出:
    1. 基金池_含C类映射.csv       - 原始明细 + C 类映射字段
    2. 基金代码_C类映射.csv       - 去重后的基金代码映射表

实现路径:
    使用 research-mcp.query_segment 按基金名称批量反查 C 类名称/代码。
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path


DEFAULT_INPUT = Path("/home/rooot/.openclaw/workspace-bot9/skills/daily-market-recap/基金池.csv")
DEFAULT_OUTPUT = Path("/home/rooot/.openclaw/workspace-bot9/skills/daily-market-recap/基金池_含C类映射.csv")
DEFAULT_MAPPING_OUTPUT = Path("/home/rooot/.openclaw/workspace-bot9/skills/daily-market-recap/基金代码_C类映射.csv")
DEFAULT_MCPORTER_ROOT = Path("/home/rooot/.openclaw/workspace-bot11")

SHARE_CLASS_RE = re.compile(r"^(.*?)([A-Z])(\d+)?(?:类)?$")
NEW_COLUMNS = [
    "原始份额类型",
    "C类查询名",
    "C类基金代码",
    "C类基金简称",
    "C类匹配状态",
]


def detect_share_class(name):
    match = SHARE_CLASS_RE.match((name or "").strip())
    if not match:
        return "", "", (name or "").strip()

    base_name, share_class, series_num = match.groups()
    # 只把常见份额后缀当作份额类型；避免误伤基金名中的普通字母
    if share_class not in {"A", "B", "C", "D", "E", "F", "H", "I", "R", "Y"}:
        return "", "", (name or "").strip()
    return share_class, series_num or "", base_name


def build_c_candidates(name):
    raw_name = (name or "").strip()
    share_class, series_num, base_name = detect_share_class(raw_name)

    if share_class == "C":
        return share_class, [raw_name]

    candidates = []
    if share_class:
        if series_num:
            candidates.append(f"{base_name}C{series_num}")
        candidates.append(f"{base_name}C")
        candidates.append(f"{base_name}C类")
    else:
        candidates.append(f"{raw_name}C")
        candidates.append(f"{raw_name}C类")

    deduped = []
    seen = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return share_class, deduped


def load_unique_funds(input_path):
    unique_funds = OrderedDict()
    with input_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fund_code = (row.get("基金代码") or "").strip()
            fund_name = (row.get("基金简称") or "").strip()
            if not fund_code or not fund_name:
                continue
            unique_funds.setdefault(fund_code, fund_name)
    return unique_funds


def chunked(items, chunk_size):
    for idx in range(0, len(items), chunk_size):
        yield items[idx: idx + chunk_size]


def call_query_segment(mcporter_root, joined_names):
    cmd = [
        "npx",
        "mcporter",
        "call",
        "research-mcp.query_segment",
        f"user_inputs={joined_names}",
    ]
    result = subprocess.run(
        cmd,
        cwd=mcporter_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "mcporter 调用失败")
    return json.loads(result.stdout)


def batch_lookup_candidates(candidate_names, mcporter_root, batch_size=20, retry=2):
    resolved = {}
    total_batches = (len(candidate_names) + batch_size - 1) // batch_size if candidate_names else 0

    for batch_idx, batch in enumerate(chunked(candidate_names, batch_size), start=1):
        joined_names = "，".join(batch)
        print(f"[查询] 第 {batch_idx}/{total_batches} 批，{len(batch)} 个候选名称", flush=True)

        payload = None
        last_error = None
        for _ in range(retry + 1):
            try:
                payload = call_query_segment(mcporter_root, joined_names)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(0.5)

        if payload is None:
            print(f"  ✗ 本批失败：{last_error}", flush=True)
            continue

        list_fcode = {}
        for item in payload.get("data", []):
            list_fcode.update(item.get("listFcode") or {})

        for candidate_name in batch:
            if candidate_name in list_fcode:
                resolved[candidate_name] = {
                    "fund_name": candidate_name,
                    "fund_code": str(list_fcode[candidate_name]).strip(),
                }
    return resolved


def resolve_c_share_map(unique_funds, mcporter_root):
    fund_meta = OrderedDict()
    all_candidates = []

    for fund_code, fund_name in unique_funds.items():
        share_class, candidates = build_c_candidates(fund_name)
        fund_meta[fund_code] = {
            "fund_name": fund_name,
            "share_class": share_class,
            "candidates": candidates,
        }
        if share_class != "C":
            all_candidates.extend(candidates)

    ordered_candidates = list(OrderedDict.fromkeys(all_candidates))
    resolved_candidates = batch_lookup_candidates(ordered_candidates, mcporter_root)

    mapping = OrderedDict()
    for fund_code, meta in fund_meta.items():
        fund_name = meta["fund_name"]
        share_class = meta["share_class"]
        candidates = meta["candidates"]

        if share_class == "C":
            mapping[fund_code] = {
                "原始份额类型": "C",
                "C类查询名": fund_name,
                "C类基金代码": fund_code,
                "C类基金简称": fund_name,
                "C类匹配状态": "原本就是C类",
            }
            continue

        matched = None
        for candidate in candidates:
            if candidate in resolved_candidates:
                matched = resolved_candidates[candidate]
                break

        mapping[fund_code] = {
            "原始份额类型": share_class or "",
            "C类查询名": matched["fund_name"] if matched else (candidates[0] if candidates else ""),
            "C类基金代码": matched["fund_code"] if matched else "",
            "C类基金简称": matched["fund_name"] if matched else "",
            "C类匹配状态": "已匹配" if matched else "未找到C类",
        }

    return mapping


def write_mapping_csv(mapping_output_path, unique_funds, mapping):
    mapping_output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["基金代码", "基金简称"] + NEW_COLUMNS

    with mapping_output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for fund_code, fund_name in unique_funds.items():
            row = {
                "基金代码": fund_code,
                "基金简称": fund_name,
            }
            row.update(mapping[fund_code])
            writer.writerow(row)


def write_enriched_csv(input_path, output_path, mapping):
    with input_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    for column in NEW_COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            fund_code = (row.get("基金代码") or "").strip()
            extra = mapping.get(fund_code, {})
            for column in NEW_COLUMNS:
                row[column] = extra.get(column, "")
            writer.writerow(row)


def summarize(mapping):
    summary = {
        "原本就是C类": 0,
        "已匹配": 0,
        "未找到C类": 0,
    }
    for item in mapping.values():
        status = item["C类匹配状态"]
        summary[status] = summary.get(status, 0) + 1
    return summary


def main():
    parser = argparse.ArgumentParser(description="用 research-mcp 批量补全基金池里的 C 类份额")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="输入 CSV 路径")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="输出明细 CSV 路径")
    parser.add_argument("--mapping-output", type=Path, default=DEFAULT_MAPPING_OUTPUT, help="输出去重映射 CSV 路径")
    parser.add_argument("--mcporter-root", type=Path, default=DEFAULT_MCPORTER_ROOT, help="mcporter 配置所在目录")
    args = parser.parse_args()

    print(f"[读取] {args.input}", flush=True)
    unique_funds = load_unique_funds(args.input)
    print(f"[读取] 去重后共 {len(unique_funds)} 只基金", flush=True)

    mapping = resolve_c_share_map(unique_funds, args.mcporter_root)
    summary = summarize(mapping)

    write_mapping_csv(args.mapping_output, unique_funds, mapping)
    write_enriched_csv(args.input, args.output, mapping)

    print(f"[输出] 已写入 {args.mapping_output}", flush=True)
    print(f"[输出] 已写入 {args.output}", flush=True)
    print(
        "[汇总] "
        f"原本就是C类 {summary.get('原本就是C类', 0)} 只，"
        f"新匹配成功 {summary.get('已匹配', 0)} 只，"
        f"未找到C类 {summary.get('未找到C类', 0)} 只",
        flush=True,
    )


if __name__ == "__main__":
    main()
