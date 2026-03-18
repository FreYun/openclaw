---
name: research-mcp
description: 金融研究数据 MCP — 基金、股票、指数、债券、宏观、商品、新闻研报。按需 Read 子模块获取工具详情。
---

# Research MCP（金融研究数据）

MCP 地址：`http://research-mcp.jijinmima.cn/mcp`
协议：Streamable HTTP（需要 `Accept: text/event-stream, application/json`）

## 格式铁律

- **日期**：`YYYYMMDD`（如 `20260317`），不是 `YYYY-MM-DD`
- **A股指数**：带后缀 `000300.SH`, `399006.SZ`
- **港股指数**：`HSI.HI`, `HSTECH.HI`, `HSCEI.HI`
- **美股指数**：`DJIA.GI`, `SPX.GI`, `NDX.GI`
- **股票/基金代码**：6 位纯数字 `600519`, `000001`
- **中国宏观 category**：小写 `gdp,cpi,ppi,m2`
- **债券期限**：国债大写 `10Y`，信用债小写 `3y`

## 意图路由（按需求找模块，Read 对应文件获取工具详情）

| 我想… | 推荐工具 | 详见 |
|--------|---------|------|
| **看 A 股/港股/美股大盘** | `market_overview` / `get_hshares_market_overview` | `market.md` |
| **查指数行情、估值、成交额** | `get_ashares_index_quote` / `get_ashares_index_val` | `market.md` |
| **查恐慌指数、南向资金** | `get_ashares_gvix` / `get_southbound_hkd_turnover` | `market.md` |
| **全面分析一只基金** | `get_fund_comprehensive_analysis` — 一站式 | `fund.md` |
| **批量查基金净值收益率** | `fund_basicinfo` | `fund.md` |
| **比较多只基金走势** | `get_multiple_funds_nav` | `fund.md` |
| **按条件筛基金** | `simple_fund_search` / `fund_theme_screening` | `fund.md` |
| **找重仓某股票的基金** | `fund_stock_holdings` | `fund.md` |
| **查个股基本面/K线/估值** | `get_stock_info` / `get_stock_daily_quote` / `get_stock_valuation` | `stock.md` |
| **查个股资金流向/北向持股** | `get_stock_fund_flow` / `get_stock_northbound_holding` | `stock.md` |
| **查国债/信用债收益率** | `get_cn_bond_yield` / `get_credit_bond_yield` | `bond.md` |
| **查中美利差/信用利差** | `get_bond_yield_spread` | `bond.md` |
| **查中国 GDP/CPI/M2 等** | `get_cn_macro_data` | `macro.md` |
| **查美国宏观数据** | `us_macro_simple` | `macro.md` |
| **查黄金等商品行情** | `commodity_data` | `macro.md` |
| **搜新闻** | `news_search` | `news.md` |
| **搜研报** | `research_search` | `news.md` |
| **从文本提取股票/基金名** | `query_segment` | `news.md` |

## 常用工作流

### 市场日报
`market_overview` → `get_hshares_market_overview` → `get_usstock_index_quote`(DJIA.GI,SPX.GI,NDX.GI) → `get_ashares_gvix` → `news_search`("市场 热点")

### 基金分析
`get_fund_comprehensive_analysis`(fund_code) → 如需净值走势加 `get_fund_nav_and_return` → 如需异动加 `get_fund_abnormal_movement`

### 个股研究
`get_stock_info` → `get_stock_daily_quote` → `get_stock_valuation` → `get_stock_fund_flow` → `get_stock_northbound_holding` → `fund_stock_holdings`(找重仓基金)

### 宏观环境
`get_cn_macro_data`(cpi,ppi,m2,pmi) → `us_macro_simple` → `get_cn_bond_yield`(10Y) → `get_bond_yield_spread`(cn_vs_us) → `commodity_data`(AU9999)
