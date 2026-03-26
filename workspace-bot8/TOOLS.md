<!-- TOOLS_COMMON:START -->

---

## Xiaohongshu (XHS) Operations

**Must `Read skills/xhs-op/mcp-tools.md` before any XHS operation. No SKILL.md = guaranteed failure.**

- Call via `npx mcporter call "xiaohongshu-mcp.tool_name(...)"` — never `curl` the port directly
- `account_id` rule: **no tool accepts `account_id`** — identity is determined by port. Passing it causes errors. Only exception: `publish_content` (optional)
- Publishing goes through the publisher (`skills/submit-to-publisher/SKILL.md`); compliance review is handled there
- On timeout: check login status first; if logged out, follow SKILL.md Step 0; if mcporter reports `offline`, report to HQ
- Never retry timed-out operations repeatedly; never start/compile/modify MCP source code

---

## ⛔ System Admin — Strictly Forbidden

**Only HQ (mag1) may execute these. All sub-bots are prohibited:**

- `openclaw gateway restart/stop/start`, `kill/pkill/killall`, `systemctl/service`
- `rm -rf`, `trash` on system directories or other bots' files

**Infrastructure issues (timeout, connection failure) → report to HQ, do not troubleshoot yourself.**

---

## Web Browsing

- **Must pass `profile: "your_account_id"`** — omitting it causes timeout
- On launch failure → `bash /home/rooot/.openclaw/scripts/ensure-browser.sh your_account_id`
- **`browser close` is mandatory after every task, success or failure** — no exceptions. Stale tabs accumulate across sessions and spike CPU. Any skill that opens a browser must close it before finishing.
- `ref` is only valid for the current snapshot; re-snapshot after page changes
- No Chrome extensions; don't retry timeouts repeatedly
- Before starting: run `browser tabs profile="your_account_id"` to check for stale tabs from previous sessions, close any you find
- **On browser timeout / "can't reach browser control service"**: do NOT fall back to web_fetch immediately. First run `bash /home/rooot/.openclaw/scripts/ensure-browser.sh your_account_id` to start Chrome, then retry the browser tool once. Only fall back if it still fails after that.

---

## Financial Data: Research MCP

直连 **research-mcp**，92 个金融数据工具，分 10 个类别。

调用：`npx mcporter call "research-mcp.tool_name(...)"`

**使用前必须 `Read skills/research-mcp/SKILL.md`**，根据意图路由表找到对应子模块（fund.md / stock.md / market.md / bond.md / macro.md / news.md），再 Read 子模块获取具体工具的参数和用法。

10 个工具箱：`market_ashares`(8) · `market_hk`(6) · `market_us`(5) · `stock`(29) · `fund`(22) · `fund_screen`(7) · `bond`(5) · `macro`(3) · `commodity`(2) · `news_report`(5)

---

## Inter-Agent Communication (Message Bus)

### Rules

1. **Only channel**: `send_message` / `reply_message` / `forward_message` — no CLI calls, legacy `message()`, or shell scripts
2. **Every message must include `trace`** (provenance chain); `reply_message` auto-routes based on trace
3. **⛔ Strict single-round**: request → process → `reply_message` → **done**. One request = one reply. Put all data in the reply — never split into multiple messages

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

### ⛔ Incoming `[MSG:xxx]` Messages

`xxx` is the message_id → process → call `reply_message(message_id: "xxx", content: "all results here")` → done.

**Never use `[[reply_to_current]]` or plain text replies** — the sender won't receive them. Always `reply_message`, whether success or failure.

---

## Image Generation: image-gen-mcp

生图用 `image-gen-mcp.generate_image(style, content)`。模型可选 `banana`（默认）或 `banana2`。图片保存到 `/tmp/image-gen/` 下。

```
npx mcporter call 'image-gen-mcp.generate_image(style: "扁平插画风", content: "一只猫在看股票K线图")'
```

---

## Tool Priority

1. **memory** → check history first, update incrementally
2. **research-mcp** → financial data (Read SKILL.md first)
3. **browser** → Xueqiu, EastMoney research reports, etc.
4. **MCP search** → supplementary search, overseas data
5. **xiaohongshu-mcp** → note management, interactions
6. **message bus** → inter-agent communication
<!-- TOOLS_COMMON:END -->



# TOOLS.md - 工具使用规范

## 联网搜索

- 内置 `web_search` 已禁用，调用会失败
- 联网搜索通过 browser 工具访问搜索引擎或目标站点

