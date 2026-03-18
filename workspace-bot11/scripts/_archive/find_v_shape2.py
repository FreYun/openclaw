import akshare as ak
import pandas as pd
from datetime import datetime

print("=== 查找今日 V 型反转板块 ===")
print(f"当前时间：{datetime.now()}")

# 获取所有概念板块
print("\n1. 获取概念板块行情...")
concept_df = ak.stock_board_concept_name_em()
print(f"概念板块数量：{len(concept_df)}")

# 打印列名
print("\n列名:", concept_df.columns.tolist())

# 打印前几行数据看看
print("\n前 5 行数据:")
print(concept_df.head())

# 按涨跌幅排序
print("\n2. 按涨跌幅排序...")
sorted_df = concept_df.sort_values('涨跌幅', ascending=False)

print("\n=== 涨幅前 20 板块 ===")
print(sorted_df.head(20))

print("\n=== 跌幅前 20 板块 ===")
print(sorted_df.tail(20))

# 找出振幅大但收盘上涨的板块（可能是 V 型反转）
print("\n3. 查找高振幅上涨板块（可能 V 型反转）...")
# 检查是否有振幅列
if '振幅' in concept_df.columns:
    # 振幅 > 4% 且 涨幅在 0% 到 3% 之间
    v_shape = concept_df[(concept_df['振幅'] > 4) & (concept_df['涨跌幅'] > 0) & (concept_df['涨跌幅'] < 3)]
    v_shape = v_shape.sort_values('振幅', ascending=False)
    print(f"符合条件的板块数量：{len(v_shape)}")
    if len(v_shape) > 0:
        print(v_shape.head(20))
else:
    print("没有振幅列，使用涨跌幅范围筛选...")
    # 找那些涨幅在 0-2% 但曾经大幅下跌的
    small_gain = concept_df[(concept_df['涨跌幅'] > 0) & (concept_df['涨跌幅'] < 2)]
    print(f"小幅上涨板块数量：{len(small_gain)}")
    print(small_gain.head(20))
