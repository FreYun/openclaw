#!/usr/bin/env python3
"""
多方法估值引擎 — 从 FinRobot ValuationEngine 提取
用法: echo '{"financial_data": {...}, "peer_data": {...}, "assumptions": {...}}' | python3 valuation.py
输入 JSON:
  financial_data:
    ebitda (float): 最新 EBITDA
    current_price (float): 当前股价
    shares_outstanding (float): 总股数
    net_debt (float, optional): 净负债，默认 EV*10%
    free_cash_flow (float, optional): FCF，默认 EBITDA*60%
    hist_ev_ebitda (list[float], optional): 历史 EV/EBITDA 倍数序列
  peer_data (dict, optional):
    { "TICKER": {"ev_ebitda": float}, ... }
  assumptions (dict, optional):
    growth_rate_1_5, growth_rate_6_10, terminal_growth, wacc, projection_years
输出 JSON: {methods: [...], synthesis: {...}, football_field: {...}}
"""
import sys, json, math
import numpy as np

def ev_ebitda_valuation(fd, target_multiple=None):
    ebitda = fd.get("ebitda", 0)
    shares = fd.get("shares_outstanding", 1)
    hist = fd.get("hist_ev_ebitda", [])
    avg_m = np.mean(hist) if hist else 12.0
    std_m = np.std(hist) if len(hist) > 1 else 3.0
    m = target_multiple if target_multiple else avg_m
    ev = ebitda * m
    nd = fd.get("net_debt", ev * 0.1)
    eq = ev - nd
    tp = eq / shares if shares else 0
    lo = (ebitda * (m - std_m) - nd) / shares if shares else 0
    hi = (ebitda * (m + std_m) - nd) / shares if shares else 0
    return {
        "method": "EV/EBITDA",
        "target_price": max(tp, 0),
        "low_estimate": max(lo, 0),
        "high_estimate": max(hi, 0),
        "confidence": 0.7,
        "assumptions": {"ebitda": ebitda, "target_multiple": round(m, 2),
                        "hist_avg_multiple": round(avg_m, 2), "hist_std": round(std_m, 2)},
        "description": f"Based on {m:.1f}x EV/EBITDA multiple",
    }

def peer_comparison_valuation(fd, peer_data):
    if not peer_data:
        return {"method": "Peer Comparison", "target_price": 0, "low_estimate": 0,
                "high_estimate": 0, "confidence": 0, "assumptions": {}, "description": "No peer data"}
    multiples = [v["ev_ebitda"] for v in peer_data.values() if v.get("ev_ebitda")]
    if not multiples:
        return {"method": "Peer Comparison", "target_price": 0, "low_estimate": 0,
                "high_estimate": 0, "confidence": 0, "assumptions": {}, "description": "No valid peer multiples"}
    avg_m, min_m, max_m = np.mean(multiples), np.min(multiples), np.max(multiples)
    ebitda = fd.get("ebitda", 0)
    shares = fd.get("shares_outstanding", 1)
    nd = fd.get("net_debt", ebitda * avg_m * 0.1)
    tp = (ebitda * avg_m - nd) / shares if shares else 0
    lo = (ebitda * min_m - nd) / shares if shares else 0
    hi = (ebitda * max_m - nd) / shares if shares else 0
    return {
        "method": "Peer Comparison",
        "target_price": max(tp, 0),
        "low_estimate": max(lo, 0),
        "high_estimate": max(hi, 0),
        "confidence": 0.6,
        "assumptions": {"peer_avg": round(avg_m, 2), "peer_range": f"{min_m:.1f}x-{max_m:.1f}x",
                        "num_peers": len(multiples)},
        "description": f"Based on {len(multiples)} peer companies",
    }

def dcf_valuation(fd, assumptions=None):
    defaults = {"growth_rate_1_5": 0.10, "growth_rate_6_10": 0.05,
                "terminal_growth": 0.025, "wacc": 0.10, "projection_years": 10}
    a = {**defaults, **(assumptions or {})}
    fcf = fd.get("free_cash_flow") or fd.get("ebitda", 0) * 0.6
    shares = fd.get("shares_outstanding", 1)
    wacc = a["wacc"]
    pv_fcf = 0
    curr = fcf
    for yr in range(1, a["projection_years"] + 1):
        g = a["growth_rate_1_5"] if yr <= 5 else a["growth_rate_6_10"]
        curr *= (1 + g)
        pv_fcf += curr / ((1 + wacc) ** yr)
    tv = curr * (1 + a["terminal_growth"]) / (wacc - a["terminal_growth"])
    pv_tv = tv / ((1 + wacc) ** a["projection_years"])
    ev = pv_fcf + pv_tv
    nd = fd.get("net_debt", ev * 0.1)
    eq = ev - nd
    tp = eq / shares if shares else 0
    # WACC ±1% sensitivity
    lo_tv = tv / ((1 + wacc + 0.01) ** a["projection_years"])
    hi_tv = tv / ((1 + wacc - 0.01) ** a["projection_years"])
    lo = (pv_fcf + lo_tv - nd) / shares if shares else 0
    hi = (pv_fcf + hi_tv - nd) / shares if shares else 0
    return {
        "method": "DCF",
        "target_price": max(tp, 0),
        "low_estimate": max(lo, 0),
        "high_estimate": max(hi, 0),
        "confidence": 0.5,
        "assumptions": a,
        "description": f"Based on {wacc*100:.1f}% WACC, {a['projection_years']}yr projection",
    }

def synthesize(results, current_price):
    valid = [r for r in results if r["target_price"] > 0]
    if not valid:
        return {"target_price": 0, "range": [0, 0], "upside_pct": 0, "methods_used": 0}
    tw = sum(r["confidence"] for r in valid)
    wp = sum(r["target_price"] * r["confidence"] for r in valid) / tw
    lo = min(r["low_estimate"] for r in valid)
    hi = max(r["high_estimate"] for r in valid)
    upside = ((wp / current_price) - 1) * 100 if current_price > 0 else 0
    return {
        "target_price": round(wp, 2),
        "range": [round(lo, 2), round(hi, 2)],
        "current_price": current_price,
        "upside_pct": round(upside, 1),
        "methods_used": len(valid),
    }

def football_field(results, current_price):
    ff = {}
    for r in results:
        if r["target_price"] > 0:
            ff[r["method"]] = {"low": round(r["low_estimate"], 2),
                               "mid": round(r["target_price"], 2),
                               "high": round(r["high_estimate"], 2)}
    ff["current_price"] = current_price
    return ff

def main():
    data = json.load(sys.stdin)
    fd = data.get("financial_data", {})
    pd_data = data.get("peer_data", {})
    assumptions = data.get("assumptions", {})
    cp = fd.get("current_price", 0)

    results = [
        ev_ebitda_valuation(fd),
        peer_comparison_valuation(fd, pd_data),
        dcf_valuation(fd, assumptions),
    ]

    output = {
        "methods": results,
        "synthesis": synthesize(results, cp),
        "football_field": football_field(results, cp),
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
