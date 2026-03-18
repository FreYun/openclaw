# -*- coding: utf-8 -*-
# 按申购金额、确认日净值、申购费率重新计算份额和手续费。费率来自 akshare「手续费」列（%），f = 手续费/100，不再乘其他系数。

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import akshare as ak

def _em_code(ts_code):
    return str(ts_code).split(".")[0].strip()

def get_fee_pct_akshare(ts_code):
    """从 akshare fund_purchase_em() 取「手续费」列（单位 %），无则试 fund_open_fund_daily_em()。返回小数如 0.1 表示 0.1%。"""
    code = _em_code(ts_code)
    if not code:
        return None
    try:
        df = ak.fund_purchase_em()
        if df is not None and not df.empty and "基金代码" in df.columns and "手续费" in df.columns:
            row = df[df["基金代码"].astype(str).str.strip() == code]
            if not row.empty:
                v = row.iloc[0]["手续费"]
                if v is not None and str(v).strip() != "" and str(v) != "nan":
                    return float(v)
        df = ak.fund_open_fund_daily_em()
        if df is not None and not df.empty:
            code_col = [c for c in df.columns if "代码" in c][0] if any("代码" in c for c in df.columns) else df.columns[0]
            row = df[df[code_col].astype(str).str.strip() == code]
            if not row.empty and "手续费" in df.columns:
                v = row.iloc[0]["手续费"]
                if v is not None and str(v).strip() and str(v) != "nan":
                    s = str(v).replace("%", "").strip()
                    if s:
                        return float(s)
    except Exception:
        pass
    return None

# 配置：code, name, amount(申购金额), nav(确认日净值)；费率由 akshare 拉取，若拉不到可在此写 fee_pct（% 数值，如 0.1 表示 0.1%）
funds = [
    {'code': '024000.OF', 'name': '农银科创板 50', 'amount': 500, 'nav': 1.3823},
    {'code': '007992.OF', 'name': '华夏证券 ETF', 'amount': 500, 'nav': 1.2505},
    {'code': '021030.OF', 'name': '汇添富创新药', 'amount': 500, 'nav': 1.5696},
    {'code': '167301.OF', 'name': '方正富邦保险', 'amount': 1000, 'nav': 1.157},
]

print("重新计算份额和手续费（费率来自 akshare 手续费列，f = 手续费/100）")
print("=" * 80)
header = "{:<20} {:>8} {:>8} {:>8} {:>10} {:>12} {:>10}".format(
    "基金", "金额", "净值", "费率%", "净额", "份额", "手续费")
print(header)
print("=" * 80)

total_fee = 0
results = []

for f in funds:
    fee_pct = f.get("fee_pct")
    if fee_pct is None:
        fee_pct = get_fee_pct_akshare(f["code"])
    if fee_pct is None:
        print("{}: 未取到费率，跳过".format(f["name"]))
        continue
    fee_rate = fee_pct / 100.0  # 手续费已是 %，如 0.1 表示 0.1%，f = 0.001
    amount = f["amount"]
    nav = f["nav"]

    net_amount = amount / (1 + fee_rate)
    units = net_amount / nav
    fee = amount - net_amount

    total_fee += fee

    results.append({
        "code": f["code"],
        "name": f["name"],
        "amount": amount,
        "nav": nav,
        "fee_rate": fee_rate,
        "fee_pct": fee_pct,
        "net_amount": net_amount,
        "units": units,
        "fee": fee
    })

    line = "{:<20} {:>8.2f} {:>8.4f} {:>7.2f} {:>10.2f} {:>12.2f} {:>10.2f}".format(
        f["name"], amount, nav, fee_pct, net_amount, units, fee)
    print(line)

print('=' * 80)
print('总手续费：{:.2f} 元'.format(total_fee))
print()
print('详细数据（JSON 格式）:')
import json
print(json.dumps(results, ensure_ascii=False, indent=2))
