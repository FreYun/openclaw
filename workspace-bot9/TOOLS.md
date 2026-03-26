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



# TOOLS.md — bot9 专属工具配置

> 首先 Read `../workspace/TOOLS_COMMON.md` 获取统一工具规范。

---

## Bot 基础信息

- **account_id**: `bot9`
- **名字**: bot9
- **主模型**: glm/glm-5-turbo（fallback: bailian/qwen3.5-plus → kimi-coding/k2p5）

---

## 浏览器

bot9 拥有独立的 Chrome 浏览器 profile，用于访问网页、打开新闻链接等。

**调用参数：**

```
browser_navigate(url: "https://...", profile: "bot9")
browser_snapshot(profile: "bot9")
browser_close(profile: "bot9")
```

| 配置项 | 值 |
|--------|-----|
| profile | `bot9` |
| CDP 端口 | `18809` |
| 启动失败时 | `bash /home/rooot/.openclaw/scripts/ensure-browser.sh bot9` |

**⚠️ 关键规则：**
- **必须传 `profile: "bot9"`**，漏传会超时
- 用完必须 `browser_close(profile: "bot9")` 关闭标签页，防止 CPU 飙升
- `ref` 只对当前快照有效，页面变化后需重新 `browser_snapshot`
- 不装 Chrome 扩展；超时不要反复重试

---

## Tushare Pro API

用于获取**当日实时**大盘指数行情（research-mcp 的指数数据有 T+1 延迟）。

- **Token**: `ed396239156fa590b3730414be7984b029e021c3531e419f6bc170d4`
- **API 地址**: `https://api.tushare.pro`（HTTP POST，JSON 格式）
- **详细用法**：见 `skills/daily-market-recap/每日复盘-写作指南.md` 中"行情数据获取"章节

---

## MCP 服务

通过 mcporter 调用，格式：`npx mcporter call "服务名.工具名(参数)"`

| 服务 | 端口 | 用途 |
|------|------|------|
| xiaohongshu-mcp | 18069 | 小红书笔记管理、互动 |
| compliance-mcp | 18090 | 合规审查 |
| image-gen-mcp | 18085 | AI 生图 |

### 小红书 MCP

```
npx mcporter call "xiaohongshu-mcp.tool_name(...)"
```

- **不传 account_id**（身份由端口决定），唯一例外：`publish_content`（可选）
- 超时先查登录状态；离线报研究部
- 发布走 `submit-to-publisher` skill

### 合规 MCP

```
npx mcporter call "compliance-mcp.check_content(content: '...', platform: 'wechat')"
```

### 生图 MCP

```
npx mcporter call 'image-gen-mcp.generate_image(style: "扁平插画风", content: "描述")'
```

模型可选 `banana`（默认）或 `banana2`，图片保存到 `/tmp/image-gen/`。

---

## 金融数据：Skill Gateway

bot9 角色：**content_creator**（基础行情查询）

```
npx mcporter call "research-mcp.tool_name(...)"
```

可用范围：基础行情报价。高级数据（Tushare 全量、研报等）需通过消息总线请求 bot7/bot8。

---

## 消息总线

```
send_message(to: "target_agent", content: "...", trace: [{
  agent: "bot9", session_id: "当前session_id",
  reply_channel: "feishu", reply_to: "ou_xxx", reply_account: "bot9"
}])
```

- 每条消息必须带 `trace`
- 一问一答，不拆分多条
- 收到 `[MSG:xxx]` → 处理 → `reply_message(message_id: "xxx", content: "结果")`
