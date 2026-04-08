# 深度分析

**篇幅**：3000-5000字
**适用**：行业/策略/方法论的深度长文

---

## 素材采集

按话题类型选用 research-mcp 工具组合：

| 话题类型 | research-mcp 工具组合 | 说明 |
|---------|----------------------|------|
| 行业研究 | `research_search(query='行业名')` → `get_stock_info` + `get_stock_valuation`（行业龙头对比）→ `get_stock_fund_flow`（资金流向）→ `news_search(query='行业名 产业')` | 竞争格局、供需、估值对比、资金流向 |
| 个股分析 | `get_stock_info` → `get_stock_daily_quote` → `get_stock_valuation` → `get_stock_market_value` → `get_stock_fund_flow` → `get_stock_northbound_holding` → `get_stock_shareholder` | 基本面、估值、资金、股东全景 |
| 宏观环境 | `market_overview` → `get_hshares_market_overview` → `get_usstock_index_quote` → `get_cn_macro_data(category='cpi,ppi,pmi,m2')` → `us_macro_simple` → `get_cn_bond_yield(maturity='10Y')` → `get_bond_yield_spread(spread_type='cn_vs_us')` → `commodity_data(symbol='AU9999')` | 全球市场、汇率、利率、商品全景 |
| 财报季对比 | 多只个股分别调 `get_stock_info` + `get_stock_valuation` + `get_stock_market_value` → 横向对比 PE/PB/市值 → `research_search(query='行业 财报')` 查研报解读 | 多公司横向对比 |
| 新闻/观点验证 | `news_search(query='待验证话题')` + `research_search(query='待验证话题')` → 交叉比对数据和观点 | 核查数据真实性、逻辑一致性 |
| 基金持仓分析 | `get_fund_comprehensive_analysis(fund_code)` → `fund_stock_holdings(stock_code)` 反查重仓基金 | 机构行为、筹码结构 |

**常用数据查询示例：**

```bash
# 个股日K线
npx mcporter call "research-mcp.get_stock_daily_quote(stock_code='000001', start_date='20260101', end_date='20260320')"

# 个股估值因子
npx mcporter call "research-mcp.get_stock_valuation(stock_code='600519')"

# 搜研报（深度分析的重要输入）
npx mcporter call "research-mcp.research_search(query='半导体 行业 景气', top_k=5, search_day_ago=30)"

# 中国宏观数据
npx mcporter call "research-mcp.get_cn_macro_data(category='cpi,ppi,pmi,m2')"

# 中美利差
npx mcporter call "research-mcp.get_bond_yield_spread(spread_type='cn_vs_us', maturity='10Y')"

# 商品行情（黄金等）
npx mcporter call "research-mcp.commodity_data(symbol='AU9999', start_date='20260101')"
```

---

## 写作风格选择

**5 种风格，详见 `skills/writing-styles/`：**

| 风格 | 文件 | 核心手法 | 适用场景 |
|------|------|---------|---------|
| **传导链** | `skills/writing-styles/style-chain.md` | A→B→C→D 多米诺推演 | 产业链价格传导、宏观→行业 |
| **先破后立** | `skills/writing-styles/style-debunk.md` | 数据推翻共识→给出真相 | 市场存在普遍误解 |
| **双轨叙事** | `skills/writing-styles/style-dual-track.md` | 旧世界坍塌+新世界崛起 | 技术迭代/新旧动能切换 |
| **庖丁解牛** | `skills/writing-styles/style-anatomy.md` | 一家公司切入全行业 | 龙头公司分析、产品拆解 |
| **灵魂三问** | `skills/writing-styles/style-three-questions.md` | 围绕3个核心问题展开 | 投资决策型文章 |

**风格决策树：**
```
行业正在经历什么？
├── 价格传导明显 → 传导链
├── 市场有误解 → 先破后立
├── 新旧交替 → 双轨叙事
├── 龙头有故事 → 庖丁解牛
├── 读者问"能不能买" → 灵魂三问
└── 不确定 → 默认传导链
```

> 确定风格后，`Read skills/writing-styles/对应风格文件.md` 加载完整结构模板和 Before/After 示范。

---

## 写作框架（通用骨架）

```
结构：
├── 标题（6字以内，反直觉/疑问句/对立概念）
├── 核心观点引语（blockquote，1-2 句话）
├── 引子段：类比/故事/反常识切入
│   └── 用生活化类比降低阅读门槛，引出核心问题
├── 分析段（多维度展开，占全文主体）
│   ├── 每段有小标题，逻辑递进
│   ├── 数据支撑（具体数字、机构观点）
│   └── 关键句式："这意味着什么？""用大白话说就是..."
├── 结论段：回到操作层面
│   ├── 总结核心观点（3 句话以内）
│   └── 给出可操作的建议或关注方向
└── 风险提示 + 免责声明
```

> 具体结构由所选风格决定，上面只是通用骨架。选定风格后以风格文件中的模板为准。

**标题规律（6字以内）：**
- 疑问句："做空反涨？"
- 反直觉："红利是假的"
- 判断型："油价要涨了"
- 悬念型："谁在撒谎？"

**关键原则：**
1. 逻辑链条至少 3 层递进 — 现象 → 原因 → 推演 → 操作含义
2. 每个观点有数据支撑 — 不空谈，用数字说话
3. 有独立观点 — 如果只是总结别人说的，不如不写
4. 系列化 — 深度文章适合做系列，形成知识网络
