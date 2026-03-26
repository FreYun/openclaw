---
name: mp-content-writer
description: >
  公众号投资类文章创作 skill。基于对标博主的写作框架，支持日复盘、深度分析、周复盘、轻松深度四种文章类型。
  集成 bot11 本地数据脚本和研究类 skill，从数据采集到成稿一站式完成。
  用户说"写篇公众号""写个复盘""写篇深度"时触发。
---

# 公众号投资文章创作 Skill

基于 6 位对标博主（思想钢印、梁狗蛋、民工看市、刘备教授、饭爷的江湖、微积分量化价投）的写作方法论，提炼出的公众号投资内容创作框架。

**适用内容方向：投资复盘 + 深度分析**

---

## 触发条件

- 用户说"写篇公众号""写个复盘""写篇深度""公众号选题"等
- 用户提供了具体话题，要求产出公众号文章

---

## Step 1: 确定文章类型

先问清楚要写哪种类型，每种类型有不同的结构和写法：

| 类型 | 适用场景 | 篇幅 | 对标来源 |
|------|---------|------|---------|
| **A. 日复盘** | 交易日收盘后，当天市场回顾+观点 | 1500-2500字 | 民工看市、刘备教授 |
| **B. 深度分析** | 行业/策略/方法论的深度长文 | 3000-5000字 | 思想钢印、饭爷、微积分 |
| **C. 周复盘** | 每周固定发布的结构化复盘 | 2000-3000字 | 自有框架 |
| **D. 轻松深度** | 用段子/故事包装的专业分析 | 1500-3000字 | 梁狗蛋、民工看市 |

---

## Step 2: 收集素材

根据文章类型，使用对应工具采集数据和素材。

### A. 日复盘素材

**统一使用 research-mcp 采集数据（`npx mcporter call "research-mcp.tool_name(...)"`）：**

#### 第一步：市场全景（必做）

```bash
# 1. A股大盘总览（指数涨跌、成交额、板块轮动）
npx mcporter call "research-mcp.market_overview()"

# 2. 主要指数详细行情（近期走势对比）
npx mcporter call "research-mcp.get_ashares_index_quote(symbol='000001.SH,000300.SH,399006.SZ,000905.SH', start_date='YYYYMMDD', end_date='YYYYMMDD')"

# 3. 全市场成交额（判断量能）
npx mcporter call "research-mcp.get_ashares_turnover(start_date='YYYYMMDD', end_date='YYYYMMDD')"

# 4. 恐慌指数（市场情绪）
npx mcporter call "research-mcp.get_ashares_gvix(start_date='YYYYMMDD', end_date='YYYYMMDD')"
```

采集到的数据模块：
| 模块 | research-mcp 工具 | 说明 |
|------|-------------------|------|
| 市场全景 | `market_overview` | 主要指数涨跌、成交额、板块概况 |
| 指数行情 | `get_ashares_index_quote` | 指数日/周/月涨跌幅 |
| 量能判断 | `get_ashares_turnover` | 全市场成交额走势 |
| 情绪指标 | `get_ashares_gvix` | 恐慌指数走势 |
| 指数估值 | `get_ashares_index_val` | PE_TTM + 历史百分位 |
| 债券收益 | `get_cn_bond_yield(maturity='10Y')` | 国债收益率（算 ERP 用） |

#### 第二步：资金面（按需）

```bash
# 北向资金（个股级别）
npx mcporter call "research-mcp.get_stock_northbound_holding(stock_code='600519', start_date='YYYYMMDD', end_date='YYYYMMDD')"

# 港股通南向资金
npx mcporter call "research-mcp.get_southbound_hkd_turnover(start_date='YYYYMMDD', end_date='YYYYMMDD')"

# 个股资金流向（主力、超大单等）
npx mcporter call "research-mcp.get_stock_fund_flow(stock_code='600519', start_date='YYYYMMDD', end_date='YYYYMMDD')"
```

#### 第三步：个股/板块数据（按需）

```bash
# 个股日K线
npx mcporter call "research-mcp.get_stock_daily_quote(stock_code='600519', start_date='YYYYMMDD', end_date='YYYYMMDD')"

# 个股估值
npx mcporter call "research-mcp.get_stock_valuation(stock_code='600519')"

# 个股行业分类
npx mcporter call "research-mcp.get_stock_industry(stock_code='600519')"
```

