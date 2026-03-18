# 投研工具速查

> 按需查阅。场景流程中需要具体调用时翻阅。

---

## MCP 连接

| 服务 | 用途 | 地址 |
|------|------|------|
| xiaohongshu-mcp | 小红书发布/互动 | localhost:18067 |
| compliance-mcp | 合规审核 | localhost:18090 |
| skill-gateway | 聚合金融数据 | localhost:18080/mcp/bot7/mcp |

调用格式：`npx mcporter call "服务名.工具名(参数)"`

---

## Tushare 行情数据

直接通过 mcporter 调用，日期格式 `YYYYMMDD`，股票代码带后缀 `.SH`/`.SZ`。

### 行情

| 工具 | 用途 | 示例 |
|------|------|------|
| `tushare_daily` | 日K线(OHLCV) | `tushare_daily(ts_code: '600519.SH', start_date: '20260310', end_date: '20260317')` |
| `tushare_daily_basic` | PE/PB/PS/市值/换手 | `tushare_daily_basic(ts_code: '600519.SH', trade_date: '20260317')` |
| `tushare_index_daily` | 指数日线 | `tushare_index_daily(ts_code: '000300.SH', start_date: '20260310', end_date: '20260317')` |

### 财务

| 工具 | 用途 | 示例 |
|------|------|------|
| `tushare_income` | 利润表 | `tushare_income(ts_code: '688256.SH', period: '20251231')` |
| `tushare_balancesheet` | 资产负债表 | `tushare_balancesheet(ts_code: '688256.SH', period: '20251231')` |
| `tushare_cashflow` | 现金流量表 | `tushare_cashflow(ts_code: '688256.SH', period: '20251231')` |
| `tushare_fina_indicator` | ROE/毛利率/EPS | `tushare_fina_indicator(ts_code: '688256.SH', period: '20251231')` |

### 资金流

| 工具 | 用途 | 示例 |
|------|------|------|
| `tushare_moneyflow_hsgt` | 北向资金日汇总 | `tushare_moneyflow_hsgt(start_date: '20260301', end_date: '20260317')` |
| `tushare_hsgt_top10` | 沪深港通十大成交股 | `tushare_hsgt_top10(trade_date: '20260317')` |
| `tushare_top10_holders` | 前十大股东 | `tushare_top10_holders(ts_code: '688256.SH')` |

### 其他

| 工具 | 用途 |
|------|------|
| `tushare_stock_basic()` | 全A股列表+基本信息 |
| `tushare_forecast` | 业绩预告 |
| `tushare_trade_cal` | 交易日历 |

---

## Skill-Gateway 聚合工具

通过 skill-gateway MCP 调用，封装了更高层的金融查询。

| 工具 | 用途 | 适用场景 |
|------|------|---------|
| `market_snapshot` | A股/港股/美股大盘快照 | 日常复盘第一步 |
| `stock_research` | 个股综合研究(基本面/K线/估值/资金) | 个股扫描 |
| `index_valuation` | 指数估值(PE/PB分位) | 判断大盘位置 |
| `search_news` | 财经新闻搜索 | 新闻归因 |
| `search_report` | 研报搜索 | 行业深研 |
| `macro_overview` | 宏观经济数据(GDP/CPI/PMI) | 宏观环境分析 |
| `commodity_quote` | 大宗商品行情 | 有色/能源相关研究 |
| `fund_analysis` | 基金综合分析 | 跟踪机构动向 |

---

## Browser 浏览

用 browser 工具直接访问，profile 用 `bot7`。

| 网站 | URL | 用途 |
|------|-----|------|
| 雪球搜索 | `https://xueqiu.com/search?q={关键词}` | 投资者讨论/情绪 |
| 雪球个股 | `https://xueqiu.com/S/SH{代码}` 或 `SZ{代码}` | 个股讨论 |
| 东财行业报告 | `https://data.eastmoney.com/report/industry.jshtml` | 券商研报 |
| 东财个股报告 | `https://data.eastmoney.com/report/stock.jshtml?code={ts_code}` | 个股研报 |
| 同花顺新闻 | `https://news.10jqka.com.cn/` | 新闻聚合 |
| 巨潮资讯 | `http://www.cninfo.com.cn/` | 公司公告原文 |

---

## 常用代码速查

### A股指数
| 名称 | 代码 |
|------|------|
| 沪深300 | `000300.SH` |
| 中证500 | `000905.SH` |
| 创业板指 | `399006.SZ` |
| 科创50 | `688000.SH` |
| 上证指数 | `000001.SH` |

### 美股/港股指数
| 名称 | 代码 |
|------|------|
| 标普500 | `SPX.GI` |
| 纳斯达克 | `NDX.GI` |
| 道琼斯 | `DJIA.GI` |
| 恒生指数 | `HSI.HI` |
| 恒生科技 | `HSTECH.HI` |

### 日期格式
- 日数据：`YYYYMMDD`（如 `20260317`）
- 月数据：`YYYYMM`（如 `202603`）
- 季度：`YYYYQN`（如 `2026Q1`）
- 财报期：用季末日期 `20251231`、`20260331`
