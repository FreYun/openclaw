"""
大盘指数概览 + 全市场涨跌统计
整理自 tushare_test.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
from config import get_tushare_pro


def get_index_overview(index_code='000001.SH', days=30):
    """
    获取大盘指数最新行情
    
    参数:
        index_code: 指数代码，默认上证指数
        days: 获取最近多少天的数据
    """
    pro = get_tushare_pro()
    end = datetime.now().strftime('%Y%m%d')
    start = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

    print("=" * 60)
    print(f"大盘指数概览 — {index_code}")
    print("=" * 60)

    try:
        df = pro.index_daily(ts_code=index_code, start_date=start, end_date=end)
        if df.empty:
            print("未获取到数据")
            return

        df = df.sort_values('trade_date', ascending=False)
        latest = df.iloc[0]

        print(f"\n最新交易日：{latest['trade_date']}")
        print(f"  收盘：{latest['close']:.2f} 点")
        print(f"  开盘：{latest['open']:.2f} 点")
        print(f"  最高：{latest['high']:.2f} 点")
        print(f"  最低：{latest['low']:.2f} 点")
        print(f"  涨跌额：{latest['change']:+.2f} 点")
        print(f"  涨跌幅：{latest['pct_chg']:+.2f}%")
        print(f"  成交量：{latest['vol']/10000:.2f} 万手")
        print(f"  成交额：{latest['amount']/100000000:.2f} 亿元")
    except Exception as e:
        print(f"获取指数数据失败：{e}")


def get_market_breadth(trade_date=None):
    """
    获取全市场涨跌家数统计
    
    参数:
        trade_date: 交易日期 YYYYMMDD，默认取最近交易日
    """
    pro = get_tushare_pro()

    if trade_date is None:
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        idx = pro.index_daily(ts_code='000001.SH', start_date=start, end_date=end)
        if idx.empty:
            print("无法确定最新交易日")
            return
        trade_date = idx.sort_values('trade_date', ascending=False).iloc[0]['trade_date']

    print(f"\n{'=' * 60}")
    print(f"全市场涨跌统计 — {trade_date}")
    print("=" * 60)

    try:
        df = pro.daily(trade_date=trade_date)
        if df.empty:
            print("未获取到数据")
            return

        up = len(df[df['pct_chg'] > 0])
        down = len(df[df['pct_chg'] < 0])
        flat = len(df[df['pct_chg'] == 0])
        limit_up = len(df[df['pct_chg'] >= 9.8])
        limit_down = len(df[df['pct_chg'] <= -9.8])

        print(f"\n  上涨：{up} 家")
        print(f"  下跌：{down} 家")
        print(f"  平盘：{flat} 家")
        if down > 0:
            print(f"  涨跌比：{up/down:.2f}")
        print(f"\n  涨停：{limit_up} 家")
        print(f"  跌停：{limit_down} 家")
    except Exception as e:
        print(f"统计失败：{e}")


if __name__ == "__main__":
    get_index_overview()
    get_market_breadth()
