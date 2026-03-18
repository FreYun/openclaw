# TOOLS.md - Wei Zhongxian Tool Config

## Bot Config

- **account_id**: `bot_main` (admin agent, does not publish to XHS directly)

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
| mcp_publisher | Publisher (印务局) | Active |
| skills | Skills Dept | Active |
| image-generator | Image Gen (制图部) | Active |
| coder | 工部 | Active |

## XHS Operations (Delegate to Publisher)

**Wei Zhongxian never operates XHS MCP directly.** For login/publish/MCP issues, message the Publisher:

```
send_message(to: "mcp_publisher", content: "Check botN login status", trace: [...])
```

## Gateway Restart

```bash
nohup bash /home/rooot/.openclaw/scripts/restart-gateway.sh > /dev/null 2>&1 &
```

Current session will disconnect after execution. New gateway auto-revives this agent.

## Dev Reference

See `skills/claude-dev-reference/SKILL.md` (a.k.a. CLAUDE.md).
