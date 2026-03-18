import tushare as ts
import pandas as pd
import sys

# 设置 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')

# 设置 Token
ts.set_token('ed396239156fa590b3730414be7984b029e021c3531e419f6bc170d4')

# 初始化 API
pro = ts.pro_api()

print("=" * 60)
print("Tushare API 测试 - 上证指数数据")
print("=" * 60)

# 1. 获取上证指数最新日线行情（使用 index_daily 接口）
print("\n1. 获取上证指数 (000001.SH) 最新行情...")
try:
    # 使用指数专用接口
    df_daily = pro.index_daily(ts_code='000001.SH', start_date='20260101', end_date='20260310')
    
    if not df_daily.empty:
        # 按日期排序，取最新
        df_daily = df_daily.sort_values('trade_date', ascending=False)
        latest = df_daily.iloc[0]
        print(f"\n[OK] 获取成功！")
        print(f"\n上证指数最新数据:")
        print(f"   交易日期：{latest['trade_date']}")
        print(f"   收盘价：{latest['close']} 点")
        print(f"   开盘价：{latest['open']} 点")
        print(f"   最高价：{latest['high']} 点")
        print(f"   最低价：{latest['low']} 点")
        print(f"   昨收价：{latest['pre_close']} 点")
        print(f"   涨跌额：{latest['change']} 点")
        print(f"   涨跌幅：{latest['pct_chg']}%")
        print(f"   成交量：{latest['vol']/10000:.2f} 万手")
        print(f"   成交额：{latest['amount']/100000000:.2f} 亿元")
    else:
        print("[Error] 未获取到日线数据")
except Exception as e:
    print(f"[Error] 获取指数数据失败：{e}")
    import traceback
    traceback.print_exc()

# 2. 获取市场涨跌家数（尝试不同接口）
print("\n" + "=" * 60)
print("2. 获取市场涨跌家数...")

# 方法 1: 通过获取全部 A 股当日行情统计
print("\n方法 1: 通过全部 A 股行情统计涨跌家数...")
try:
    # 获取最新交易日全部 A 股行情
    df_all = pro.daily(start_date='20260227', end_date='20260227')
    
    if not df_all.empty:
        # 统计涨跌
        up_count = len(df_all[df_all['pct_chg'] > 0])
        down_count = len(df_all[df_all['pct_chg'] < 0])
        flat_count = len(df_all[df_all['pct_chg'] == 0])
        
        print(f"\n[OK] 统计成功！")
        print(f"\n市场涨跌统计 (2026-02-27):")
        print(f"   上涨家数：{up_count} 家")
        print(f"   下跌家数：{down_count} 家")
        print(f"   持平家数：{flat_count} 家")
        
        if down_count > 0:
            ratio = up_count / down_count
            print(f"   涨跌比：{ratio:.2f} (涨/跌)")
        
        # 涨停跌停统计
        limit_up = len(df_all[df_all['pct_chg'] >= 9.8])
        limit_down = len(df_all[df_all['pct_chg'] <= -9.8])
        print(f"\n   涨停家数：{limit_up} 家")
        print(f"   跌停家数：{limit_down} 家")
    else:
        print("[Error] 未获取到全部 A 股数据")
except Exception as e:
    print(f"[Error] 统计失败：{e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
