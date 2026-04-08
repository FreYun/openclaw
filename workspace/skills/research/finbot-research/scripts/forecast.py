#!/usr/bin/env python3
"""
财务预测引擎 — 从 FinRobot financial_data_processor 提取
用法: echo '{"historical": [...], "config": {...}}' | python3 forecast.py

输入 JSON:
  historical: list of dicts（每行一个指标，列名为年份如 "2022A","2023A","2024A"）
    [{"metrics": "Revenue", "2022A": 394328000000, "2023A": 383285000000, "2024A": 385603000000},
     {"metrics": "EBITDA", ...}, {"metrics": "EBITDA Margin", "2022A": "33.1%", ...},
     {"metrics": "Contribution Margin", ...}, {"metrics": "SG&A", ...},
     {"metrics": "EPS", ...}, {"metrics": "PE Ratio", ...}]
  config:
    revenue_base_year: "2024A"
    revenue_growth_assumptions: {"2025E": 0.05, "2026E": 0.06, "2027E": 0.07}
    margin_improvement: {"Contribution Margin": 0.005, "EBITDA Margin": 0.005}
    sga_margin_change: -0.003

输出 JSON:
  forecast: 完整 historical+forecast 表 (list of dicts)
  actual_years, forecast_years: 年份列表
  cagr: 收入历史 CAGR (str like "5.2%")
"""
import sys, json

def parse_pct(v):
    """'33.1%' -> 0.331;  直接 float -> 原值"""
    if isinstance(v, str) and "%" in v:
        return float(v.replace("%", "").replace(",", "")) / 100
    return None

def fmt_pct(v):
    return f"{v*100:.1f}%"

def get_row(rows, metric):
    for r in rows:
        if r.get("metrics") == metric:
            return r
    return None

def get_val(rows, metric, year):
    r = get_row(rows, metric)
    if r and year in r:
        v = r[year]
        if v is None:
            return None
        p = parse_pct(v) if isinstance(v, str) else None
        if p is not None:
            return p
        if isinstance(v, str):
            try:
                return float(v.replace(",", ""))
            except ValueError:
                return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    return None

def set_val(rows, metric, year, val):
    r = get_row(rows, metric)
    if r is None:
        r = {"metrics": metric}
        rows.append(r)
    r[year] = val

def main():
    data = json.load(sys.stdin)
    rows = [dict(r) for r in data.get("historical", [])]
    cfg = data.get("config", {})
    base_year = cfg.get("revenue_base_year", "")
    growth_assumptions = cfg.get("revenue_growth_assumptions", {})
    margin_imp = cfg.get("margin_improvement", {})
    sga_change = cfg.get("sga_margin_change", 0)

    # Collect years
    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())
    actual_years = sorted([k for k in all_keys if isinstance(k, str) and k.endswith("A") and k != "metrics"])
    forecast_years = sorted(growth_assumptions.keys())

    # 1) Revenue Growth for actual years
    prev_rev = None
    for y in actual_years:
        rv = get_val(rows, "Revenue", y)
        if prev_rev and rv and prev_rev > 0:
            g = (rv - prev_rev) / prev_rev
            set_val(rows, "Revenue Growth", y, fmt_pct(g))
        prev_rev = rv

    # 2) Forecast Revenue
    base_rev = get_val(rows, "Revenue", base_year)
    if base_rev:
        curr_rev = base_rev
        for fy in forecast_years:
            g = growth_assumptions[fy]
            curr_rev *= (1 + g)
            set_val(rows, "Revenue", fy, round(curr_rev, 2))
            set_val(rows, "Revenue Growth", fy, fmt_pct(g))

    # 3) Forecast Margins
    for metric, imp in margin_imp.items():
        bm = get_val(rows, metric, base_year)
        if bm is None:
            continue
        if bm > 1:  # stored as percentage number like 33.1
            bm = bm / 100
        curr_m = bm
        for fy in forecast_years:
            curr_m += imp
            set_val(rows, metric, fy, fmt_pct(curr_m))

    # 4) Forecast SG&A
    sga_m = get_val(rows, "SG&A Margin", base_year)
    if sga_m is not None:
        if sga_m > 1:
            sga_m = sga_m / 100
        curr_sga = sga_m
        for fy in forecast_years:
            curr_sga += sga_change
            set_val(rows, "SG&A Margin", fy, fmt_pct(curr_sga))
            rev = get_val(rows, "Revenue", fy)
            if rev:
                set_val(rows, "SG&A", fy, round(rev * curr_sga, 2))

    # 5) Back-calculate EBITDA
    for fy in forecast_years:
        rev = get_val(rows, "Revenue", fy)
        cm = get_val(rows, "Contribution Margin", fy)
        sga = get_val(rows, "SG&A", fy)
        if rev and cm is not None:
            if cm > 1:
                cm = cm / 100
            cp = rev * cm
            set_val(rows, "Contribution Profit", fy, round(cp, 2))
            set_val(rows, "Cost of Operations", fy, round(rev - cp, 2))
            if sga:
                ebitda = cp - sga
                set_val(rows, "EBITDA", fy, round(ebitda, 2))
                if rev > 0:
                    set_val(rows, "EBITDA Margin", fy, fmt_pct(ebitda / rev))

    # 6) Forecast EPS & PE
    base_eps = get_val(rows, "EPS", base_year)
    if base_eps:
        curr_eps = base_eps
        for fy in forecast_years:
            rg = growth_assumptions.get(fy, 0)
            mi = margin_imp.get("EBITDA Margin", 0)
            curr_eps *= (1 + rg) * (1 + mi)
            set_val(rows, "EPS", fy, round(curr_eps, 2))

    base_pe = get_val(rows, "PE Ratio", base_year)
    if base_pe:
        for i, fy in enumerate(forecast_years):
            pe = base_pe * (0.95 ** (i + 1))
            set_val(rows, "PE Ratio", fy, round(pe, 1))

    # 7) CAGR
    cagr_str = None
    if len(actual_years) >= 2:
        r0 = get_val(rows, "Revenue", actual_years[0])
        r1 = get_val(rows, "Revenue", actual_years[-1])
        try:
            n = int(actual_years[-1].replace("A", "")) - int(actual_years[0].replace("A", ""))
        except ValueError:
            n = 0
        if r0 and r1 and r0 > 0 and n > 0:
            cagr = (r1 / r0) ** (1 / n) - 1
            cagr_str = fmt_pct(cagr)

    output = {
        "forecast": rows,
        "actual_years": actual_years,
        "forecast_years": forecast_years,
        "cagr": cagr_str,
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