> **板块历史行情**：当主题段涉及某板块逻辑时，可通过查该板块代表性个股（龙头股）的 `get_stock_daily_quote` 近 30 日走势来建立上下文，也可用 `get_ashares_index_quote` 查对应行业指数。分析角度：近期累计涨跌幅、区间高低点位置、成交额变化趋势、对比大盘表现。

> **原则：聊板块逻辑时，读者需要知道"这个板块从哪来、现在在哪、可能往哪去"，而不仅仅是"今天涨了/跌了"。**

**板块逻辑解读（不许瞎猜，必须有据）：**

光有历史行情数据还不够，板块背后的产业逻辑、政策驱动、供需变化不能靠自己猜。讨论板块逻辑时，必须先搜索外部解读：

1. **搜研报（research-mcp）：** 用 `research_search` 搜索券商研报，语义匹配，找近期券商对该板块大趋势的判断（供需格局、景气周期、政策催化等）。调用方式：`npx mcporter call "research-mcp.research_search(query='{板块名} 行业', top_k=3, search_day_ago=30)"`
2. **搜产业新闻（research-mcp）：** 用 `news_search` 搜索近期产业面变化（订单、产能、价格、政策）。调用方式：`npx mcporter call "research-mcp.news_search(query='{板块名} 产业 动态', top_k=5, search_day_ago=7)"`
3. **查知识星球：** 用 `zsxq-reader` skill（`Read skills/zsxq-reader/SKILL.md` 后执行）在已加入的星球中搜索该板块关键词，提取大V对板块趋势的解读、逻辑链、核心标的等
4. **补充搜索：** WebSearch `"{板块名}" 产业 最新动态`，与 research-mcp 搜索结果交叉验证

拿到外部解读后，再结合实际盘面数据（历史走势 + 当日表现），拆解最新的板块节奏：
- 研报说的逻辑和盘面走势是否一致？（一致则加强，不一致则值得讨论）
- 板块处于什么阶段？（预期驱动 vs 业绩验证 vs 资金博弈）
- 当前节奏是主升、震荡还是退潮？

> **铁律：板块逻辑阐述必须有来源（研报、知识星球、产业新闻），不允许凭空编造产业逻辑或猜测政策方向。引用时标注来源。**

**外部信息：**
- `research-mcp.news_search` 搜当日财经热点、政策事件
- 博主参考：读 `memory/公众号博主-dig/民工看市.md`、`memory/公众号博主-dig/刘备教授.md` 看同行今天怎么写

### B. 深度分析素材

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
# 个股日K线（替代 tushare）
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

**博主参考：** 按深度写法对标读对应博主文章（见附录速查表）

### C. 周复盘素材

- 本周每日数据：连续调用 `research-mcp.get_ashares_index_quote` 拉取本周 5 个交易日的指数走势，`research-mcp.get_ashares_turnover` 拉成交额
- 周度板块表现：`research-mcp.market_overview()` 获取最新板块排名，`research-mcp.research_search(query='本周市场回顾', top_k=3, search_day_ago=7)` 查研报总结
- 资金面周度变化：`research-mcp.get_southbound_hkd_turnover` 拉南向资金周度数据
- `research-mcp.news_search(query='下周 经济数据 事件', top_k=5, search_day_ago=3)` 搜下周重要事件/数据预告

### D. 轻松深度素材

- 与深度分析相同的 research-mcp 数据基础
- `research-mcp.news_search(query='热点 段子 投资', top_k=5)` 搜社交媒体热梗素材
- 额外关注：生活化类比素材
- 博主参考：`memory/公众号博主-dig/梁狗蛋.md`、`memory/公众号博主-dig/民工看市.md`

---

## Step 3: 按类型套用写作框架

### A. 日复盘框架

> **详细指南见** `daily-review-guide.md`（数据→观点→成文全流程）
> **范文见** `review-output/公众号_2026-03-19.md`（滞胀交易主题）

**学自：民工看市（主题驱动） + 刘备教授（双段式结构）**

