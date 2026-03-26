---
name: energy-chem-tracker
description: >
  能源化工产业链跟踪技能。监控原油/煤炭/天然气三大上游及其衍生品（甲醇、PTA、
  乙二醇、PE、PP、PVC、烧碱、尿素等）的价格、库存、开工率、利润、新增产能，
  输出产业链日报、周报、事件点评，支持小红书和公众号两个渠道。
---

# 能源化工产业链跟踪 skill

跟踪中国能源化工产业链核心品种，覆盖石油化工、煤化工、盐化工三大路线。重点关注：价格趋势、库存周期、开工率变化、利润传导、新增产能投放。输出可用于小红书笔记、公众号文章、飞书提醒。

---

## 1. 触发条件

### 定时触发（heartbeat）

| 时间 | 任务 | 说明 |
|------|------|------|
| 每日 9:00 | **早盘信息巡逻** | 搜索隔夜外盘（原油/天然气）、国内期货夜盘、重要数据发布 |
| 每日 16:00 | **收盘数据更新** | 更新当日期货收盘、现货价格变动、库存数据到 `daily-feed.md` |
| 每周五 20:00 | **周报数据采集** | 汇总本周各品种价格涨跌、库存变化、开工率、利润走势 |
| 每周日 10:00 | **周报生成** | 输出能源化工周报草稿 |

### 被动触发

- 研究部说 "查一下化工"、"PTA怎么样"、"甲醇行情"、"化工周报" 等
- 原油单日波动 > 3% 或化工品种单日涨跌停
- 知识星球 / 雪球出现化工板块相关热帖
- 重大产能投放 / 检修 / 政策（如环保限产）

---

## 2. 信息源与工具

### 2.1 数据源优先级

**大宗商品价格数据优先级**：Mysteel（钢联）> 卓创资讯 > 隆众资讯 > 百川盈孚 > 生意社

Mysteel 是化工品现货价格、库存、开工率的首选数据源，数据准确性和更新频率最高。查价格时优先搜 Mysteel。

### 2.2 联网搜索

```bash
# 首选 Mysteel（价格/库存/开工率）
web_search("mysteel 化工 今日价格")
web_search("mysteel PTA 甲醇 乙二醇 价格")
web_search("mysteel 聚烯烃 库存 周度")
web_search("mysteel 化工品 开工率")

# 补充源
web_search("原油 布伦特 WTI 最新价格")
web_search("卓创资讯 化工品 周度数据")

# 利润与新产能
web_search("化工品种 利润 盈亏 本周")
web_search("能源化工 新增产能 2026 投产")
web_search("XX品种 检修计划 本月")
```

关键词库（轮换使用）：
- 上游类：`原油 布伦特 WTI`、`动力煤 焦煤`、`天然气 LNG`、`LPG 液化气`
- 石化链：`PTA 价格`、`乙二醇 EG`、`苯乙烯 EB`、`甲醇 价格`、`PE LLDPE HDPE`、`PP 聚丙烯`
- 煤化工：`煤制烯烃 MTO`、`煤制乙二醇`、`尿素 价格`、`电石法PVC`
- 盐化工：`PVC 烧碱`、`纯碱 价格`、`氯碱平衡`
- 综合类：`Mysteel 化工`、`卓创资讯 化工`、`隆众资讯 能源`、`生意社 化工`、`百川盈孚`

### 2.3 浏览器信息源（用 bot11 profile）

| 平台 | 用法 | 关注内容 |
|------|------|---------|
| **Mysteel（钢联）** | `openclaw browser navigate "https://www.mysteel.com/" --browser-profile bot11` | **首选价格源**。化工品现货价格、库存、开工率、利润周报 |
| **金十数据** | `openclaw browser navigate "https://www.jin10.com/" --browser-profile bot11` | 原油/天然气实时快讯、EIA库存数据、OPEC决议 |
| **雪球** | `openclaw browser navigate "https://xueqiu.com/k?q=化工+能源" --browser-profile bot11` | 化工个股讨论、券商研报观点、板块异动 |
| **知识星球** | 通过 zsxq-reader skill 读取 | 黑马调研中化工/能源相关研报和纪要 |
| **卓创资讯** | web_search("site:sci99.com 化工 价格") | 补充 Mysteel 的品种覆盖 |
| **百川盈孚** | web_search("百川盈孚 XX品种 价格") | 产能、产量、开工率数据 |

