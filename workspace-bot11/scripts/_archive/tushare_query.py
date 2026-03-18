import tushare as ts
import pandas as pd
from datetime import datetime, timedelta

# 初始化 tushare
ts.set_token('8b19d5a19e0f8d6e5c2a3f4b7d9e1c6a2b5d8f3e')
pro = ts.pro_api()

# 相关标的代码 (从雪球讨论中提取)
stocks = {
    '银行': ['600036.SH', '601166.SH', '601939.SH', '601288.SH', '600919.SH'],
    '存储芯片': ['688525.SH', '301308.SZ', '688008.SH'],
    'PCB': ['300476.SZ', '002384.SZ', '002916.SZ', '000636.SZ'],
    '半导体': ['688256.SH', '688981.SH', '688041.SH'],
    '油气': ['601857.SH', '600028.SH', '600938.SH'],
    '航运': ['600026.SH', '601872.SH', '601919.SH']
}

# 获取日期范围
today = datetime.now().strftime('%Y%m%d')
three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y%m%d')

print('数据获取时间:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
print('='*80)

for sector, codes in stocks.items():
    print(f'\n【{sector}】')
    print('-'*60)
    
    for code in codes:
        try:
            # 获取日线数据
            df = pro.daily(ts_code=code, start_date=three_days_ago, end_date=today)
            if len(df) > 0:
                df = df.sort_values('trade_date').reset_index(drop=True)
                latest = df.iloc[-1]
                
                # 计算 3 天涨跌幅
                if len(df) >= 2:
                    three_day_change = ((latest['close'] / df.iloc[0]['close']) - 1) * 100
                else:
                    three_day_change = latest['pct_chg']
                
                print(f"{code}: 今日 {latest['pct_chg']:.2f}% | 3 天 {three_day_change:.2f}% | 收盘价 {latest['close']:.2f}")
        except Exception as e:
            print(f'{code}: 获取失败 - {str(e)[:50]}')