```
文章结构：
├── 标题（5-15字，口语化，带情绪但不标题党）
├── 核心观点引语（1句话，blockquote格式，点出今天最重要的信号）
├── 【一句话概览】指数涨跌 + 成交额 + 涨跌家数，3 行内搞定
├── 【主题段】今天最值得聊的 1-2 个话题（占全文 60%，800-1500 字）
│   ├── 不是流水账，而是围绕一个主题深入展开
│   ├── 从盘面现象 → 背后逻辑 → 对操作的影响
│   ├── 数据嵌入叙述中（不要列表格）
│   └── 穿插自身操作动态（如有）
├── 【反向信号/值得注意的点】（可选，200-300 字）
│   └── 与主流叙事相反的数据，避免单一视角
├── 【新闻简评】3-5 条精选新闻 + 每条 2-3 句点评
│   └── 点评角度：这条新闻对投资有什么影响？
├── 结尾（简短收束，明天关注什么）
└── 风险提示（固定模板）
```

**标题规律：**
- 字数：5-15 字
- 风格：口语化 + 情绪化 + 不透露全部内容
- 好标题举例："怎么就突然开始交易衰退了？""苟住！""有点麻。。""滞胀这只靴子，今天砸下来了"
- 坏标题举例："3月18日A股市场复盘""今日大盘分析"（太干，没人想点）

**关键原则：**
1. 主题驱动，不做流水账 — 每天选最有价值的 1-2 个话题深入聊
2. 有自己的判断 — 不是转述新闻，而是给出观点
3. 操作透明 — 有买卖动作就说，做错了也说
4. 敢说不知道 — "这个问题很复杂，我也没想清楚"比装懂更有信任感

**日复盘写作流程：**

```
1. 拉数据    research-mcp: market_overview → get_ashares_index_quote → get_ashares_turnover → get_ashares_gvix
                ↓
2. 补资金面  research-mcp: get_southbound_hkd_turnover + get_cn_bond_yield(10Y) + get_ashares_index_val（算 ERP）
                ↓
3. 搜新闻    research-mcp: news_search("今日 A股 市场", top_k=5) + WebSearch 补充
             按需：get_stock_daily_quote / get_stock_fund_flow（具体个股）
                ↓
4. 找故事    从数据中找 1-2 个最有解读空间的信号
             （不是最大涨跌，而是"读者明天开盘前最想知道的事"）
                ↓
5. 形成观点  发生了什么 → 为什么 → 意味着什么
                ↓
6. 写文章    按上方结构模板写，1500-2500 字
                ↓
7. 优化标题  生成 2-3 个候选，选最有好奇心驱动的
                ↓
8. 自检      见 Step 6 质量自检清单
                ↓
9. 交付      展示给用户确认
```

---

### B. 深度分析框架

**学自：思想钢印（结构化长文） + 饭爷（传导链叙事） + 微积分（数据祛魅）**

```
结构：
├── 标题（15-25字，反直觉/疑问句/对立概念）
├── 核心观点引语（blockquote，1-2 句话）
├── 【1/N 引子段】类比/故事/反常识切入
│   └── 用生活化类比降低阅读门槛，引出核心问题
├── 【2/N - (N-1)/N 分析段】多维度展开
│   ├── 每段有小标题，逻辑递进
│   ├── 数据支撑（图表、具体数字、机构观点）
│   └── 关键句式："这意味着什么？""用大白话说就是..."
├── 【N/N 结论段】回到操作层面
│   ├── 总结核心观点（3 句话以内）
│   └── 给出可操作的建议或关注方向
└── 风险提示 + 免责声明
```

**三种深度写法可选：**

| 写法 | 对标 | 核心手法 | 适用场景 |
|------|------|---------|---------|
| **传导链式** | 饭爷 | A→B→C→D 的多米诺推演 | 宏观、大宗商品、产业链 |
| **方法论式** | 思想钢印 | 提出框架 → 多案例验证 | 投资体系、选股方法、估值 |
| **祛魅式** | 微积分 | 先破（数据推翻常识）→ 后立（给出替代方案） | 揭示指数/基金/策略的真实面貌 |

**标题规律：**
- 疑问句制造认知冲突："为什么被做空的股票最后暴涨？"
- 反直觉/反常识："巴菲特只要活得够久，终会破产"
- 冒号式判断："红利不等于HALO：这些才是免疫AI的防空洞"
- 传导链暗示："油价上涨已成定局"

