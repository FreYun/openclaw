<!-- TOOLS_COMMON:START -->

---

## System Admin — Strictly Forbidden

**Only HQ (mag1) may execute these. All sub-bots are prohibited:**

- `openclaw gateway restart/stop/start`, `kill/pkill/killall`, `systemctl/service`
- `rm -rf`, `trash` on system directories or other bots' files

**Infrastructure issues (timeout, connection failure) → report to HQ, do not troubleshoot yourself.**

---

## Inter-Agent Communication (Message Bus)

### Rules

1. **Only channel**: `send_message` / `reply_message` / `forward_message` — no CLI calls, legacy `message()`, or shell scripts
2. **Every message must include `trace`** (provenance chain); `reply_message` auto-routes based on trace
3. **Strict single-round**: request → process → `reply_message` → **done**. One request = one reply. Put all data in the reply — never split into multiple messages

### Tools

| Tool | Purpose |
|------|---------|
| `send_message` | Start a new conversation/request |
| `reply_message` | Return results (defaults to Feishu user; add `also_notify_agent: true` to also wake upstream agent) |
| `forward_message` | Forward to another agent (trace auto-appended) |
| `get_message` / `list_messages` | Query message details / inbox |

### Trace Construction

```
send_message(to: "target_agent", content: "...", trace: [{
  agent: "your_account_id", session_id: "current_session_id",
  reply_channel: "feishu", reply_to: "ou_xxx", reply_account: "your_account_id"
}])
```

`reply_channel/reply_to/reply_account`: only set at the origin hop. Intermediate forwards auto-append trace.

### Incoming `[MSG:xxx]` Messages

`xxx` is the message_id → process → call `reply_message(message_id: "xxx", content: "all results here")` → done.

**Never use `[[reply_to_current]]` or plain text replies** — the sender won't receive them. Always `reply_message`, whether success or failure.

---

## Image Generation: image-gen-mcp

生图用 `image-gen-mcp.generate_image(style, content)`。模型可选 `banana`（默认）或 `banana2`。

```
npx mcporter call 'image-gen-mcp.generate_image(style: "扁平插画风", content: "一只猫在看股票K线图")'
```

---

## Memory Recall: mem0_search

语义记忆检索——跨历史会话、日记、发帖、研究报告做语义搜索。当你需要回忆"我之前对 X 说过/想过/做过什么"时调用，替代手动 grep 文件。

| 参数 | 说明 |
|------|------|
| `query` | 自然语言检索词 |
| `scope` | `self`（默认，仅查自己的记忆）/ `all`（跨 bot 查询） |

```
mem0_search(query: "黄金ETF写过哪些角度", scope: "self")
```

典型场景：发文前查重、承接上篇话题、回忆过往研究结论、避免重复踩坑。

---

## Tool Priority

1. **memory** → check history first, update incrementally
2. **research-mcp** → financial data
3. **browser** → Xueqiu, EastMoney research reports, etc.
4. **MCP search** → supplementary search, overseas data
5. **xiaohongshu-mcp** → note management, interactions
6. **message bus** → inter-agent communication
<!-- TOOLS_COMMON:END -->







# TOOLS.md - 小奶龙的工具箱

## 🚨 浏览器 profile 铁律（最高优先级）

> **无论何时何地，调用 `browser` 工具的任何操作（start / open / snapshot / act 等），必须显式传 `profile: "bot11"`（CDP 端口 18811）。**
> **⛔ 绝对禁止使用 `profile: "openclaw"`（18800）、`profile: "chrome"` 或省略 profile 参数 —— 省略会 fallback 到默认的 openclaw（18800），导致串号。**
> **没有任何例外。每一次调用都要检查自己传了 `profile: "bot11"`。**
> **即使你在其他地方看到 `profile: "openclaw"` 的示例，也不要跟着用——那不是你的 profile。**

---

## 数据源总览

| 工具 | 用途 | 费用 | 限制 |
|------|------|------|------|
| Web 搜索 | 实时新闻、政策、观点、任意信息 | 免费 | 每月 2000 次，5 QPS |
| akshare | 板块行情、概念板块、个股日线、行业排名 | 免费 | 无次数限制，但接口偶尔不稳定 |
| Tushare | 股票/指数/财务数据，更结构化稳定 | 免费（积分制） | 高级接口需要积分，每分钟 500 次 |

**选择原则：**
- 查实时新闻、政策、观点 → Web 搜索
- 查板块行情、概念热点、行业排名 → akshare（快、免费、无需 Token）
- 查个股日线、财务数据、指数历史 → Tushare（更稳定、字段更全）
- 两个数据源结果有出入时，以 Tushare 为准

---

## Tushare API

