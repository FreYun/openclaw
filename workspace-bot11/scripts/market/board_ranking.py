"""
板块涨跌排名
合并自 check_blocks.py + check_blocks_ak.py
默认使用 akshare，可通过参数切换到 tushare。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
from config import PREFERRED_DATA_SOURCE, get_tushare_pro


def get_industry_ranking_ak(top_n=30):
    """使用 akshare 获取行业板块涨跌排名"""
    import akshare as ak

    print("\n=== 行业板块涨跌排名 (akshare) ===")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        print("\n【同花顺行业板块】")
        df = ak.stock_board_industry_name_em()
        print(f"板块数量：{len(df)}")

        sorted_df = df.sort_values('涨跌幅', ascending=False)
        print(f"\n涨幅前 {top_n}：")
        print(sorted_df.head(top_n).to_string(index=False))
        print(f"\n跌幅前 {top_n}：")
        print(sorted_df.tail(top_n).to_string(index=False))
    except Exception as e:
        print(f"获取行业板块失败：{e}")


def get_concept_ranking_ak(top_n=20):
    """使用 akshare 获取概念板块涨跌排名"""
    import akshare as ak

    print("\n=== 概念板块涨跌排名 (akshare) ===")

    try:
        df = ak.stock_board_concept_name_em()
        print(f"概念板块数量：{len(df)}")

        sorted_df = df.sort_values('涨跌幅', ascending=False)
        print(f"\n涨幅前 {top_n}：")
        print(sorted_df.head(top_n).to_string(index=False))
        print(f"\n跌幅前 {top_n}：")
        print(sorted_df.tail(top_n).to_string(index=False))
    except Exception as e:
        print(f"获取概念板块失败：{e}")


def get_industry_ranking_ts():
    """使用 tushare 获取申万行业指数"""
    pro = get_tushare_pro()

    print("\n=== 申万行业指数 (tushare) ===")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        indices = pro.index_basic(market='SW')
        print(f"申万指数数量：{len(indices)}")
        print(indices.head(20).to_string(index=False))
    except Exception as e:
        print(f"获取申万指数失败：{e}")


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else PREFERRED_DATA_SOURCE

    if source == "akshare":
        get_industry_ranking_ak()
        get_concept_ranking_ak()
    elif source == "tushare":
        get_industry_ranking_ts()
    else:
        print(f"未知数据源：{source}，请使用 akshare 或 tushare")
