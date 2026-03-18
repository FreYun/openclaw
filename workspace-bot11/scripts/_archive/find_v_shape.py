import akshare as ak
import pandas as pd
from datetime import datetime

print("=== 查找今日 V 型反转板块 ===")
print(f"当前时间：{datetime.now()}")

# 获取所有概念板块
print("\n1. 获取概念板块行情...")
concept_df = ak.stock_board_concept_name_em()
print(f"概念板块数量：{len(concept_df)}")

# 筛选今天涨幅在 2%-5% 之间的板块（可能是 V 型反转）
# 同时查看那些振幅较大的板块
print("\n2. 分析板块涨跌幅分布...")

# 按涨跌幅排序
sorted_df = concept_df.sort_values('涨跌幅', ascending=False)
print("\n=== 涨幅前 20 板块 ===")
print(sorted_df.head(20)[['排名', '板块名称', '板块代码', '涨跌幅', '涨跌额', '振幅']])

print("\n=== 跌幅前 20 板块 ===")
print(sorted_df.tail(20)[['排名', '板块名称', '板块代码', '涨跌幅', '涨跌额', '振幅']])

# 找出振幅大但收盘上涨的板块（可能是 V 型反转）
print("\n3. 查找高振幅上涨板块（可能 V 型反转）...")
# 振幅 > 4% 且 涨幅在 0% 到 3% 之间
v_shape = concept_df[(concept_df['振幅'] > 4) & (concept_df['涨跌幅'] > 0) & (concept_df['涨跌幅'] < 3)]
v_shape = v_shape.sort_values('振幅', ascending=False)
print(f"符合条件的板块数量：{len(v_shape)}")
if len(v_shape) > 0:
    print(v_shape[['排名', '板块名称', '板块代码', '涨跌幅', '涨跌额', '振幅', '最高涨幅', '最低涨幅']].head(20))

# 获取一些具体板块的分时数据
print("\n4. 获取部分板块分时数据...")
test_blocks = ['油气开采', '航运概念', '煤炭概念', '贵金属', '储能']

for block in test_blocks:
    try:
        block_code = concept_df[concept_df['板块名称'] == block]['板块代码'].values
        if len(block_code) > 0:
            code = block_code[0]
            # 获取分时数据
            intraday_df = ak.stock_board_concept_hist_em(symbol=code, period="分时")
            print(f"\n{block} ({code}) 分时数据:")
            print(intraday_df.head(10))
            
            # 计算最低点和最高点
            if '涨跌幅' in intraday_df.columns:
                min_change = intraday_df['涨跌幅'].min()
                max_change = intraday_df['涨跌幅'].max()
                current_change = intraday_df['涨跌幅'].iloc[-1] if len(intraday_df) > 0 else 0
                print(f"  最低：{min_change:.2f}%, 最高：{max_change:.2f}%, 当前：{current_change:.2f}%")
                
                # 判断是否 V 型反转
                if min_change < -2 and current_change > 0:
                    print(f"  *** {block} 可能是 V 型反转！***")
    except Exception as e:
        print(f"获取 {block} 数据失败：{e}")
