#!/usr/bin/env python3
"""
老詹的组合 - 日内收益率预估
用跟踪指数的实时涨跌幅估算各基金及组合整体的日内收益率

用法:
  python3 portfolio_intraday.py          # 终端输出
  python3 portfolio_intraday.py --json   # JSON 输出（供前端调用）
  python3 portfolio_intraday.py --serve  # 启动 HTTP 服务（含前端）
"""

import akshare as ak
import json
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ============================================================
# 持仓定义：基金 -> 跟踪指数映射
# ============================================================
POSITIONS = [
    # (基金代码, 名称, 方向, 成本净值, 仓位%, 指数源, 指数代码)
    # 指数源: "a" = A股指数, "hk" = 港股指数, "global" = 全球指数, "etf" = ETF代理
    ("000051", "华夏沪深300联接A",     "沪深300",    1.5558, 15.94, "a",  "000300"),
    ("021243", "富国央企红利联接A",   "央企红利",   1.036,  11.68, "a",  "000825"),
    ("006327", "易方达中概互联联接A", "中概互联",   0.9776,  9.86, "a",  "H30533"),
    ("110026", "易方达创业板联接A",   "创业板",     2.1929,  9.26, "a",  "399006"),
    ("022627", "博时A100联接A",       "A100",       1.1394,  9.25, "a",  "000903"),
    ("001631", "天弘食品饮料联接A",   "食品饮料",   1.3323,  7.79, "a",  "930653"),
    ("011609", "易方达科创50联接C",   "科创50",     0.842,   7.45, "a",  "000688"),
    ("013127", "汇添富恒生科技联接A", "恒生科技",   0.9084,  3.56, "hk", "HSTECH"),
    ("025490", "平安卫星产业A",       "卫星产业",   1.2562,  3.06, "a",  "931594"),
    ("167301", "方正富邦保险A",       "保险",       0.9305,  2.98, "a",  "399809"),
    ("021030", "汇添富创新药联接A",   "创新药",     1.6878,  1.92, "a",  "987018"),
    ("018043", "天弘纳斯达克100A",    "纳斯达克",   1.8896,  1.33, "global", "NDX"),
    ("007992", "华安证券公司联接A",   "券商",       1.3006,  1.26, "a",  "399975"),
    ("000217", "华安黄金联接C",       "黄金",       1.7535,  0.70, "etf", "518880"),
    ("016630", "易方达中证1000联接A", "中证1000",   1.1406,  0.57, "a",  "000852"),
    ("021985", "财通先进制造A",       "先进制造",   1.8596,  0.57, "a",  "930850"),
]

CASH_WEIGHT = 12.82

INDEX_DISPLAY_NAMES = {
    "HSTECH": "恒生科技指数",
    "NDX": "纳斯达克100",
    "H30533": "中国互联网50",
    "930653": "中证食品饮料",
    "987018": "港股通创新药",
    "930850": "智能制造",
}

# 分类
CATEGORIES = {
    "宽基指数": ["000300", "000825", "399006", "000903", "000688"],
    "港股/海外": ["H30533", "HSTECH", "NDX"],
    "行业主题": ["930653", "931594", "399809", "987018", "399975", "930850"],
    "小盘": ["000852"],
    "商品": ["518880"],
}

def _category_of(idx_code):
    for cat, codes in CATEGORIES.items():
        if idx_code in codes:
            return cat
    return "其他"


# ============================================================
# 数据获取
# ============================================================

def fetch_a_indices():
    result = {}
    for market in ["上证系列指数", "深证系列指数", "中证系列指数"]:
        try:
            df = ak.stock_zh_index_spot_em(symbol=market)
            for _, row in df.iterrows():
                result[row['代码']] = {
                    'name': row['名称'],
                    'pct': float(row['涨跌幅']) if row['涨跌幅'] is not None else 0.0,
                    'price': float(row['最新价']) if row['最新价'] is not None else 0.0,
                }
        except Exception as e:
            print(f"  [WARN] 获取 {market} 失败: {e}", file=sys.stderr)
    return result


def fetch_hk_indices():
    result = {}
    try:
        df = ak.stock_hk_index_spot_em()
        for _, row in df.iterrows():
            result[row['代码']] = {
                'name': row['名称'],
                'pct': float(row['涨跌幅']) if row['涨跌幅'] is not None else 0.0,
                'price': float(row['最新价']) if row['最新价'] is not None else 0.0,
            }
    except Exception as e:
        print(f"  [WARN] 获取港股指数失败: {e}", file=sys.stderr)
    return result


def fetch_global_indices():
    result = {}
    try:
        df = ak.index_global_spot_em()
        for _, row in df.iterrows():
            result[row['代码']] = {
                'name': row['名称'],
                'pct': float(row['涨跌幅']) if row['涨跌幅'] is not None else 0.0,
                'price': float(row['最新价']) if row['最新价'] is not None else 0.0,
            }
    except Exception as e:
        print(f"  [WARN] 获取全球指数失败: {e}", file=sys.stderr)
    return result


