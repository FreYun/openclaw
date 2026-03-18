import akshare as ak
import pandas as pd
from datetime import datetime

print("=== 获取 A 股板块今日行情 ===")
print(f"当前时间：{datetime.now()}")

# 获取申万一级行业指数实时行情
try:
    print("\n1. 获取申万一级行业指数...")
    sw_index_df = ak.index_stock_cons_csindex(symbol="801010")  # 申万一级
    print(f"申万一级指数数量：{len(sw_index_df)}")
    print(sw_index_df.head())
except Exception as e:
    print(f"获取申万指数失败：{e}")

# 获取同花顺行业板块
try:
    print("\n2. 获取同花顺行业板块行情...")
    ths_df = ak.stock_board_industry_name_em()
    print(f"同花顺行业板块数量：{len(ths_df)}")
    print(ths_df.head(20))
except Exception as e:
    print(f"获取同花顺数据失败：{e}")

# 获取概念板块
try:
    print("\n3. 获取概念板块行情...")
    concept_df = ak.stock_board_concept_name_em()
    print(f"概念板块数量：{len(concept_df)}")
    print(concept_df.head(20))
except Exception as e:
    print(f"获取概念板块失败：{e}")

# 获取行业板块分时数据（需要具体板块代码）
try:
    print("\n4. 获取行业板块涨跌幅排行...")
    # 东方财富行业板块实时行情
    industry_rank = ak.stock_board_industry_rank_em()
    print(f"行业板块排行数量：{len(industry_rank)}")
    print(industry_rank.head(30))
except Exception as e:
    print(f"获取行业排行失败：{e}")
