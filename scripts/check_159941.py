#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询 159941.SZ 最近走势"""

import tushare as ts

pro = ts.pro_api()

# 获取 159941.SZ 前30个交易日的前复权日线数据
df = ts.pro_bar(
    ts_code='159941.SZ',
    adj='qfq',
    start_date='20250101',
    end_date='20260211',
    ma=[5, 10, 20],
    factors=['tor', 'vr']
)

if df is not None and not df.empty:
    print("159941.SZ（纳斯达克100ETF）最近走势：\n")
    print(df[['trade_date', 'open', 'high', 'low', 'close', 'pct_chg', 'vol', 'ma_5', 'ma_10', 'ma_20', 'tor', 'vr']].to_string(index=False))

    # 简单统计
    latest = df.iloc[0]
    print(f"\n最新交易日: {latest['trade_date']}")
    print(f"收盘价: {latest['close']:.2f}")
    print(f"涨跌幅: {latest['pct_chg']:.2f}%")
    print(f"5日均线: {latest['ma_5']:.2f}")
    print(f"换手率: {latest['tor']:.2f}%")
else:
    print("没有数据，可能原因：1）交易日期间无数据 2）积分不够 3）网络问题")