**关键原则：**
1. 逻辑链条至少 3 层递进 — 现象 → 原因 → 推演 → 操作含义
2. 每个观点有数据支撑 — 不空谈，用数字说话
3. 有独立观点 — 如果只是总结别人说的，不如不写
4. 系列化 — 深度文章适合做系列，形成知识网络

---

### C. 周复盘框架

**自有框架设计（综合各家优点）：**

```
结构：
├── 标题：固定栏目前缀 + 期数 + 本周关键词
│   └── 例："周复盘|第12期：科技回调，资源走强"
├── 【一、本周市场回顾】
│   ├── 主要指数周涨跌（表格形式）
│   ├── 领涨/领跌板块 Top5
│   └── 本周核心叙事（一句话总结本周市场在交易什么）
├── 【二、持仓/组合变动】
│   ├── 本周操作记录
│   └── 操作逻辑说明
├── 【三、关键信号跟踪】
│   ├── 跟踪 3-5 个自定义指标（如市场温度、估值分位数、资金流向等）
│   └── 本周变化 + 趋势判断
├── 【四、下周展望】
│   ├── 需要关注的事件/数据
│   └── 操作计划
└── 固定结尾
```

**关键原则：**
1. 格式固定、期数连续 — 让读者形成阅读习惯
2. 有自己的量化指标 — 别人无法复制的东西才是护城河
3. 实盘记录 — 真金白银的操作比任何分析都有说服力
4. 固定发布时间 — 每周几的几点，雷打不动

---

### D. 轻松深度框架

**学自：梁狗蛋（虚构小说体/段子体） + 民工看市（自嘲幽默）**

```
可选形式：

形式一：虚构小说体（梁狗蛋式）
├── "全文系虚构" 声明（合规+反讽双重功能）
├── 人物登场（固定角色：基金经理/分析师/销售）
├── 场景化对话（路演/晨会/调研）
│   └── 在对话中植入专业投资逻辑
├── 反转结尾（不直接给结论，让读者自己悟）
└── 风险提示

形式二：排比归谬体
├── 提出一个命题
├── 穷举所有条件，发现结论都一样（归谬法）
└── 在荒诞中传递真实观点

形式三：段子化复盘
├── 用段子承载观点（不是在分析后面加笑话）
├── 自嘲式表达（"在让人失望这块，恒科从没让人失望过"）
└── 跨界类比（把投资现象映射到生活场景）
```

**关键原则：**
1. 幽默是结构性组件，不是调味品 — 段子本身承载观点
2. 需要真正懂行才写得出来 — 归谬法需要穷举所有逻辑路径
3. 留白 > 直说 — 反转结尾比直接给结论有效 100 倍

---

## Step 4: 写作风格指南

### 通用风格要求

| 维度 | 要求 |
|------|------|
| **语气** | 专业但不端着，像一个懂行的朋友在聊天 |
| **用词** | 专业术语 + 口语化表达混搭，关键术语用大白话翻译一次 |
| **句式** | 短句为主，长分析拆成多段，制造阅读节奏感 |
| **观点** | 必须有独立判断，不做复读机；对了不吹，错了不删 |
| **数据** | 关键论点必须有数据支撑，标注数据来源 |
| **诚实** | 不懂就说不懂，比装懂更有信任感 |
| **留余地** | 用"大概率""如果没意外"软化判断，不把话说死 |

### 人设与语气

公众号文章以**真人博主**视角写作，**不使用小奶龙/本龙/龙相关的任何人设元素**。具体要求：
- 第一人称用"我"，但读起来像一个真人投资博主在写，不是一只龙在写
- **禁止出现**："本龙""小奶龙""奶龙""龙""卖萌""小富龙"等内部人设词汇
- **禁止**在文章中使用奶龙式语气（如撒娇、卖萌、自称龙等）
- 语气参考：专业但不端着，有观点有态度，像一个懂行的朋友在分享
- 如果账号的公众号人设尚未明确，先与用户确认

### 绝对不要

- 不要用 Markdown 加粗（`**`）— 公众号正文不需要 Markdown 格式标记，用纯文本写
- 不要写"众所周知""首先让我们来看" — 废话
- 不要纯罗列数据不给观点 — 那是数据终端不是文章
- 不要每天都看多或都看空 — 墙头草没人信
- 不要用"震惊！""暴涨！""重磅！" — 低质标题党
- 不要抄别人的观点当自己的 — 引用要标注来源
- 不要给具体个股买卖建议 — 合规红线

