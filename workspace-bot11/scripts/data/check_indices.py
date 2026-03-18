import tushare as ts
import akshare as ak

ts.set_token('ed396239156fa590b3730414be7984b029e021c3531e419f6bc170d4')
pro = ts.pro_api()

# 先查昨日 (03-05) 数据作为参考
yesterday = '20260305'

indices = [
    ('000042.SH', '中证金融地产', '金融地产 ETF'),
    ('399975.SZ', '中证证券', '券商 ETF'),
    ('000688.SH', '科创 50', '科创板 ETF'),
    ('399965.SZ', '中证 800 金融', '保险参考'),
]

print('=== 指数昨日表现 (2026-03-05) ===\n')

for ts_code, name, fund in indices:
    try:
        df = pro.index_daily(ts_code=ts_code, start_date=yesterday, end_date=yesterday)
        if len(df) > 0:
            row = df.iloc[0]
            pct_chg = row['pct_chg']
            close = row['close']
            print(f'{fund} → {name}')
            print(f'  收盘：{close:.2f}  涨跌幅：{pct_chg:+.2f}%')
            print()
    except Exception as e:
        print(f'{fund} → {name} - 查询失败')
        print()

# 用 akshare 查实时板块行情
print('\n=== 今日板块实时行情 (东方财富) ===\n')
try:
    board = ak.stock_board_industry_name_em()
    keywords = ['证券', '保险', '银行', '房地产', '半导体']
    for kw in keywords:
        matches = board[board['板块名称'].str.contains(kw, na=False)]
        if len(matches) > 0:
            print(f'【{kw}】')
            for _, row in matches.head(3).iterrows():
                print(f'  {row["板块名称"]}: {row["涨跌幅"]}%')
            print()
except Exception as e:
    print(f'akshare 查询失败：{e}')
