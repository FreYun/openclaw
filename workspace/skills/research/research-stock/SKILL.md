---
name: research-stock
description: 单股快速数据拉取。在行业研究中，对某只具体个股做快速数据查询：当前估值、近期走势、最新财务指标。这是支撑行业分析的辅助工具，不是独立研究报告。用法：/research-stock 600519.SH 或 /research-stock 茅台 估值
---

# 单股快速查询 /research-stock

**触发词**：`/research-stock`、"帮我查一下XX的PE"、"XX现在市值多少"、"XX最新财务怎么样"、"XX的ROE是多少"

**定位**：行业分析的数据辅助工具。用于在 sector-pulse / industry-earnings 过程中，对某只个股做针对性的数据补充查询。如果用户需要完整的个股深度研究，建议在 sector-pulse 框架下对比行业来做，而不是孤立分析单股。

---

## 执行流程

**确定 `TODAY`、股票代码（或名称 → `tushare_stock_basic` 确认 ts_code）、查询目的。**

根据用户具体需求，**按需选取**以下数据，不必全部拉取：

> 若用户同时提供了股票走势图表，使用 `/technical-analyst` 进行技术面分析，与基本面数据相互印证。

---

### 行情与估值（按需）

```
tushare_daily(ts_code, start_date=近60日)    → 价格走势、涨跌幅
tushare_daily_basic(ts_code, 最近交易日)      → PE/PB/PS/市值/换手率
tushare_index_daily(000300.SH, 同期)         → 沪深300对比（若需要相对表现）
```

---

### 财务指标（按需）

```
tushare_fina_indicator(ts_code, 最近2期)     → ROE/毛利率/净利率（快速健康度）
tushare_income(ts_code, 近2期)              → 营收/利润增速
tushare_cashflow(ts_code, 最近期)           → 经营现金流（利润质量验证）
```

---

### 资金面（按需）

```
tushare_hsgt_top10(近3-5交易日)             → 是否出现在北向十大
tushare_top10_holders(ts_code)              → 主要股东结构
```

---

### 联网查询（browser + browser，**必须执行**）

数值数据来自 Tushare，但分析师观点、近期事件、市场情绪必须通过 browser 和搜索获取。**两者同步进行。**

**browser 浏览**

**雪球个股主页是首选**：`https://xueqiu.com/S/SH{6位代码}` 或 `SZ{6位代码}`

东方财富个股研报可查分析师评级和目标价：`https://data.eastmoney.com/report/stock.jshtml?code={ts_code}`

根据查询目的自由访问其他相关页面。

**browser 搜索**：补充 browser 未覆盖的信息，如行业对比、近期公告解读等。

⚠️ 所有内容必须核查具体发布时间戳，"最新"、"近期"必须锚定到具体日期。

---

## 输出格式

**根据查询目的输出，轻量简洁，不铺开做完整报告。**

示例（估值快查）：
```
{股票名称}（{ts_code}）| {TODAY}
当前价：X元 | 市值：XX亿
PE(TTM)：XX倍 | PB：X.X倍 | PS：X.X倍
近1M：+X% | 近3M：+X%（沪深300同期：+X%）
换手率：X%（近5日均）
分析师：[评级] [目标价]（[研报日期] 🟢/🟡/🔴）
近期动态：[browser/搜索读到的重要信息，或"无重大事件"]
数据：Tushare Pro + browser + browser
```

示例（财务快查）：
```
{股票名称} 财务快照（{报告期}）
营收：XX亿（YoY +X%）| 净利润：XX亿（YoY +X%）
毛利率：X% | ROE：X% | 经营现金流/净利润：X.X
市场情绪：[雪球主流观点一句话]
数据：Tushare Pro + browser + browser
```

---

## 注意事项

- **够用就好**：用户只问PE就只给PE，不要主动铺开做全套分析
- **行业背景优先**：如果查询明显是为了行业对比（"XX的毛利率和YY比怎么样"），直接进入 sector-pulse 或 industry-earnings 流程
- **报告期确认**：财务数据按最近已披露期，A股财报一般延迟1-4个月
- **数据权限**：若 Tushare 返回空（积分不足），说明原因，不要猜测数据