### 值得学习的表达技巧

**1. 类比降维（思想钢印 + 刘备教授）**
把专业概念翻译成生活常识。如"慢牛快熊"→"KTV一天健身一天 vs KTV三天进ICU三个月"。

**2. 一句话金句（表舅 + 民工看市）**
在分析中埋入一句有传播力的话。如"在让人失望这块，恒科从没让人失望过"。

**3. 传导链叙事（饭爷）**
A→B→C→D 的多米诺骨牌式推演，让读者有"恍然大悟"的快感。

**4. 自我验证（饭爷 + 民工看市）**
引用自己之前文章的判断，展示逻辑链条的连贯性。对了就说"之前聊过"，错了就复盘为什么错。

**5. 先破后立（微积分）**
先用数据推翻一个主流认知，再给出自己的替代方案。制造反差，读者印象深刻。

---

## Step 5: 标题优化

标题决定了 80% 的打开率。写完正文后，用以下清单优化标题：

### 标题自检清单

- [ ] 能引发好奇心吗？（读者看到标题会想"为什么？"）
- [ ] 有没有透露太多？（标题把结论说完了就没人点进来了）
- [ ] 像人说的话吗？（不像论文标题、不像新闻标题）
- [ ] 有情绪共振吗？（读者看到会心一笑/皱眉/好奇）
- [ ] 字数合适吗？（日复盘 5-15 字，深度 15-25 字）

### 好标题模板

| 类型 | 模板 | 举例 |
|------|------|------|
| 口语反问 | "怎么就突然XXX了？" | "怎么就突然开始交易衰退了？" |
| 反直觉 | "XXX其实是YYY" | "红利不等于HALO" |
| 情绪短句 | "XX了。。" / "苟住！" | "拐点。。" |
| 悬念 | "XXX，谁在撒谎？" | "PE报警与股息率黄金坑，谁在撒谎？" |
| 判断型 | "XXX已成定局/不远了" | "油价上涨已成定局" |

---

## Step 6: 质量自检

完稿后，逐条检查：

### 内容质检

- [ ] 有独立观点，不是复读别人的话
- [ ] 关键论点有数据/事实支撑
- [ ] 逻辑链条完整，不存在跳跃
- [ ] 没有给具体个股买卖建议（合规红线）
- [ ] 涉及投资内容有风险提示/免责声明
- [ ] 没有抄袭，引用有标注

### 表达质检

- [ ] 读出声来像人说的话，不像 AI 写的
- [ ] 开头 3 行能留住人
- [ ] 没有废话段落（每段都有信息量）
- [ ] 短句为主，阅读节奏流畅
- [ ] 标题通过了上面的自检清单

### 格式质检

- [ ] 标题长度合适
- [ ] 正文有分段，不是一坨
- [ ] 关键数据/观点有加粗或其他强调
- [ ] 结尾有收束，不是突然断掉

---

## Step 7: 交付与发布

### 7.1 展示文章

将完整文章（标题 + 正文 + 风险提示）展示给用户确认。附上：
- 文章类型和字数
- 核心观点概述（1-2 句话）
- 建议的发布时间（如有）

### 7.2 用户确认

等待用户对内容的确认或修改意见。修改后需重新展示。

### 7.3 封面配图（必做）

> **铁律：文章确认后，必须走 `mp-cover-art` skill 生成封面配图，不可跳过。**

1. Read `skills/mp-cover-art/SKILL.md`
2. 按 mp-cover-art 流程：分析文章 → 选模板 → 推荐方案 → 研究部确认 → 生图 → 展示给研究部 → 保存
3. 封面保存到 `workspace/images/cover/YYYY-MM-DD/`

### 7.4 发布方式

确认后按用户指定的方式发布：

| 方式 | 操作 | 说明 |
|------|------|------|
| **浏览器发布** | 用 browser 工具（`profile: "bot11"`）打开微信公众平台后台，手动创建图文并粘贴内容 | 需已登录公众号后台 |
| **用户自行发布** | 将文章以 Markdown 格式保存到 `review-output/` 目录，告知用户文件路径 | 用户自行复制到公众号后台 |
| **保存草稿** | 将文章保存到 `memory/公众号草稿/` 目录待后续发布 | 适合需要多篇文章排期的情况 |