### 2.4 数据接口

```python
# 期货行情（akshare）
import akshare as ak

# 能源化工期货主力合约
# 大商所(DCE)：LLDPE(l), PP(pp), PVC(v), 乙二醇(eg), LPG(pg), 苯乙烯(eb)
# 郑商所(CZCE)：PTA(TA), 甲醇(MA), 尿素(UR), 纯碱(SA), 烧碱(SH), 短纤(PF)
# 上期能源(INE)：原油(sc)

# 获取主力合约行情
df = ak.futures_main_sina(symbol="TA0")  # PTA主力
df = ak.futures_main_sina(symbol="MA0")  # 甲醇主力
df = ak.futures_main_sina(symbol="l0")   # LLDPE主力
df = ak.futures_main_sina(symbol="sc0")  # 原油主力

# 化工板块股票
df = ak.stock_board_concept_cons_em(symbol="化工")
df = ak.stock_board_industry_cons_em(symbol="化学制品")
```

---

## 3. Memory 文件结构

> 所有数据文件路径相对于 `workspace-bot11/memory/energy-chem/`。
> 该目录由 bot 自主维护，不需要研究部审批。

```
memory/energy-chem/
├── daily-feed.md              # 每日资讯流水（滚动保留 7 天）
├── price-tracker.md           # 核心品种价格跟踪表（每日更新，首选 Mysteel）
├── inventory-tracker.md       # 库存数据跟踪（每周更新）
├── capacity-pipeline.md       # 新增产能投产计划（月度更新）
├── margin-monitor.md          # 各品种各路线利润跟踪（每周更新）
├── stock-watchlist.md         # 股票标的跟踪（估值/催化/观点更新）
├── investment-themes.md       # 当前活跃的投资主题
├── research-notes.md          # 知识星球/雪球研报摘要
├── cycle-positioning.md       # 各品种周期位置判断（每季度审视）
├── event-archive.md           # 重大事件记录（政策/事故/产能变动）
├── content-archive.md         # 已发布内容记录
├── weekly/                    # 周报存档
│   └── 2026-WXX.md
└── chain-analysis/            # 各品种深度分析
    ├── pta.md
    ├── methanol.md
    ├── polyolefins.md
    ├── pvc-caustic.md
    ├── urea.md
    └── crude-oil.md
```

### 维护规则

| 文件 | 更新频率 | 说明 |
|------|---------|------|
| `daily-feed.md` | 每日追加 | 超过 7 天的内容移除，精华提炼到品种分析文件 |
| `price-tracker.md` | 交易日收盘后 | 非交易日跳过。格式见 `price-tracker-template` 子文档 |
| `inventory-tracker.md` | 每周五 | 多数库存数据为周度发布 |
| `capacity-pipeline.md` | 每月初 | 新增确认的投产/退出信息随时更新 |
| `margin-monitor.md` | 每周 | 利润大幅变化时随时更新 |
| `chain-analysis/` | 有重大变化时 | 检修/投产/政策/事故 |
| `event-archive.md` | 重大事件后 | 立即记录 |

---

## 4. 配套技能

| 技能 | 何时使用 |
|------|---------|
| `xhs-op/内容策划` | 将化工内容纳入小红书日常选题 |
| `mp-content-writer` | 输出公众号长文（周报、品种深度） |
| `zsxq-reader` | 从知识星球获取化工/能源相关研报纪要 |
| `xhs-browser-publish` | 发布小红书笔记 |
