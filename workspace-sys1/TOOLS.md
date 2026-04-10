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






# TOOLS.md — Publisher Tool Config


## MCP 路由（单进程多租户）

xiaohongshu-mcp 单进程监听 `:18060`，通过 URL path 区分 bot。印务局的 mcporter 配置了所有 bot 的 MCP 端点。

**服务名 = `xhs-{account_id}`**，例如 bot7 的帖子用 `xhs-bot7`。mcporter.json 里每个 bot 对应一个服务名，路由到 `/mcp/botN`。**绝对不要用 `xiaohongshu-mcp` 作为服务名** — 它不存在于 mcporter.json 中，会导致发错账号。

## Usage

```bash
# Publish（服务名必须是 xhs-{account_id}）
npx mcporter call "xhs-bot7.publish_content(title: '...', ...)"
# Login check（同样用 xhs-{account_id}）
npx mcporter call "xhs-bot7.check_login_status()"
# Compliance
npx mcporter call "compliance-mcp.review_content(title: '...', content: '...', tags: '...')"
# Health check
curl -s --connect-timeout 5 http://localhost:18060/health
```

## MCP Restart — ⛔ 禁止自行执行

> **印务局禁止重启 MCP 服务。** kill MCP 会中断所有 bot 正在执行的浏览器操作（发布、登录等），
> 导致数据不一致和 Chrome profile 损坏。遇到 MCP 异常时：
> 1. 记录错误日志
> 2. 上报 mag1（send_message）
> 3. 等待管理员处理
> 4. **绝对不要执行 `lsof -ti:18060 | xargs kill` 或任何 kill 命令**

## Publish Queue

```
/home/rooot/.openclaw/workspace-sys1/publish-queue/
├── pending/      ← folder format (post.md + media) or .md file (legacy)
├── publishing/   ← mv lock
└── published/    ← archive (success only; failures deleted + notified)
```

Submit script: `skills/xhs-op/submit-to-publisher.sh`

## Feishu Alert

```
message(action="send", channel="feishu", target="oc_e59188e3ecdb04acd9b33843870a2249", message="...")
```
