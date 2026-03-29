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

生图用 `image-gen-mcp.generate_image(style, content)`。模型可选 `banana`（默认）或 `banana2`。图片保存到 `/tmp/image-gen/` 下。

```
npx mcporter call 'image-gen-mcp.generate_image(style: "扁平插画风", content: "一只猫在看股票K线图")'
```

---

## Tool Priority

1. **memory** → check history first, update incrementally
2. **research-mcp** → financial data
3. **browser** → Xueqiu, EastMoney research reports, etc.
4. **MCP search** → supplementary search, overseas data
5. **xiaohongshu-mcp** → note management, interactions
6. **message bus** → inter-agent communication
<!-- TOOLS_COMMON:END -->






# TOOLS.md - bot5（宣妈慢慢变富）工具配置


---

## Bot 专属配置

- **account_id**: `bot5`
- **小红书 MCP 端口**: 18065（已配置在 mcporter.json，不需要手动指定）

## 浏览器（全局规则）

**所有浏览器操作必须使用 `profile="bot5"`**，无论是发布、研究还是截图，调用 browser 工具时一律带上此参数。

## 封面生图

- **生图工具：** `image-gen-mcp.generate_image(style, content)`，style 固定不变从模板复制，content 每次按场景填写
- **每次生图前必须先向研究部确认：** 卡片文字、情绪场景、背景色
- **⚠️ 铁律：每次需要生图时，必须先 `Read skills/xuanma-cover/SKILL.md`，从文件中复制 STYLE 模板和场景表情库。禁止凭记忆自己写 prompt，必须以文件内容为准。**

## 内容规范

- **标题限制：** 图文/视频标题最多 20 字；长文无硬性限制
- **封面与内容形式：** 见本 workspace 的 `CONTENT_STYLE.md`

## 行情数据（Research Gateway）

你的 mcporter.json 已配置 `research-mcp`（端口 18080），权限由 dashboard 管理，可直接调用以下工具查行情数据：

### 你有权限的工具

| 工具 | 说明 | 常用参数 |
|------|------|---------|
| `commodity_quote` | **黄金/白银等商品行情** | `symbol="AU9999"` 或 `"黄金9999"`，`days=30` |
| `market_snapshot` | A股/港股/美股大盘快照 | 无必填参数 |
| `fund_analysis` | 基金综合分析 | `fund_code="000001"` |
| `fund_screen` | 基金筛选 | 按条件筛 |
| `macro_overview` | 宏观经济数据（GDP/CPI/M2等） | `category="cpi,ppi,m2"` |
| `search_news` | 财经新闻搜索 | `keyword="黄金"` |
| `search_report` | 研报搜索 | `keyword="黄金"` |
| `index_valuation` | 指数估值 | 指数代码 |

### 查黄金行情（最常用）

调用 research-mcp 的 `commodity_quote` 工具：
- **黄金**：`symbol="AU9999"` 或 `symbol="黄金9999"`
- **白银**：`symbol="AG9999"` 或 `symbol="白银9999"`
- **多个商品**：逗号分隔 `symbol="AU9999,AG9999"`
- **历史天数**：`days=30`（默认 30 天）

### 写稿前查行情的推荐流程

1. `commodity_quote`(symbol="AU9999") — 拿最新金价和近期走势
2. `market_snapshot` — 看大盘环境
3. `search_news`(keyword="黄金") — 搜相关新闻做选题
4. 结合行情数据和新闻写稿

### 需要更多工具？

如需 `stock_research`、`bond_monitor` 等当前角色没有的工具，向技能部发权限申请（见 `skills/research-mcp/SKILL.md`）。

---

## 本 workspace 路径

- 内容规范：`CONTENT_STYLE.md`
- 人设与研究部规范：`SOUL.md`、`USER.md`
- 工作流程：`AGENTS.md`
