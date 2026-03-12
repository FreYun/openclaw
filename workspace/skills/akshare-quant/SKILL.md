---
name: akshare-quant
description: Access Chinese financial market data using AKShare library. Use when the user needs stock prices, fund data, index data, financial news, or any quantitative finance data from Chinese markets (A-shares, Hong Kong stocks, funds, indices). Provides real-time quotes, historical data, and fundamental information.
---

# AKShare Quantitative Data

## Overview

AKShare is a Python library for accessing Chinese financial market data including:
- **A-share stocks**: Real-time quotes, historical prices, fundamentals
- **Funds**: Public funds, private funds, NAV data
- **Indices**: Market indices, sector indices
- **News**: Financial news, announcements
- **Macro**: Economic indicators

## Installation

```bash
pip install akshare
```

## Core Workflows

### 1. Get Stock Information

**Basic info for a single stock:**
```python
import akshare as ak

# Stock basic info (name, total shares, industry, etc.)
df = ak.stock_individual_info_em(symbol='600519')
print(df)
```

**Stock list (all A-shares):**
```python
# Get all A-share stocks with current prices
df = ak.stock_zh_a_spot_em()
# Returns: code, name, price, change%, volume, etc.
```

### 2. Get Historical Prices

**Daily historical data:**
```python
# Parameters:
# - symbol: Stock code (e.g., '600519' for 贵州茅台)
# - period: 'daily', 'weekly', 'monthly'
# - start_date/end_date: Format 'YYYYMMDD'
# - adjust: 'qfq' (前复权), 'hfq' (后复权), '' (不复权)

df = ak.stock_zh_a_hist(
    symbol='600519',
    period='daily',
    start_date='20250101',
    end_date='20250227',
    adjust='qfq'
)
# Columns: 日期, 股票代码, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
```

**Recent N days (lightweight):**
```python
# For recent data only, use shorter date range to avoid timeout
df = ak.stock_zh_a_hist(symbol='000001', start_date='20250220', end_date='20250227')
```

### 3. Get Index Data

**Market indices:**
```python
# 上证指数: '000001'
# 深证成指: '399001'
# 创业板指: '399006'
# 沪深300: '000300'

df = ak.index_zh_a_hist(symbol='000001', period='daily', start_date='20250201', end_date='20250227')
```

### 4. Get Fund Data

**Fund list:**
```python
df = ak.fund_name_em()  # All public funds
```

**Fund NAV (historical):**
```python
# Get fund NAV history
df = ak.fund_open_fund_info_em(fund='000001', indicator='单位净值走势')
```

### 5. Get Financial News

**Latest news:**
```python
df = ak.stock_info_global_em()
# Columns: 标题, 摘要, 发布时间, 链接
```

## Important Notes

### Rate Limiting & Timeouts

- **Large queries timeout**: Getting all 5000+ A-shares at once often fails
- **Solution**: Use specific symbols or short date ranges
- **Recommended**: Query single stock or small batch (< 50 stocks)

### Data Reliability

| Interface | Stability | Notes |
|-----------|-----------|-------|
| `stock_individual_info_em` | ⭐⭐⭐⭐⭐ | Very stable, single stock |
| `stock_zh_a_hist` | ⭐⭐⭐⭐⭐ | Stable with date range |
| `stock_zh_a_spot_em` | ⭐⭐⭐ | May timeout for all stocks |
| `index_zh_a_hist` | ⭐⭐⭐⭐⭐ | Stable |
| `stock_info_global_em` | ⭐⭐⭐⭐⭐ | News feed, stable |

### Common Stock Codes

| Code | Name | Exchange |
|------|------|----------|
| 600519 | 贵州茅台 | Shanghai |
| 000001 | 平安银行 | Shenzhen |
| 000001 | 上证指数 | Index |
| 399001 | 深证成指 | Index |
| 399006 | 创业板指 | Index |

## Usage Patterns

### Pattern 1: Quick Price Check
```python
import akshare as ak

df = ak.stock_individual_info_em(symbol='600519')
current_price = df[df['item'] == '最新价']['value'].values[0]
print(f"茅台当前价格: {current_price}")
```

### Pattern 2: Recent Trend Analysis
```python
import akshare as ak

# Get last 10 trading days
df = ak.stock_zh_a_hist(symbol='600519', start_date='20250210', end_date='20250227', adjust='qfq')
avg_change = df['涨跌幅'].mean()
print(f"近10日平均涨跌幅: {avg_change:.2f}%")
```

### Pattern 3: Compare Multiple Stocks
```python
import akshare as ak

stocks = ['600519', '000001', '000333']  # 茅台, 平安银行, 美的集团
for code in stocks:
    df = ak.stock_individual_info_em(symbol=code)
    name = df[df['item'] == '股票简称']['value'].values[0]
    price = df[df['item'] == '最新价']['value'].values[0]
    print(f"{name}({code}): {price}")
```

## Error Handling

Common errors and solutions:

```python
import akshare as ak

try:
    df = ak.stock_zh_a_hist(symbol='600519', start_date='20250101', end_date='20250227')
except Exception as e:
    if "timeout" in str(e).lower():
        print("请求超时，尝试缩短时间范围")
        df = ak.stock_zh_a_hist(symbol='600519', start_date='20250220', end_date='20250227')
    else:
        raise
```

## Scripts

The `scripts/` directory contains helper scripts for common tasks:

- `get_stock_price.py` - Get current price for a stock
- `get_hist_data.py` - Get historical data with error handling
- `batch_query.py` - Query multiple stocks efficiently

See individual script documentation for usage details.
