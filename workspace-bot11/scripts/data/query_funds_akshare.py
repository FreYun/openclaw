# -*- coding: utf-8 -*-
"""
用 akshare 查指定基金：近一周净值 + 手续费（天天基金为前端申购费率）。
净值: fund_open_fund_info_em(symbol=六位代码, indicator="单位净值走势")
申购费: fund_purchase_em() 或 fund_open_fund_daily_em() 的「手续费」列，单位 %
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import akshare as ak

# 基金代码（东方财富/天天基金为 6 位）
FUNDS = ['024000', '007992', '021030', '167301']

def main():
    # 1) 近一周净值：开放式用 fund_open_fund_info_em，取最近约 5 个交易日
    print('========== 近一周净值 (akshare) ==========')
    for code in FUNDS:
        try:
            df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            if df is None or df.empty:
                print('\n%s: 无净值数据(或为场内需用 LOF 接口)' % code)
                continue
            df = df.tail(8)  # 近一周约 5~7 个交易日
            print('\n%s:' % code)
            for _, r in df.iterrows():
                print('  %s  单位净值: %s' % (r['净值日期'], r['单位净值']))
        except Exception as e:
            print('\n%s: %s' % (code, e))

    # 2) 手续费（天天基金为申购费）：fund_purchase_em 或 fund_open_fund_daily_em
    print('\n========== 手续费/申购费 (akshare) ==========')
    try:
        purchase = ak.fund_purchase_em()
        if purchase is not None and not purchase.empty:
            # 列名可能是 基金代码
            code_col = '基金代码' if '基金代码' in purchase.columns else purchase.columns[1]
            name_col = '基金简称' if '基金简称' in purchase.columns else purchase.columns[2]
            fee_col = '手续费' if '手续费' in purchase.columns else None
            for code in FUNDS:
                row = purchase[purchase[code_col].astype(str).str.strip() == code]
                if not row.empty and fee_col:
                    print('%s  %s  手续费(申购费): %s%%' % (code, row.iloc[0][name_col], row.iloc[0][fee_col]))
                else:
                    print('%s: 未在 fund_purchase_em 中找到' % code)
        else:
            print('fund_purchase_em 无数据')
    except Exception as e:
        print('fund_purchase_em 失败:', e)

    # 备用：开放式基金每日表也有手续费
    try:
        daily = ak.fund_open_fund_daily_em()
        if daily is not None and not daily.empty:
            print('\n(备用) fund_open_fund_daily_em 中上述基金的手续费:')
            code_col = [c for c in daily.columns if '代码' in c or c == '基金代码']
            code_col = code_col[0] if code_col else daily.columns[0]
            for code in FUNDS:
                row = daily[daily[code_col].astype(str).str.strip() == code]
                if not row.empty:
                    fee = row.iloc[0].get('手续费', row.iloc[0].get('手续费', ''))
                    name = row.iloc[0].get('基金简称', '')
                    print('  %s  %s  手续费: %s' % (code, name, fee))
    except Exception as e:
        print('fund_open_fund_daily_em:', e)

if __name__ == '__main__':
    main()
