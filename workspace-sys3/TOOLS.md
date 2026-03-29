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






# TOOLS

> First read `../workspace/TOOLS_COMMON.md` for shared rules.

## Identity

- **agent_id**: `coder`
- **role**: R&D

## Tools

- **claude**: `/home/rooot/.local/bin/claude` — requires `unset CLAUDECODE` + `--dangerously-skip-permissions`
- **tmux**: `/usr/bin/tmux` — manage background coding sessions

Skill: `skills/coding-agent/SKILL.md`

## Repositories

| Project | Path | Lang |
|---------|------|------|
| OpenClaw | `/home/rooot/.openclaw/` | TS, Shell, MD |
| XHS MCP | `/home/rooot/MCP/xiaohongshu-mcp/` | Go |
| XHS Profile Demo | `/home/rooot/MCP/profile-demo/` | Go |
| OpenClaw CLI | `/home/rooot/.openclaw/openclaw/` | TS |

## MCP Ports

mag1: 18060 | bot1-10: 18061-18070

## Chrome Profiles

`/home/rooot/.xhs-profiles/botN/` — read-only, never delete

## Agent IDs

| ID | Role |
|----|------|
| mag1 | Dispatcher |
| coder | R&D (self) |
| sys1 | MCP ops |
| security | Security audit |
| skills | Skill management |
| image-generator | Image gen |
| bot1-10 | Content bots |