> **浏览器发布公众号的详细流程待用户确认后沉淀为独立 skill（`mp-browser-publish`）。** 在此之前，优先使用"用户自行发布"方式。

### 7.4 记录

发布后记录到当日日记 `memory/YYYY-MM-DD.md`：
- 文章标题、类型、字数
- 发布平台和时间
- 使用的数据来源和研究工具
- 写作过程中的经验或教训

---

## 附录 A：research-mcp 工具链速查

所有数据统一通过 `npx mcporter call "research-mcp.tool_name(...)"` 获取。工具详情见 `Read skills/research-mcp/SKILL.md` 及其子模块。

| 场景 | research-mcp 工具 | 适用文章类型 |
|------|-------------------|-------------|
| **市场全景** | `market_overview()` | 日复盘、周复盘 |
| **指数行情** | `get_ashares_index_quote(symbol, start_date, end_date)` | 日复盘、周复盘 |
| **成交额** | `get_ashares_turnover(start_date, end_date)` | 日复盘、周复盘 |
| **恐慌指数** | `get_ashares_gvix(start_date, end_date)` | 日复盘 |
| **指数估值** | `get_ashares_index_val(symbol)` | 日复盘、深度分析 |
| **个股行情** | `get_stock_daily_quote(stock_code, start_date, end_date)` | 所有类型 |
| **个股估值** | `get_stock_valuation(stock_code)` | 深度分析 |
| **个股资金** | `get_stock_fund_flow(stock_code, start_date, end_date)` | 日复盘、深度分析 |
| **北向持股** | `get_stock_northbound_holding(stock_code, start_date, end_date)` | 日复盘、深度分析 |
| **港股大盘** | `get_hshares_market_overview()` | 深度分析（全球视角） |
| **美股指数** | `get_usstock_index_quote(symbol='DJIA.GI,SPX.GI,NDX.GI')` | 深度分析（全球视角） |
| **中国宏观** | `get_cn_macro_data(category='cpi,ppi,pmi,m2')` | 深度分析 |
| **美国宏观** | `us_macro_simple()` | 深度分析 |
| **国债收益率** | `get_cn_bond_yield(maturity='10Y')` | 日复盘（ERP）、深度分析 |
| **中美利差** | `get_bond_yield_spread(spread_type='cn_vs_us', maturity='10Y')` | 深度分析 |
| **商品行情** | `commodity_data(symbol='AU9999')` | 深度分析 |
| **搜研报** | `research_search(query, top_k, search_day_ago)` | 所有类型 |
| **搜新闻** | `news_search(query, top_k, search_day_ago)` | 所有类型 |
| **基金分析** | `get_fund_comprehensive_analysis(fund_code)` | 深度分析 |
| **重仓基金** | `fund_stock_holdings(stock_code)` | 深度分析 |

---

## 附录 B：对标博主速查表

需要找灵感或参考时，去读对标博主的近期文章：

| 博主 | 文章摘要 | 核心学习点 |
|------|---------|-----------|
| **思想钢印** | `memory/公众号博主-dig/思想钢印.md` | 1/N分段式长文、类比开头、行为金融框架、系列化写作 |
| **梁狗蛋** | `memory/公众号博主-dig/梁狗蛋.md` | 虚构小说体、人物IP（小刘/老王）、归谬法、反转结尾 |
| **民工看市** | `memory/公众号博主-dig/民工看市.md` | 段子化复盘、波动率止盈框架、自嘲幽默、敢说不知道 |
| **刘备教授** | `memory/公众号博主-dig/刘备教授.md` | 双段式结构（市场+杂谈）、历史类比、口语黑话、万物皆周期 |
| **饭爷的江湖** | `memory/公众号博主-dig/饭爷的江湖.md` | 供需钱框架、传导链叙事、预判验证体系、口语化宏观分析 |
| **微积分量化价投** | `memory/公众号博主-dig/微积分量化价投.md` | 祛魅方法论、穿透底层数据、先破后立、Q1-Q10暴力回测 |

> 路径为相对路径，基于 `workspace-bot11/`。完整文章在 `memory/公众号博主/` 目录下对应文件中。
