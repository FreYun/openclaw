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

## Tool Priority

1. **memory** → check history first, update incrementally
2. **research-mcp** → financial data
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
| bot2 | 狗哥说财 | Active |
| bot3 | meme爱理财 | — |
| bot4 | 研报搬运工阿泽 | Active |
| bot5 | 宣妈慢慢变富 | Active |
| bot6 | 爱理财的James | — |
| bot7 | 老K投资笔记 | Active |
| bot8 | bot8 | Active |
| bot9 | 公众号运营强哥 | — |
| bot10 | 测试君 | — |
| bot11 | 小奶龙 | — |
| bot12 | 小天爱黄金 | — |
| bot13 | 美股学长 Alex | — |
| bot14 | 捂紧小荷包 | — |
| bot15 | 搞钱小财迷 | — |
| bot16 | 小贝宏观笔记 | — |
| bot17 | 团子养基 | — |
| bot18 | 抄作业课代表 | — |
| sys1 | 印务局 | Active |
| sys2 | 技能部 | Active |
| sys3 | 工部 (Coder) | Active |

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