def fetch_etf_spot():
    result = {}
    try:
        df = ak.fund_etf_spot_em()
        for _, row in df.iterrows():
            result[str(row['代码'])] = {
                'name': row['名称'],
                'pct': float(row['涨跌幅']) if row['涨跌幅'] is not None else 0.0,
                'price': float(row['最新价']) if row['最新价'] is not None else 0.0,
            }
    except Exception as e:
        print(f"  [WARN] 获取ETF行情失败: {e}", file=sys.stderr)
    return result


# ============================================================
# 核心计算
# ============================================================

def compute_portfolio():
    """计算组合日内收益，返回结构化 dict"""
    sources_needed = set(p[5] for p in POSITIONS)
    data = {}

    if "a" in sources_needed:
        data['a'] = fetch_a_indices()
    if "hk" in sources_needed:
        data['hk'] = fetch_hk_indices()
    if "global" in sources_needed:
        data['global'] = fetch_global_indices()
    if "etf" in sources_needed:
        data['etf'] = fetch_etf_spot()

    total_pct = 0.0
    items = []
    missing = []

    for code, name, direction, avg_nav, weight, source, idx_code in POSITIONS:
        source_data = data.get(source, {})
        idx_info = source_data.get(idx_code)

        if idx_info is None:
            missing.append(f"{direction}({idx_code})")
            pct = 0.0
            idx_name = "未获取"
            idx_price = 0.0
        else:
            pct = idx_info['pct']
            idx_name = INDEX_DISPLAY_NAMES.get(idx_code, idx_info['name'])
            idx_price = idx_info['price']

        contribution = weight * pct / 100.0
        total_pct += contribution

        items.append({
            "fund_code": code,
            "fund_name": name,
            "direction": direction,
            "avg_nav": avg_nav,
            "weight": weight,
            "index_code": idx_code,
            "index_name": idx_name,
            "index_price": idx_price,
            "index_pct": round(pct, 4),
            "contribution": round(contribution, 4),
            "category": _category_of(idx_code),
        })

    # 按分类汇总
    cat_summary = {}
    for item in items:
        cat = item["category"]
        if cat not in cat_summary:
            cat_summary[cat] = {"weight": 0, "contribution": 0}
        cat_summary[cat]["weight"] += item["weight"]
        cat_summary[cat]["contribution"] += item["contribution"]

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positions": items,
        "cash_weight": CASH_WEIGHT,
        "total_pct": round(total_pct, 4),
        "category_summary": {k: {"weight": round(v["weight"], 2), "contribution": round(v["contribution"], 4)} for k, v in cat_summary.items()},
        "missing": missing,
    }


# ============================================================
# 终端输出
# ============================================================

def print_terminal(result):
    now = result["timestamp"]
    print(f"{'='*70}")
    print(f"  老詹的组合 - 日内收益率预估")
    print(f"  时间: {now}")
    print(f"{'='*70}\n")

    print(f"  {'方向':<14} {'仓位':>6} {'指数涨跌':>8} {'贡献':>8}  {'跟踪指数'}")
    print(f"  {'─'*14} {'─'*6} {'─'*8} {'─'*8}  {'─'*20}")

    for item in result["positions"]:
        pct_str = f"{item['index_pct']:+.2f}%"
        contrib_str = f"{item['contribution']:+.4f}%"
        print(f"  {item['direction']:<14} {item['weight']:>5.2f}% {pct_str:>8} {contrib_str:>8}  {item['index_name']}")

    print(f"  {'─'*14} {'─'*6} {'─'*8} {'─'*8}")
    print(f"  {'现金':<14} {CASH_WEIGHT:>5.2f}%  {'0.00%':>7} {'0.0000%':>8}")
    print(f"  {'─'*14} {'─'*6} {'─'*8} {'─'*8}")
    print(f"  {'组合预估':<12} {'100%':>6} {'':>8} {result['total_pct']:>+.4f}%")
    print()

    base = 100000
    est_pnl = base * result['total_pct'] / 100
    print(f"  若账户总资产 10 万元，今日预估盈亏: {est_pnl:+.2f} 元")
    print()

    if result["missing"]:
        print(f"  ⚠ 以下指数未获取到数据，按 0% 计算: {', '.join(result['missing'])}")
        print()

    print(f"  注意: 联接基金实际收益会因申赎费、仓位比例（通常 90-95%）、")
    print(f"        跟踪误差等因素与指数略有偏差")


# ============================================================
# HTTP 服务
# ============================================================

class PortfolioHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/portfolio":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            result = compute_portfolio()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
        elif self.path == "/" or self.path == "/index.html":
            html_path = Path(__file__).parent / "portfolio.html"
            if html_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_path.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"portfolio.html not found")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def serve(port=18086):
    server = HTTPServer(("0.0.0.0", port), PortfolioHandler)
    print(f"  组合看板已启动: http://localhost:{port}")
    print(f"  API 地址: http://localhost:{port}/api/portfolio")
    print(f"  按 Ctrl+C 停止\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  已停止")
        server.server_close()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    if "--json" in sys.argv:
        result = compute_portfolio()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "--serve" in sys.argv:
        port = 18086
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        serve(port)
    else:
        result = compute_portfolio()
        print_terminal(result)
