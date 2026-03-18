# Plan: 独立 Message Session 用于 Agent 间通讯

## 问题

当前 `send_message`/`forward_message`/`ask_agent` 唤醒目标 agent 时，使用 `openclaw agent --agent <target> --message "..."` 命令，没有指定 session key，导致消息默认落入 `agent:<target>:main` session，与 heartbeat、本地调试共用同一个 session。

## 方案

为 agent 间通讯创建一个专用的 session key: `agent:<target>:message`。需要修改 4 个文件：

### 1. `openclaw/src/cli/program/register.agent.ts` — 添加 `--session-key` CLI 选项

```
.option("--session-key <key>", "Use an explicit session key (e.g. agent:bot7:message)")
```

### 2. `openclaw/src/commands/agent-via-gateway.ts` — 传递 sessionKey

- `AgentCliOpts` 增加 `sessionKey?: string`
- `agentViaGatewayCommand` 中：如果 `opts.sessionKey` 存在，优先使用它而不是从 agentId 推导

### 3. `openclaw/extensions/agent-messaging/src/dispatch.ts` — 使用 message session key

当 `route.kind === "wake_agent"` 且没有 `route.session_id` 时（即新的 send_message/forward_message/ask_agent 场景），传递 `--session-key agent:<target>:message`：

```typescript
if (route.session_id) {
  argv.push("--session-id", route.session_id);
} else {
  argv.push("--session-key", `agent:${route.agent}:message`);
}
```

### 4. `dashboard/server.js` — 识别 message session 类型

在 session source 解析中增加对 `:message` 的识别，让 dashboard 显示 `message` 标签。

## 效果

- 每个 agent 会有一个独立的 `agent:<agentId>:message` session，所有 agent 间通讯都在这里
- main session 不再被 agent 消息污染，保持干净
- reply_message 回调仍然走 trace 中记录的 session_id（即原始 session），不受影响
- Dashboard 上可以看到 "message" 类型的独立 session
