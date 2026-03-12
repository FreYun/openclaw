# AKShare API 快速参考

## 股票数据

### 基本信息
```python
ak.stock_individual_info_em(symbol='600519')  # 个股基本信息
```
输出字段：最新价、股票代码、股票简称、总股本、流通股本、总市值、流通市值、行业、上市时间

### 实时行情
```python
ak.stock_zh_a_spot_em()  # 全部A股实时行情（可能超时）
```

### 历史行情
```python
ak.stock_zh_a_hist(symbol='600519', period='daily', start_date='20250101', end_date='20250227', adjust='qfq')
```
- period: daily/weekly/monthly
- adjust: qfq(前复权)/hfq(后复权)/''(不复权)

输出字段：日期、股票代码、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率

### 分时数据
```python
ak.stock_zh_a_minute(symbol='600519', period='1')  # 1分钟线
ak.stock_zh_a_minute(symbol='600519', period='5')  # 5分钟线
```

## 指数数据

```python
ak.index_zh_a_hist(symbol='000001', period='daily', start_date='20250201', end_date='20250227')
```
常用指数代码：
- 000001: 上证指数
- 399001: 深证成指
- 399006: 创业板指
- 000300: 沪深300
- 000016: 上证50
- 000905: 中证500

## 基金数据

### 基金列表
```python
ak.fund_name_em()  # 公募基金列表
```

### 基金净值
```python
ak.fund_open_fund_info_em(fund='000001', indicator='单位净值走势')
```
indicator选项：
- 单位净值走势
- 累计净值走势
- 累计收益率走势

## 新闻资讯

```python
ak.stock_info_global_em()  # 全球财经快讯
ak.stock_telegraph_em()    # 财联社电报
```

## 宏观经济

```python
ak.macro_china_gdp()       # GDP数据
ak.macro_china_cpi()       # CPI数据
ak.macro_china_pmi()       # PMI数据
ak.macro_china_lpr()       # LPR利率
```

## 板块数据

### 行业板块
```python
ak.stock_board_industry_name_ths()        # 同花顺行业列表
ak.stock_board_industry_index_ths(symbol='半导体')  # 行业指数
```

### 概念板块
```python
ak.stock_board_concept_name_ths()         # 同花顺概念列表
ak.stock_board_concept_index_ths(symbol='华为概念')  # 概念指数
```

## 资金流向

```python
ak.stock_fund_flow_individual(symbol='600519')  # 个股资金流
ak.stock_fund_flow_concept()                     # 概念板块资金流
ak.stock_fund_flow_industry()                    # 行业板块资金流
```

## 龙虎榜

```python
ak.stock_lhb_detail_daily(start_date='20250227', end_date='20250227')  # 每日龙虎榜
ak.stock_lhb_stock_detail(symbol='600519', date='20250227')            # 个股龙虎榜
```
