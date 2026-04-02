# 数据源与时效详解

> 黄金盯盘最常见的错误：**盘中拿收盘价当实时价格**。本文档明确每个数据源的时效性。

---

## 数据源时效分类

### 🟢 实时/近实时（盘中可用）

#### 1. 金十数据 (jin10.com)

**获取方式**：浏览器访问
```
browser navigate "https://www.jin10.com/" profile="你的account_id"
```
> ⚠️ profile 用你自己的 account_id（见 TOOLS.md），不要用别人的。

**能拿到的数据**：
- COMEX 黄金期货实时报价（页面顶部行情栏）
- 黄金相关快讯（7×24 快讯流）
- 经济数据日历（非农、CPI、美联储议息等发布时间）
- 美元指数 DXY 实时报价

**时效**：实时推送，秒级更新

**盘中用法**：
1. 打开金十首页 → 顶部看 COMEX 金价实时报价
2. 快讯栏搜索"黄金"/"gold" → 最新消息面
3. 数据日历 → 确认今天有无重要数据发布

**注意**：金十网页可能弹登录框，直接关掉即可，不影响查看行情和快讯。

**⚠️ 用完必须 `browser close`**——金十有实时推送，不关会持续吃 CPU。

---

#### 2. Web Search 实时报价

**获取方式**：联网搜索
```
web_search("黄金 实时价格")
web_search("gold spot price today")
web_search("COMEX gold price")
web_search("AU9999 实时价格")
```

**时效**：分钟级，搜索引擎聚合多个报价源

**适合场景**：快速确认当前金价区间，不需要打开浏览器

---

#### 3. Mysteel 贵金属（盘中报价）

**获取方式**：浏览器访问
```
browser navigate "https://www.mysteel.com/" profile="你的account_id"
```
然后搜索"黄金"或直接导航到贵金属频道。

**能拿到的数据**：
- AU9999 现货报价（盘中会更新）
- 上海金交所各合约报价
- 黄金现货升贴水
- 实物金条/金饰报价

**时效**：盘中更新，但不如金十频繁。更适合看现货价和升贴水。

**Mysteel 搜索技巧**：
```
web_search("mysteel 黄金 今日价格")
web_search("mysteel AU9999 现货")
web_search("mysteel 贵金属 周报")
```

---

### 🔴 收盘/延迟数据（盘中不能当实时价用）

#### 4. research-mcp `commodity_data`

**调用方式**：
```
commodity_data(symbol="AU9999", start_date="20260320", end_date="20260325")
commodity_data(symbol="黄金9999")
```

**返回内容**：每日收盘价、开盘价、最高价、最低价

**时效**：⚠️ **T+1 收盘后更新**。盘中调用返回的"最新"数据是前一个交易日的收盘价。

**正确用法**：收盘后复盘、历史走势分析、计算周涨跌幅

---

#### 5. 近 N 天走势（用 `commodity_data` 指定日期范围）

**调用方式**：
```
commodity_data(symbol="AU9999", start_date="30天前的日期", end_date="今天的日期")
```

**时效**：⚠️ 同上，**收盘后更新**，盘中数据滞后。

**正确用法**：收盘后看近 N 天走势趋势

> ⚠️ `commodity_quote` 工具已下线，不要调用。用 `commodity_data` + 日期范围替代。

---

#### 6. research-mcp `futures_data`

**调用方式**：
```
futures_data(symbol="AU.SHF", start_date="20260320", end_date="20260325")
```

**时效**：⚠️ 收盘数据，且据 research-mcp 文档标注"数据不完整"，**不推荐作为主数据源**。

---

## 盘中 vs 收盘 速查决策树

```
我要查金价
├── 现在是交易时段？
│   ├── 是 → 盘中模式
│   │   ├── 需要精确报价 → 金十数据（浏览器）
│   │   ├── 快速了解区间 → web_search("黄金 实时价格")
│   │   └── 看现货升贴水 → Mysteel（浏览器）
│   └── 否 → 收盘模式
│       ├── 今日收盘数据 → commodity_data(AU9999) ✅
│       ├── 近期走势 → commodity_data(AU9999, start_date=30天前, end_date=今天) ✅
│       └── 外盘收盘 → web_search("COMEX 黄金 收盘")
├── 我要分析走势趋势
│   └── commodity_data 拉 30-90 天数据 ✅
├── 我要看消息面
│   ├── 实时快讯 → 金十数据（浏览器）
│   └── 搜索新闻 → news_search("黄金") / web_search
└── 我要看观点研报
    ├── 知识星球 → 飞书问 bot11
    └── 券商研报 → research_search("黄金 贵金属")
```

---

## 关联指标数据源

| 指标 | 盘中获取 | 收盘获取 |
|------|---------|---------|
| 美元指数 DXY | 金十数据 / web_search("DXY 美元指数") | web_search |
| 美债 10Y 收益率 | 金十数据 / web_search | `get_cn_bond_yield` (中国国债) |
| 人民币汇率 | web_search("USDCNY 今日") | `get_cn_macro_data`(category="usdcny") |
| VIX 恐慌指数 | web_search("VIX index today") | web_search |
| COMEX 持仓 | — | web_search("CFTC COT 黄金") (每周五发布) |
| 全球央行购金 | — | web_search("世界黄金协会 央行购金") (月度/季度) |

---

## 交易时间参考

| 市场 | 交易时间（北京时间） | 说明 |
|------|-------------------|------|
| 上海金交所 AU9999 | 09:00-11:30, 13:30-15:30, 20:00-02:30 | 夜盘跨日 |
| 上期所黄金期货 | 09:00-10:15, 10:30-11:30, 13:30-15:00, 21:00-02:30 | 有中间休息 |
| COMEX 黄金期货 | 06:00-05:00 (次日) | 几乎 23h 连续，周末休市 |
| 伦敦金 (XAU/USD) | 类似 COMEX | OTC 市场 |

> 节假日休市安排不同，遇到跨市场长假要留意外盘走势。
