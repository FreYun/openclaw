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



# TOOLS.md - Wei Zhongxian Tool Config

## Bot Config

- **account_id**: `mag1` (admin agent, does not publish to XHS directly)

## Inter-Agent Communication (Message Bus)

Only channel: `send_message` / `reply_message` / `forward_message`

- **Forbidden:** `openclaw agent --message`, `message()` legacy tool, Feishu group messaging
- Every message must carry trace (provenance chain)
- On receiving `[MSG:xxx]` → must `reply_message` when done

### Agent ID Reference

| agent_id | Name | Status |
|----------|------|--------|
| bot1 | 来财妹妹 | Active |
| bot2 | bot2 | Active (DM) |
| bot4 | 研报搬运工阿泽 | Active |
| bot5 | 宣妈慢慢变富 | Active |
| bot7 | 老K投资笔记 | Active |
| bot8 | 老k | Active |
| bot3/6/9/10 | — | No active session |
| security | Security Dept | Active |
| sys1 | Publisher (印务局) | Active |
| skills | Skills Dept | Active |
| image-generator | Image Gen (制图部) | Active |
| coder | 工部 | Active |

## XHS Operations (Delegate to Publisher)

**Wei Zhongxian never operates XHS MCP directly.** For login/publish/MCP issues, message the Publisher:

```
send_message(to: "sys1", content: "Check botN login status", trace: [...])
```

## Gateway Restart

```bash
nohup bash /home/rooot/.openclaw/scripts/restart-gateway.sh > /dev/null 2>&1 &
```

Current session will disconnect after execution. New gateway auto-revives this agent.

## Dev Reference

See `skills/claude-dev-reference/SKILL.md` (a.k.a. CLAUDE.md).
