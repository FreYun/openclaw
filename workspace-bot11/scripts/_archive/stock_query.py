import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

# 相关标的代码 (从雪球讨论中提取)
stocks = {
    '银行': ['600036', '601166', '601939', '601288', '600919'],
    '存储芯片': ['688525', '301308', '688008'],
    'PCB': ['300476', '002384', '002916', '000636'],
    '半导体': ['688256', '688981', '688041'],
    '油气': ['601857', '600028', '600938'],
    '航运': ['600026', '601872', '601919']
}

# 股票名称映射
stock_names = {
    '600036': '招商银行', '601166': '兴业银行', '601939': '建设银行',
    '601288': '农业银行', '600919': '江苏银行',
    '688525': '佰维存储', '301308': '江波龙', '688008': '澜起科技',
    '300476': '胜宏科技', '002384': '东山精密', '002916': '深南电路',
    '000636': '风华高科', '688256': '寒武纪', '688981': '中芯国际',
    '688041': '海光信息', '601857': '中国石油', '600028': '中国石化',
    '600938': '中国海油', '600026': '中远海能', '601872': '招商轮船',
    '601919': '中远海控'
}

print('数据获取时间:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
print('='*80)

all_data = []

for sector, codes in stocks.items():
    print(f'\n【{sector}】')
    print('-'*60)
    
    for code in codes:
        try:
            # 获取 A 股日线数据
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if len(df) > 0:
                df = df.tail(5)  # 获取最近 5 天数据
                latest = df.iloc[-1]
                
                # 今日涨跌幅
                today_change = latest['涨跌幅']
                
                # 计算 3 天涨跌幅
                if len(df) >= 4:
                    three_day_change = ((latest['收盘'] / df.iloc[-4]['收盘']) - 1) * 100
                else:
                    three_day_change = today_change
                
                close_price = latest['收盘']
                name = stock_names.get(code, code)
                
                print(f"{name}({code}): 今日 {today_change:+.2f}% | 3 天 {three_day_change:+.2f}% | 收盘 {close_price:.2f}")
                
                all_data.append({
                    '板块': sector,
                    '代码': code,
                    '名称': name,
                    '今日%': today_change,
                    '3 天%': three_day_change,
                    '收盘价': close_price
                })
        except Exception as e:
            print(f'{code}: 获取失败 - {str(e)[:40]}')

# 创建汇总表格
print('\n' + '='*80)
print('数据汇总表')
print('='*80)

df_all = pd.DataFrame(all_data)
for sector in df_all['板块'].unique():
    sector_df = df_all[df_all['板块'] == sector]
    print(f'\n【{sector}】')
    for _, row in sector_df.iterrows():
        today_flag = '[+]' if row['今日%'] > 0 else ('[-]' if row['今日%'] < 0 else '[=]')
        three_flag = '[+]' if row['3 天%'] > 0 else ('[-]' if row['3 天%'] < 0 else '[=]')
        print(f"  {row['名称']}: 今日{today_flag}{row['今日%']:+.2f}% | 3 天{three_flag}{row['3 天%']:+.2f}% | {row['收盘价']:.2f}元")
