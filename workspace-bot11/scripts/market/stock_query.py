"""
按板块查询个股行情
合并自 stock_query.py + tushare_query.py
默认使用 akshare，可通过参数切换到 tushare。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
from config import PREFERRED_DATA_SOURCE, get_tushare_pro

WATCHLIST = {
    '银行': {
        '600036': '招商银行', '601166': '兴业银行', '601939': '建设银行',
        '601288': '农业银行', '600919': '江苏银行',
    },
    '存储芯片': {
        '688525': '佰维存储', '301308': '江波龙', '688008': '澜起科技',
    },
    'PCB': {
        '300476': '胜宏科技', '002384': '东山精密', '002916': '深南电路',
        '000636': '风华高科',
    },
    '半导体': {
        '688256': '寒武纪', '688981': '中芯国际', '688041': '海光信息',
    },
    '油气': {
        '601857': '中国石油', '600028': '中国石化', '600938': '中国海油',
    },
    '航运': {
        '600026': '中远海能', '601872': '招商轮船', '601919': '中远海控',
    },
}


def query_ak(watchlist=None):
    """使用 akshare 查询个股行情"""
    import akshare as ak

    watchlist = watchlist or WATCHLIST
    print(f"数据获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("数据源：akshare")
    print("=" * 80)

    all_data = []
    for sector, stocks in watchlist.items():
        print(f"\n【{sector}】")
        print("-" * 60)

        for code, name in stocks.items():
            try:
                df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
                if len(df) == 0:
                    continue
                df = df.tail(5)
                latest = df.iloc[-1]

                today_chg = latest['涨跌幅']
                three_day_chg = ((latest['收盘'] / df.iloc[-4]['收盘']) - 1) * 100 if len(df) >= 4 else today_chg

                print(f"{name}({code}): 今日 {today_chg:+.2f}% | 3天 {three_day_chg:+.2f}% | 收盘 {latest['收盘']:.2f}")
                all_data.append({
                    '板块': sector, '代码': code, '名称': name,
                    '今日%': today_chg, '3天%': three_day_chg, '收盘价': latest['收盘'],
                })
            except Exception as e:
                print(f"{name}({code}): 获取失败 - {str(e)[:40]}")

    return pd.DataFrame(all_data)


def query_ts(watchlist=None):
    """使用 tushare 查询个股行情"""
    pro = get_tushare_pro()
    watchlist = watchlist or WATCHLIST

    today = datetime.now().strftime('%Y%m%d')
    start = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

    print(f"数据获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("数据源：tushare")
    print("=" * 80)

    for sector, stocks in watchlist.items():
        print(f"\n【{sector}】")
        print("-" * 60)

        for code, name in stocks.items():
            ts_code = code + (".SH" if code.startswith("6") else ".SZ")
            try:
                df = pro.daily(ts_code=ts_code, start_date=start, end_date=today)
                if len(df) == 0:
                    continue
                df = df.sort_values('trade_date').reset_index(drop=True)
                latest = df.iloc[-1]

                three_day_chg = ((latest['close'] / df.iloc[0]['close']) - 1) * 100 if len(df) >= 2 else latest['pct_chg']

                print(f"{name}({ts_code}): 今日 {latest['pct_chg']:+.2f}% | 3天 {three_day_chg:+.2f}% | 收盘 {latest['close']:.2f}")
            except Exception as e:
                print(f"{name}({ts_code}): 获取失败 - {str(e)[:40]}")


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else PREFERRED_DATA_SOURCE

    if source == "akshare":
        query_ak()
    elif source == "tushare":
        query_ts()
    else:
        print(f"未知数据源：{source}")
