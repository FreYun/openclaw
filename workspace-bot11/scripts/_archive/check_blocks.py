import tushare as ts
import pandas as pd
from datetime import datetime

# 尝试使用 tushare pro
try:
    # 读取 token (如果有的话)
    with open('tushare_token.txt', 'r') as f:
        token = f.read().strip()
    ts.set_token(token)
    pro = ts.pro_api()
    print("Tushare Pro 已配置")
except FileNotFoundError:
    print("未找到 tushare token，尝试使用免费版")
    pro = None

# 获取申万一级行业指数列表
if pro:
    try:
        # 获取指数基本信息
        indices = pro.index_basic(market='SW')
        print(f"\n申万指数数量：{len(indices)}")
        print(indices.head(10))
    except Exception as e:
        print(f"获取指数列表失败：{e}")
else:
    print("使用免费版 tushare")
    # 免费版获取行业板块数据
    try:
        df = ts.get_industry_classified()
        print(f"\n行业板块数量：{len(df)}")
        print(df.head(10))
    except Exception as e:
        print(f"获取行业数据失败：{e}")

# 获取今日行情
print("\n=== 今日板块行情 ===")
try:
    # 获取同花顺行业板块实时行情
    ths_df = ts.get_ths_index()
    print(f"同花顺行业板块数量：{len(ths_df)}")
    print(ths_df.head(20))
except Exception as e:
    print(f"获取同花顺数据失败：{e}")
