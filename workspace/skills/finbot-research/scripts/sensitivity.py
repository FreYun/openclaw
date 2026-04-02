#!/usr/bin/env python3
"""
敏感性分析器 — 从 FinRobot SensitivityAnalyzer 提取
用法: echo '{"base_forecast": [...], "revenue_range": [-0.05,0.05], "margin_range": [-0.02,0.02], "steps": 5}' | python3 sensitivity.py

输入 JSON:
  base_forecast: list of dicts, 每行一个指标
    [{"metrics": "Revenue", "2024A": 100000, "2025E": 105000, ...},
     {"metrics": "EBITDA", ...},
     {"metrics": "EBITDA Margin", "2024A": "22.5%", ...}]
  revenue_range: [min_delta, max_delta]  (如 [-0.05, 0.05])
  margin_range:  [min_delta, max_delta]  (如 [-0.02, 0.02])
  steps: int (默认 5)

输出 JSON:
  revenue_sensitivity: [{growth_delta, year: adjusted_rev, ...}, ...]
  margin_sensitivity: [{margin_delta, year_ebitda_margin, year_ebitda, ...}, ...]
  combined_matrix: {index_col: "Revenue Growth", columns: ["Margin -2.0%"...], data: [[...]]}
  confidence_intervals: {metric: {base, lower, upper, confidence}, ...}
  assumptions: {year: {revenue_growth, ebitda_margin}, ...}
"""
import sys, json
import numpy as np

def parse_pct(v):
    if isinstance(v, str) and "%" in v:
        return float(v.replace("%", "").replace(",", ""))
    try:
        return float(v)
    except:
        return None

def get_val(rows, metric, year):
    for r in rows:
        if r.get("metrics") == metric and year in r:
            v = r[year]
            if v is None:
                return None
            if isinstance(v, str):
                v = v.replace(",", "").replace("%", "")
            try:
                return float(v)
            except:
                return None
    return None

def forecast_years(rows):
    yrs = set()
    for r in rows:
        for k in r:
            if isinstance(k, str) and k.endswith("E"):
                yrs.add(k)
    return sorted(yrs)

def revenue_sensitivity(rows, rev_range, steps):
    fyrs = forecast_years(rows)
    base = {y: get_val(rows, "Revenue", y) for y in fyrs}
    base = {y: v for y, v in base.items() if v is not None}
    if not base:
        return []
    deltas = np.linspace(rev_range[0], rev_range[1], steps)
    results = []
    for d in deltas:
        row = {"growth_delta": f"{d*100:+.1f}%"}
        for y, bv in base.items():
            row[y] = round(bv * (1 + d), 2)
        results.append(row)
    return results

def margin_sensitivity(rows, mar_range, steps):
    fyrs = forecast_years(rows)
    base_margins = {}
    for y in fyrs:
        m = get_val(rows, "EBITDA Margin", y)
        if m is not None:
            base_margins[y] = m  # already as percentage number like 22.5
    if not base_margins:
        return []
    deltas = np.linspace(mar_range[0], mar_range[1], steps)
    results = []
    for d in deltas:
        row = {"margin_delta": f"{d*100:+.1f}%"}
        for y, bm in base_margins.items():
            adj = bm + d * 100  # percentage points
            row[f"{y}_ebitda_margin"] = f"{adj:.1f}%"
            rev = get_val(rows, "Revenue", y)
            if rev:
                row[f"{y}_ebitda"] = round(rev * adj / 100, 2)
        results.append(row)
    return results

def combined_matrix(rows, rev_range, mar_range, steps):
    fyrs = forecast_years(rows)
    if not fyrs:
        return {}
    ty = fyrs[-1]
    base_rev = get_val(rows, "Revenue", ty)
    base_mar = get_val(rows, "EBITDA Margin", ty)
    if base_rev is None or base_mar is None:
        return {}
    rd = np.linspace(rev_range[0], rev_range[1], steps)
    md = np.linspace(mar_range[0], mar_range[1], steps)
    cols = [f"Margin {d*100:+.1f}%" for d in md]
    data = []
    index = []
    for r in rd:
        label = f"{r*100:+.1f}%"
        index.append(label)
        row_vals = []
        for m in md:
            adj_rev = base_rev * (1 + r)
            adj_mar = base_mar + m * 100
            ebitda = adj_rev * adj_mar / 100
            row_vals.append(round(ebitda, 2))
        data.append(row_vals)
    return {"target_year": ty, "index_label": "Revenue Growth",
            "columns": cols, "index": index, "data": data}

def confidence_intervals(rows, metrics=None, confidence_levels=None):
    if metrics is None:
        metrics = ["Revenue", "EBITDA"]
    if confidence_levels is None:
        confidence_levels = [0.90, 0.95, 0.99]
    z_map = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    fyrs = forecast_years(rows)
    if not fyrs:
        return {}
    ty = fyrs[-1]
    result = {}
    for metric in metrics:
        bv = get_val(rows, metric, ty)
        if bv is None:
            continue
        std_ratio = 0.15
        cis = {}
        for cl in confidence_levels:
            z = z_map.get(cl, 1.96)
            moe = bv * std_ratio * z
            cis[f"{cl*100:.0f}%"] = {"lower": round(bv - moe, 2), "upper": round(bv + moe, 2)}
        result[metric] = {"base": round(bv, 2), "target_year": ty, "intervals": cis}
    return result

def extract_assumptions(rows):
    fyrs = forecast_years(rows)
    out = {}
    for y in fyrs:
        a = {}
        rg = get_val(rows, "Revenue Growth", y)
        if rg is not None:
            a["revenue_growth"] = f"{rg:.1f}%"
        em = get_val(rows, "EBITDA Margin", y)
        if em is not None:
            a["ebitda_margin"] = f"{em:.1f}%"
        if a:
            out[y] = a
    return out

def main():
    data = json.load(sys.stdin)
    rows = data.get("base_forecast", [])
    rr = data.get("revenue_range", [-0.05, 0.05])
    mr = data.get("margin_range", [-0.02, 0.02])
    steps = data.get("steps", 5)

    output = {
        "revenue_sensitivity": revenue_sensitivity(rows, rr, steps),
        "margin_sensitivity": margin_sensitivity(rows, mr, steps),
        "combined_matrix": combined_matrix(rows, rr, mr, steps),
        "confidence_intervals": confidence_intervals(rows),
        "assumptions": extract_assumptions(rows),
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