- **Token：** `ed396239156fa590b3730414be7984b029e021c3531e419f6bc170d4`
- **初始化方式：**
```python
import tushare as ts
ts.set_token('ed396239156fa590b3730414be7984b029e021c3531e419f6bc170d4')
pro = ts.pro_api()
```
- **代码格式：** 上交所 `.SH`，深交所 `.SZ`，北交所 `.BJ`
- **日期格式：** `YYYYMMDD`（如 `20260301`）
- **数据更新：** 日线行情交易日 15-17 点更新
- **详细参考：** `memory/Tushare API 使用指南.md`

### 常用接口

| 接口 | 用途 | 示例 |
|------|------|------|
| `pro.daily()` | 个股日线行情 | `pro.daily(ts_code='000001.SZ', start_date='20260101')` |
| `pro.index_daily()` | 指数日线行情 | `pro.index_daily(ts_code='000001.SH')` |
| `pro.daily(trade_date=)` | 某日全市场行情 | `pro.daily(trade_date='20260301')` |
| `pro.income()` | 利润表 | 需 2000 积分 |
| `pro.balancesheet()` | 资产负债表 | 需 2000 积分 |
| `pro.fund_nav()` | 基金净值 | 需 2000 积分 |

### 实时行情接口（盘中必须用这些，不要用 akshare 全量拉取）

```python
# 1. 实时快照 — 当前价、开高低、买五卖五、成交量额
#    注意：用旧版 ts 接口，代码用6位纯数字（不带 .SZ/.SH）
df = ts.get_realtime_quotes('000001')              # 单只
df = ts.get_realtime_quotes(['000001','600519'])   # 多只
# 返回字段：name, open, pre_close, price, high, low, bid, ask,
#           volume, amount, b1_v~b5_v, b1_p~b5_p, a1_v~a5_v, a1_p~a5_p,
#           date, time, code

# 2. 实时分钟K线 — 日内走势结构
#    用 Pro API，代码带 .SZ/.SH 后缀
#    freq: 1min / 5min / 15min / 30min / 60min
#    限频：每分钟最多 2 次调用
df = pro.stk_mins(ts_code='000001.SZ', freq='5min')
# 返回字段：ts_code, trade_time, open, high, low, close, vol, amount
```

**为什么优先用 tushare 而不是 akshare 取实时行情**：
- `ts.get_realtime_quotes()` 按代码精准查询，秒级返回
- `ak.stock_zh_a_spot_em()` 拉全市场 5000+ 股票再过滤，慢且浪费
- tushare 返回的 `name` 字段可以验证代码对应的股票名称，避免代码搞错

---

## akshare

免费开源，无需 Token，直接 `import akshare as ak` 即可。

### 常用接口

| 接口 | 用途 | 返回字段 |
|------|------|----------|
| `ak.stock_zh_a_hist(symbol, period="daily", adjust="qfq")` | 个股历史日线 | 日期、开高低收、涨跌幅、成交量 |
| `ak.stock_board_concept_name_em()` | 概念板块列表+实时行情 | 板块名称、涨跌幅、振幅、涨跌额 |
| `ak.stock_board_industry_name_em()` | 行业板块列表+实时行情 | 同上 |
| `ak.stock_board_industry_rank_em()` | 行业板块涨跌排名 | 排名、板块名、涨跌幅 |
| `ak.stock_board_concept_hist_em(symbol, period="分时")` | 概念板块分时数据 | 时间、价格、涨跌幅 |

### 注意事项
- akshare 接口名和参数可能随版本更新变化，报错时先查最新文档
- 板块代码用东方财富的编码体系
- 个股代码不带后缀（如 `600036` 而非 `600036.SH`）

---

## Python 脚本

所有脚本统一放在 `scripts/` 目录下，按功能分类。Token 等配置集中在 `scripts/config.py`。

### 统一配置

`scripts/config.py` — Tushare Token、默认数据源等。所有脚本通过 `from config import *` 引入。

### 行情类 `scripts/market/`

| 脚本 | 用途 | 使用方式 |
|------|------|----------|
| `board_ranking.py` | 行业板块 + 概念板块涨跌排名 | `python scripts/market/board_ranking.py [akshare\|tushare]` |
| `stock_query.py` | 按板块查个股行情（今日 + 3天涨跌幅） | `python scripts/market/stock_query.py [akshare\|tushare]` |
| `v_shape_scan.py` | V 型反转板块扫描（高振幅 + 收盘上涨） | `python scripts/market/v_shape_scan.py` |
| `limit_down_scan.py` | 连续一字跌停股票扫描 | `python scripts/market/limit_down_scan.py [start_date] [end_date] [min_days]` |

#### limit_down_scan.py 说明