## 网页浏览

**必须使用：OpenClaw 自带 browser 工具**

- 严禁使用 Chrome 插件或任何浏览器扩展
- 需要登录或 JS 渲染的页面用 browser 工具处理

### 投研必访站点（每次行业研究必须覆盖至少2个）

**雪球 xueqiu.com** — 投资者讨论、机构观点、实时情绪
- 行业/股票搜索：`https://xueqiu.com/search?q={关键词}`
- 个股主页：`https://xueqiu.com/S/SH{6位代码}` 或 `SZ{6位代码}`（含置顶讨论和最新观点）
- 重点看：置顶帖、近期高赞帖子、机构研究员发文

**东方财富 eastmoney.com** — 研报、新闻、股吧
- 行业研报（最重要）：`https://data.eastmoney.com/report/industry.jshtml`
- 个股研报：`https://data.eastmoney.com/report/stock.jshtml?code={ts_code}`
- 行业新闻：`https://so.eastmoney.com/news/s?keyword={行业名称}`
- 股吧（舆情参考）：`https://guba.eastmoney.com/list,{6位代码}.html`

**同花顺 10jqka.com.cn** — 新闻聚合、行业动态
- 行业新闻：`https://news.10jqka.com.cn/`搜索行业关键词
- 个股资讯：`https://stockpage.10jqka.com.cn/{6位代码}/`

### browser 使用原则

- 每次行业研究（sector-pulse）：**必须**访问东方财富研报 + 雪球相关讨论
- 每次个股研究（research-stock）：访问个股雪球主页 + 东方财富个股研报
- 浏览后注意时间核验：页面上的"今天"是网站服务器时间，发帖/发布时间才是内容时间

## 金融数据：Tushare 工具（直接调用，无需搜索）

A 股量化数据优先用 Tushare 工具，不要去搜索：

| 工具名 | 用途 |
|--------|------|
| `tushare_stock_basic` | 股票列表、基本信息 |
| `tushare_daily` | 日线行情（OHLCV） |
| `tushare_daily_basic` | 估值数据（PE/PB/PS/市值） |
| `tushare_income` | 利润表 |
| `tushare_balancesheet` | 资产负债表 |
| `tushare_cashflow` | 现金流量表 |
| `tushare_fina_indicator` | 财务指标（ROE/ROA/毛利率等） |
| `tushare_forecast` | 业绩预告 |
| `tushare_moneyflow_hsgt` | 北向/南向资金日汇总 |
| `tushare_hsgt_top10` | 沪深港通十大成交股 |
| `tushare_top10_holders` | 前十大股东 |
| `tushare_index_daily` | 指数日线（沪深300、创业板等） |
| `tushare_trade_cal` | 交易日历 |

股票代码格式：`600519.SH`（上交所）、`000001.SZ`（深交所）。日期格式：`YYYYMMDD`。

## 研究工具优先级

1. **memory（QMD）** → 先检索历史研究，有则增量更新
2. **Tushare 工具** → A 股行情、财务、北向资金（结构化数据）
3. **browser 工具** → 雪球、东方财富研报、同花顺（**必须执行，不是可选**）
4. **browser 搜索** → 补充搜索、验证、海外数据

## 投研技能地图

| 技能 | 触发场景 |
|------|---------|
| `/sector-pulse` | 行业深度研究（旗舰） |
| `/industry-earnings` | 财报季行业横向比较 |
| `/flow-watch` | 北向资金行业轮动 |
| `/market-environment-analysis` | 全球宏观环境：risk-on/risk-off、美股/汇率/大宗/VIX |
| `/research-stock` | 个股快速数据查询（估值/财务/资金） |
| `/technical-analyst` | 用户提供图表时的技术面分析 |
| `/news-factcheck` | 核查资讯/研报观点的真实性和时效性 |
| `/stock-watcher` | 管理个人自选股列表，查看持仓行情摘要 |
| `/record` | 研究完成后保存结论到记忆系统 |
| `/self-review` | 定期复盘 + 自我进化 |

## 投研常用信息源

- 行业研报：东方财富 `data.eastmoney.com/report/`、同花顺研报
- 投资者讨论：雪球 `xueqiu.com`
- 公司公告：巨潮资讯 `cninfo.com.cn`、上交所 `sse.com.cn`、深交所 `szse.cn`
- 行业数据：IDC、Gartner、公司 IR 页面
- 深度报道：36kr、晚点 LatePost、路透中文、财新
