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

bot_main: 18060 | bot1-10: 18061-18070

## Chrome Profiles

`/home/rooot/.xhs-profiles/botN/` — read-only, never delete

## Agent IDs

| ID | Role |
|----|------|
| bot_main | Dispatcher |
| coder | R&D (self) |
| mcp_publisher | MCP ops |
| security | Security audit |
| skills | Skill management |
| image-generator | Image gen |
| bot1-10 | Content bots |