- **用途：** 扫描指定时间区间内连续一字跌停的股票，统计连续天数、起止日期、累计跌幅
- **参数：** `start_date`（YYYYMMDD，默认30天前）、`end_date`（YYYYMMDD，默认今天）、`min_days`（最少连续天数，默认2）
- **数据源：** 历史日用 Tushare `pro.daily(trade_date=)`；若 end_date 包含当日，自动用 akshare 实时行情判断今日是否仍在跌停
- **一字跌停判定：** 开=高=低=收 且跌幅达板级阈值（主板 -9.8%、创业板/科创板 -19.8%、北交所 -29.8%）
- **触发场景：** 小富龙说「帮我看看 xxx 时间的连续跌停股票」时，直接运行此脚本
- **示例：** `python scripts/market/limit_down_scan.py 20260101 20260311 3`

### 数据类 `scripts/data/`

| 脚本 | 用途 | 使用方式 |
|------|------|----------|
| `index_overview.py` | 大盘指数概览 + 全市场涨跌家数 | `python scripts/data/index_overview.py` |
| `portfolio_update.py` | 旅游基金每日持仓收益更新 | `python scripts/data/portfolio_update.py [akshare]` |

#### portfolio_update.py 说明

- **输入：** `positions/holdings.json`（持仓配置）
- **输出：** `portfolio-history/YYYY-MM-DD.md`（日报）+ `portfolio-summary.md`（总览）
- **流程：** 读取持仓 → 使用 akshare `fund_open_fund_info_em` 获取基金最新净值 → 估算市值变动 → 更新 holdings.json → 生成报告
- **定时执行：** 每日 23:00 自动运行（心跳巡检兜底）
- **手动执行：** 持仓变动后手动触发，或心跳巡检发现当日快照缺失时触发

### 脚本规范

- 新脚本按类别放入对应子目录（行情→market，数据→data，分析→analysis）
- Token 和通用配置一律写在 `config.py`，不要硬编码到脚本里
- 行情类脚本可以按需在 akshare / Tushare 之间切换；**基金净值相关脚本使用 akshare**（手续费率用接口返回的原始值，不再额外乘系数）
- 旧版脚本归档在 `scripts/_archive/`，仅供参考

---

## 商业航天跟踪

- **Skill：** `skills/space-tracker/SKILL.md` — 商业航天产业跟踪，包括发射日历维护、核心标的监控、产业动态巡逻、内容输出（小红书/公众号/飞书）
- 涉及发射提醒、航天概念股、产业链分析等操作时，**先读此 Skill 再执行**
- 数据源优先级：维基百科发射列表 → 联网搜索 → 知识星球/雪球补充
- 概念股行情用 akshare（`商业航天`板块 BK0963、`卫星互联网`板块 BK0921）

---

## 知识星球

通过浏览器（profile: `bot11`）访问已登录的知识星球网页版，提取话题内容。

- **Skill：** `skills/zsxq-reader/SKILL.md` — 涉及知识星球的任何操作（浏览、搜索、巡检、深度阅读），**一律先读此 Skill 再操作，禁止裸用 browser 工具**
- **已加入星球、页面选择器、滚动加载方式、输出格式等**均以 SKILL.md 为准

---

## 浏览器 / 小红书自动化

用于小红书等需要登录的平台操作。

- **默认浏览器：** 使用 **小奶龙专属独立浏览器**。调用 `browser` 工具时（start / open / snapshot / act 等）默认传 `profile: "bot11"`（CDP 端口 18811），不要用 `profile: "openclaw"` 或 `profile: "chrome"`
- 通过 OpenClaw 内置的 browser 工具调用
- **小红书相关 Skill（一律用浏览器方式）：**
  - `skills/xhs-browser-publish/SKILL.md` — 通过 OpenClaw 浏览器操作创作者中心网页，完成登录、发图文/视频/长文、浏览、评论、点赞收藏等。
    > **铁律：必须先 `Read skills/xhs-browser-publish/SKILL.md` 把完整流程加载到上下文，再动手操作浏览器。禁止跳过 skill 直接裸用 browser 工具。**
    - **执行顺序：** 严格按 SKILL.md 的 Step 0 → Step 1 → Step 2/3/4 逐步执行，不跳步
    - 用 browser 工具（`profile: "bot11"`）操作创作者中心网页完成图文/视频/长文发布
    - **话题标签：** 必须在正文输完后**逐个添加**（输入 `#` + 关键词 → 从弹出浮层点选），不能跟正文一起粘贴
  - **发布前**：对照 **`memory/小红书限流规则备忘.md`** 做敏感词与限流自检后再发。

---

## Web 搜索

阿里云百炼 MCP WebSearch 服务。

- **MCP URL：** `https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/mcp`
- **API Key：** `sk-3db2ca07665b49e8a8cf44de44ebf6e6`
- **工具名：** `bailian_web_search`
- **免费额度：** 每月 2000 次
- **限流：** 5 QPS
- **调用方式：** MCP `tools/call`，参数 `query`（搜索词）+ 可选 `count`（结果数量，默认 5）

---

_新工具用熟了就更新到这里。这是小奶龙的速查手册。_
