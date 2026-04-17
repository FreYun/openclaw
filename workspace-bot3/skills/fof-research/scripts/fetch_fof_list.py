#!/usr/bin/env python3
"""
fetch_fof_list.py — 从 Tushare 拉取全市场公募 FOF,分类、合并份额,输出 fof_universe.json

运行: python3 skills/fof-research/scripts/fetch_fof_list.py
输出:
  - data/fof_universe.json   # 结构化全量
  - data/fof_summary.md      # 人眼浏览版

更新频率: 每月或新发行后手动跑。不要写进 cron,FOF 新发频率极低。

识别口径(Tushare 的 fund_type 枚举里没有 FOF,只能靠 name):
  - name 含 "FOF"  → 普通 FOF
  - name 含 "养老目标" → 养老目标 FOF (日期型 / 风险型)
  - name 含 "养老" 但不含 "养老目标" → 按其他类处理,不纳入(避免误伤非 FOF 的养老概念基金)
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import tushare as ts
except ImportError:
    sys.exit("请先安装 tushare: pip install tushare")

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_DIR = SKILL_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CRED_PATH = SKILL_DIR.parent.parent / "config" / "credentials" / "tushare.json"


def load_token() -> str:
    if not CRED_PATH.exists():
        sys.exit(f"找不到 {CRED_PATH},请先创建")
    return json.loads(CRED_PATH.read_text(encoding="utf-8"))["token"]


def fetch_all_oof_funds(pro) -> "pd.DataFrame":
    """分页拉取场外全量基金。Tushare fund_basic 单次上限 15000。"""
    import pandas as pd
    parts = []
    offset = 0
    while True:
        part = pro.fund_basic(market="O", offset=offset)
        if part is None or len(part) == 0:
            break
        parts.append(part)
        if len(part) < 15000:
            break
        offset += 15000
    return pd.concat(parts, ignore_index=True)


def classify(name: str) -> tuple[str, dict]:
    """
    返回 (category, meta)。
    category ∈ {
      '目标日期型', '目标风险型', '普通FOF', 'other'
    }
    meta 含解析出的关键属性(target_year / risk_level / hold_period)
    """
    meta: dict = {}

    # 持有期
    m = re.search(r"(一|二|三|四|五|六|七|八|九|十)年持有", name)
    if m:
        cn2num = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                  "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        meta["hold_period_years"] = cn2num[m.group(1)]

    # 目标日期型
    md = re.search(r"养老目标(?:日期)?(\d{4})", name)
    if md:
        meta["target_year"] = int(md.group(1))
        return "目标日期型", meta

    # 目标风险型 (必须带"养老目标")
    if "养老目标" in name:
        # "均衡" 和 "平衡" 同义,归入"平衡"
        for kw, level in [
            ("保守", "保守"), ("稳健", "稳健"),
            ("平衡", "平衡"), ("均衡", "平衡"),
            ("积极", "积极"), ("成长", "成长"),
        ]:
            if kw in name:
                meta["risk_level"] = level
                return "目标风险型", meta
        # 有"养老目标"但分不出风险级别
        return "目标风险型", meta

    # 显式 FOF 后缀但不含"养老目标"
    if "FOF" in name.upper():
        return "普通FOF", meta

    return "other", meta


def normalize_stem(name: str) -> str:
    """
    去掉份额后缀,得到合并键。
    份额常见后缀: 单字母 A/B/C/E/H/I/Q/Y,或数字,或 "美元", "人民币"
    """
    stem = name
    # 去掉末尾的单字母份额 (前面可能带空格或不带)
    stem = re.sub(r"\s*[A-Z]$", "", stem)
    # 去掉末尾的 "人民币/美元" 等份额类型
    stem = re.sub(r"(人民币|美元|现汇|现钞)$", "", stem)
    return stem.strip()


SHARE_PRIORITY = {"A": 1, "": 2, "C": 3, "E": 4, "Y": 5}


def share_class(name: str, stem: str) -> str:
    """从 name 尾部抽出份额字母,无则返回空串。"""
    tail = name[len(stem):].strip()
    if len(tail) == 1 and tail.isalpha():
        return tail.upper()
    return ""


def merge_shares(records: list[dict]) -> list[dict]:
    """把同一 FOF 的不同份额合并成一条,保留所有份额列表。"""
    by_stem: dict[str, list[dict]] = {}
    for r in records:
        stem = normalize_stem(r["name"])
        r["_stem"] = stem
        r["_share"] = share_class(r["name"], stem)
        by_stem.setdefault(stem, []).append(r)

    merged: list[dict] = []
    for stem, group in by_stem.items():
        # 代表份额: 优先 A 或无后缀,再按成立日最早
        group.sort(key=lambda x: (
            SHARE_PRIORITY.get(x["_share"], 99),
            x.get("found_date") or "99999999",
        ))
        rep = group[0]
        merged.append({
            "primary_code": rep["ts_code"],
            "primary_name": rep["name"],
            "stem": stem,
            "category": rep["category"],
            "target_year": rep.get("target_year"),
            "risk_level": rep.get("risk_level"),
            "hold_period_years": rep.get("hold_period_years"),
            "management": rep.get("management"),
            "custodian": rep.get("custodian"),
            "found_date": rep.get("found_date"),
            "issue_date": rep.get("issue_date"),
            "m_fee": rep.get("m_fee"),
            "c_fee": rep.get("c_fee"),
            "benchmark": rep.get("benchmark"),
            "status": rep.get("status"),
            "all_shares": [
                {
                    "code": x["ts_code"],
                    "name": x["name"],
                    "share": x["_share"],
                    "found_date": x.get("found_date"),
                }
                for x in group
            ],
            "share_count": len(group),
        })
    return merged


def build_summary_md(merged: list[dict], generated_at: str) -> str:
    lines = [
        "# FOF 宇宙总览",
        "",
        f"生成时间: {generated_at}",
        f"数据源: Tushare Pro `fund_basic(market='O')`",
        f"合并后 FOF 产品数: **{len(merged)}**",
        "",
        "## 按子类分布",
        "",
        "| 子类 | 数量 |",
        "|---|---|",
    ]
    cat_count: dict[str, int] = {}
    for r in merged:
        cat_count[r["category"]] = cat_count.get(r["category"], 0) + 1
    for c in ("普通FOF", "目标日期型", "目标风险型", "other"):
        if c in cat_count:
            lines.append(f"| {c} | {cat_count[c]} |")
    lines.append("")

    # 目标日期型按年份
    year_count: dict[int, int] = {}
    for r in merged:
        if r["category"] == "目标日期型" and r.get("target_year"):
            year_count[r["target_year"]] = year_count.get(r["target_year"], 0) + 1
    if year_count:
        lines += ["## 目标日期型 — 按目标年份", "", "| 目标年份 | 数量 |", "|---|---|"]
        for y in sorted(year_count):
            lines.append(f"| {y} | {year_count[y]} |")
        lines.append("")

    # 目标风险型按风险等级
    risk_count: dict[str, int] = {}
    for r in merged:
        if r["category"] == "目标风险型":
            risk_count[r.get("risk_level") or "未识别"] = \
                risk_count.get(r.get("risk_level") or "未识别", 0) + 1
    if risk_count:
        lines += ["## 目标风险型 — 按风险等级", "", "| 风险等级 | 数量 |", "|---|---|"]
        for lv in ("保守", "稳健", "平衡", "积极", "成长", "未识别"):
            if lv in risk_count:
                lines.append(f"| {lv} | {risk_count[lv]} |")
        lines.append("")

    # 基金公司 Top 10
    mgmt_count: dict[str, int] = {}
    for r in merged:
        mgmt_count[r.get("management") or "未知"] = \
            mgmt_count.get(r.get("management") or "未知", 0) + 1
    lines += ["## FOF 管理人 Top 10", "", "| 基金公司 | FOF 数量 |", "|---|---|"]
    for mgmt, cnt in sorted(mgmt_count.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"| {mgmt} | {cnt} |")
    lines.append("")

    lines += [
        "## 'other' 类(需人工校对)",
        "",
        "名字显式含 FOF 但不含'养老目标',或分类规则没覆盖到的:",
        "",
    ]
    others = [r for r in merged if r["category"] == "other"]
    for r in others:
        lines.append(f"- {r['primary_code']} | {r['primary_name']} | {r['management']}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    ts.set_token(load_token())
    pro = ts.pro_api()

    print("[1/4] 拉取 Tushare fund_basic(market='O') ...", flush=True)
    df = fetch_all_oof_funds(pro)
    print(f"       场外全量: {len(df)} 条", flush=True)

    print("[2/4] 按 name 过滤 FOF ...", flush=True)
    mask = df["name"].str.contains("FOF", case=False, na=False) | \
           df["name"].str.contains("养老目标", na=False)
    fof_df = df[mask].copy()
    print(f"       命中 FOF: {len(fof_df)} 条(份额未合并)", flush=True)

    records = []
    for _, row in fof_df.iterrows():
        category, meta = classify(row["name"])
        rec = {
            "ts_code": row["ts_code"],
            "name": row["name"],
            "management": row["management"],
            "custodian": row["custodian"],
            "found_date": row["found_date"],
            "issue_date": row["issue_date"],
            "m_fee": float(row["m_fee"]) if row["m_fee"] == row["m_fee"] else None,
            "c_fee": float(row["c_fee"]) if row["c_fee"] == row["c_fee"] else None,
            "benchmark": row["benchmark"],
            "status": row["status"],
            "category": category,
            **meta,
        }
        records.append(rec)

    print("[3/4] 合并份额 ...", flush=True)
    merged = merge_shares(records)
    print(f"       合并后产品: {len(merged)} 只", flush=True)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = {
        "generated_at": generated_at,
        "source": "Tushare Pro fund_basic(market='O')",
        "identification_rule": "name 含 'FOF' 或 '养老目标'",
        "total_raw_shares": len(records),
        "total_merged_products": len(merged),
        "products": merged,
    }

    json_path = DATA_DIR / "fof_universe.json"
    md_path = DATA_DIR / "fof_summary.md"
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_summary_md(merged, generated_at), encoding="utf-8")

    print(f"[4/4] 写出:", flush=True)
    print(f"       - {json_path}", flush=True)
    print(f"       - {md_path}", flush=True)


if __name__ == "__main__":
    main()
