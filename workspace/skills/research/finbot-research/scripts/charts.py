#!/usr/bin/env python3
"""
图表生成器 — 从 FinRobot chart_generator 提取核心图表
用法: echo '{"chart_type": "...", "data": {...}, "output_path": "/tmp/x.png", "ticker": "NVDA"}' | python3 charts.py

chart_type:
  revenue_ebitda  — 收入+EBITDA 趋势 (双轴柱线图)
  sensitivity     — 敏感性热力图
  peer_ev_ebitda  — 同行 EV/EBITDA 对比柱图
  football_field  — 估值区间足球场图

所有图表保存为 PNG，路径在输出 JSON 的 "path" 字段返回。
"""
import sys, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# 颜色规范
PRIMARY = "#0B1B33"
ACCENT = "#D2A74A"
TEXT = "#333333"
GRID = "#E0E0E0"
COLORS = [PRIMARY, ACCENT, "#666666", "#4A7C59", "#8B4513", "#2F4F4F"]

def setup_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9, "axes.titlesize": 11, "axes.titleweight": "bold",
        "axes.labelsize": 9, "axes.edgecolor": GRID, "axes.grid": True,
        "grid.color": GRID, "grid.linestyle": "--", "grid.alpha": 0.7,
        "figure.facecolor": "white", "savefig.facecolor": "white",
    })

def save(fig, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=150, facecolor="white")
    plt.close(fig)

# ────────── 图表类型 ──────────

def chart_revenue_ebitda(data, path, ticker):
    """收入+EBITDA 趋势: 柱图(Revenue) + 折线(EBITDA)"""
    years = data["years"]
    revenue = data["revenue"]
    ebitda = data["ebitda"]
    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(years))
    w = 0.5
    bars = ax1.bar(x, [r / 1e9 for r in revenue], w, color=PRIMARY, alpha=0.85, label="Revenue")
    ax1.set_ylabel("Revenue ($B)", color=TEXT)
    ax1.set_xticks(x)
    ax1.set_xticklabels(years, rotation=45)
    ax2 = ax1.twinx()
    ax2.plot(x, [e / 1e9 for e in ebitda], color=ACCENT, marker="o", linewidth=2, label="EBITDA")
    ax2.set_ylabel("EBITDA ($B)", color=ACCENT)
    ax1.set_title(f"{ticker} — Revenue & EBITDA Trend")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    fig.tight_layout()
    save(fig, path)

def chart_sensitivity(data, path, ticker):
    """二维敏感性热力图"""
    matrix = np.array(data["data"])
    rows = data["index"]
    cols = data["columns"]
    fig, ax = plt.subplots(figsize=(7, 5))
    mid = matrix[len(rows)//2, len(cols)//2]
    vmin, vmax = matrix.min(), matrix.max()
    im = ax.imshow(matrix / 1e9, cmap="RdYlGn", aspect="auto", vmin=vmin/1e9, vmax=vmax/1e9)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows, fontsize=8)
    ax.set_xlabel("EBITDA Margin Delta")
    ax.set_ylabel("Revenue Growth Delta")
    ax.set_title(f"{ticker} — Sensitivity Analysis (EBITDA $B, {data.get('target_year','')})")
    for i in range(len(rows)):
        for j in range(len(cols)):
            v = matrix[i, j] / 1e9
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7,
                    color="white" if abs(v - mid/1e9) > (vmax-vmin)/1e9*0.3 else "black")
    fig.colorbar(im, ax=ax, label="EBITDA ($B)")
    fig.tight_layout()
    save(fig, path)

def chart_peer_ev_ebitda(data, path, ticker):
    """同行 EV/EBITDA 对比柱图"""
    companies = data["companies"]
    multiples = data["multiples"]
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = [ACCENT if c == ticker else PRIMARY for c in companies]
    bars = ax.bar(companies, multiples, color=colors)
    avg = np.mean(multiples)
    ax.axhline(avg, color="#999", linestyle="--", linewidth=1, label=f"Avg: {avg:.1f}x")
    ax.set_ylabel("EV/EBITDA")
    ax.set_title(f"EV/EBITDA Peer Comparison")
    ax.legend()
    for bar, val in zip(bars, multiples):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f"{val:.1f}x", ha="center", fontsize=8)
    fig.tight_layout()
    save(fig, path)

def chart_football_field(data, path, ticker):
    """估值区间足球场图"""
    methods = [k for k in data if k != "current_price"]
    cp = data.get("current_price", 0)
    fig, ax = plt.subplots(figsize=(8, 3.5))
    y_pos = range(len(methods))
    for i, m in enumerate(methods):
        d = data[m]
        lo, mid, hi = d["low"], d["mid"], d["high"]
        ax.barh(i, hi - lo, left=lo, height=0.5, color=COLORS[i % len(COLORS)], alpha=0.6)
        ax.plot(mid, i, "D", color=COLORS[i % len(COLORS)], markersize=8)
        ax.text(hi + cp * 0.02, i, f"${mid:.0f}", va="center", fontsize=8)
    if cp > 0:
        ax.axvline(cp, color="red", linestyle="--", linewidth=1.5, label=f"Current: ${cp:.0f}")
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(methods)
    ax.set_xlabel("Price ($)")
    ax.set_title(f"{ticker} — Valuation Football Field")
    ax.legend(loc="lower right")
    fig.tight_layout()
    save(fig, path)

# ────────── 主入口 ──────────

CHART_MAP = {
    "revenue_ebitda": chart_revenue_ebitda,
    "sensitivity": chart_sensitivity,
    "peer_ev_ebitda": chart_peer_ev_ebitda,
    "football_field": chart_football_field,
}

def main():
    inp = json.load(sys.stdin)
    ct = inp.get("chart_type", "")
    data = inp.get("data", {})
    path = inp.get("output_path", f"/tmp/equity-charts/{ct}.png")
    ticker = inp.get("ticker", "")

    setup_style()

    fn = CHART_MAP.get(ct)
    if not fn:
        json.dump({"error": f"Unknown chart_type: {ct}", "available": list(CHART_MAP.keys())}, sys.stdout)
        return

    try:
        fn(data, path, ticker)
        json.dump({"ok": True, "chart_type": ct, "path": path}, sys.stdout)
    except Exception as e:
        json.dump({"error": str(e), "chart_type": ct}, sys.stdout)

if __name__ == "__main__":
    main()
