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



# TOOLS.md - bot2 工具配置


---

## Bot 专属配置

- **account_id**: `bot2`
- **小红书 MCP 端口**: 18062（共享实例，已配置在 mcporter.json）

---

## 工具使用

**完整工具优先级和使用方式见 `memory/research/产业链研究流程.md` 的"工具优先级速查"章节。**

Browser 工具必须传 `profile: "bot2"`，不要省略。

---

## TMT 专业信息源

### 半导体

| 站点 | URL | 关注内容 |
|------|-----|---------|
| 集微网 | jiwei.com | 芯片产业链新闻、国产替代进度、晶圆厂扩产 |
| 芯智讯 | icsmart.cn | 半导体行业深度分析、设备材料动态 |
| 半导体行业观察 | semiinsights.com | 行业趋势、技术路线、制程演进 |
| DIGITIMES | digitimes.com | 亚太半导体供应链数据、产能追踪 |

### AI/算力

| 站点 | URL | 关注内容 |
|------|-----|---------|
| 量子位 | qbitai.com | AI 芯片、大模型、算力基础设施 |
| 机器之心 | jiqizhixin.com | AI 技术趋势、行业应用 |
| The Information | theinformation.com | 硅谷大厂 AI 战略、算力采购 |

### 消费电子 & 通信

| 站点 | URL | 关注内容 |
|------|-----|---------|
| 电子工程专辑 | eet-china.com | 消费电子零部件、新品拆解 |
| C114 通信网 | c114.com.cn | 5G/光通信/运营商资本开支 |
| 36氪 | 36kr.com | TMT 公司动态、产业趋势 |

### 综合（雪球/东方财富优先）

| 站点 | URL | 关注内容 |
|------|-----|---------|
| 雪球 | xueqiu.com | TMT 板块讨论、机构观点、市场情绪 |
| 东方财富 | eastmoney.com | 行业研报、板块资金流向 |
| 同花顺 | 10jqka.com.cn | TMT 板块新闻、概念股梳理 |

---

## 内容制作

- 产业链图/技术路线图 → 大模型生图，prompt 规范见 `CONTENT_STYLE.md`
- 结构化数据（竞争格局/财务对比/国产替代进度） → `text_to_image` 文字卡片
- 发帖 → `skills/submit-to-publisher/SKILL.md`
