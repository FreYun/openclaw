"""
V 型反转板块扫描
合并自 find_v_shape.py + find_v_shape2.py
扫描当日概念板块，找出高振幅但收盘上涨的板块（疑似 V 型反转）。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd
from datetime import datetime


def scan_v_shape(amplitude_threshold=4.0, gain_range=(0, 3)):
    """
    扫描 V 型反转概念板块
    
    参数:
        amplitude_threshold: 最小振幅（%），默认 4%
        gain_range: 涨幅范围 (min%, max%)，默认 0~3%
    """
    print("=== V 型反转板块扫描 ===")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"筛选条件：振幅 > {amplitude_threshold}%，涨幅 {gain_range[0]}% ~ {gain_range[1]}%")

    concept_df = ak.stock_board_concept_name_em()
    print(f"\n概念板块总数：{len(concept_df)}")

    sorted_df = concept_df.sort_values('涨跌幅', ascending=False)
    print(f"\n【涨幅前 20】")
    print(sorted_df.head(20)[['板块名称', '涨跌幅', '涨跌额']].to_string(index=False))

    print(f"\n【跌幅前 20】")
    print(sorted_df.tail(20)[['板块名称', '涨跌幅', '涨跌额']].to_string(index=False))

    if '振幅' in concept_df.columns:
        v_shape = concept_df[
            (concept_df['振幅'] > amplitude_threshold) &
            (concept_df['涨跌幅'] > gain_range[0]) &
            (concept_df['涨跌幅'] < gain_range[1])
        ].sort_values('振幅', ascending=False)

        print(f"\n【疑似 V 型反转板块】（共 {len(v_shape)} 个）")
        if len(v_shape) > 0:
            print(v_shape[['板块名称', '板块代码', '涨跌幅', '振幅']].head(20).to_string(index=False))
        else:
            print("今日未发现符合条件的 V 型反转板块。")
    else:
        print("\n数据中无振幅字段，使用涨跌幅范围筛选替代...")
        small_gain = concept_df[
            (concept_df['涨跌幅'] > gain_range[0]) &
            (concept_df['涨跌幅'] < gain_range[1])
        ]
        print(f"小幅上涨板块数量：{len(small_gain)}")
        print(small_gain.head(20).to_string(index=False))

    return concept_df


def check_intraday(concept_df, block_names):
    """
    检查指定板块的分时数据，判断是否有盘中大跌后拉回的走势
    
    参数:
        concept_df: 概念板块 DataFrame
        block_names: 要检查的板块名称列表
    """
    print(f"\n=== 分时数据验证 ===")

    for name in block_names:
        try:
            codes = concept_df[concept_df['板块名称'] == name]['板块代码'].values
            if len(codes) == 0:
                print(f"\n{name}：未找到板块代码")
                continue

            code = codes[0]
            intraday = ak.stock_board_concept_hist_em(symbol=code, period="分时")

            if '涨跌幅' in intraday.columns and len(intraday) > 0:
                min_chg = intraday['涨跌幅'].min()
                max_chg = intraday['涨跌幅'].max()
                cur_chg = intraday['涨跌幅'].iloc[-1]

                print(f"\n{name} ({code})：最低 {min_chg:.2f}% → 最高 {max_chg:.2f}% → 收盘 {cur_chg:.2f}%")
                if min_chg < -2 and cur_chg > 0:
                    print(f"  *** 确认 V 型反转！***")
            else:
                print(f"\n{name}：分时数据不完整")
        except Exception as e:
            print(f"\n{name}：获取分时数据失败 - {e}")


if __name__ == "__main__":
    df = scan_v_shape()

    test_blocks = ['油气开采', '航运概念', '煤炭概念', '贵金属', '储能']
    check_intraday(df, test_blocks)
