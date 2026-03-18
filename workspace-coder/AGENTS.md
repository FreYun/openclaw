# AGENTS — Workflow

## Session Startup

1. Read `SOUL.md`
2. Read `USER.md`
3. Read `TOOLS.md`
4. Read `memory/YYYY-MM-DD.md` (today + yesterday)
5. Main session: also read `MEMORY.md`

## Workflow

### 1. Receive request
From: Admin / bot_main / other agents' bug reports

### 2. Analyze & rewrite prompt
- Understand intent, confirm with Admin if ambiguous
- Gather context: read related code (via Claude Code), check project structure
- Break large tasks into small, independently verifiable prompts

### 3. Send to Claude Code

```bash
SOCKET="/tmp/coding-agents.sock"
tmux -S "$SOCKET" new-session -d -s task-name -c /path/to/project
tmux -S "$SOCKET" send-keys -t task-name \
  "unset CLAUDECODE && claude -p 'prompt' --output-format text --dangerously-skip-permissions" Enter
tmux -S "$SOCKET" capture-pane -p -t task-name -S -30
```

### 4. QA output
Check generated/modified files via capture-pane. Verify against acceptance criteria.

### 5. Deliver or retry
- **Pass** — report to Admin
- **Round 1 fail** — fix prompt, retry
- **Round 2 fail** — stop, report to Admin with details

## Memory

### Diary `memory/YYYY-MM-DD.md`
- Requests received and results
- Key prompts sent and Claude Code performance
- Prompt optimization learnings

Newest entries at top.

### Long-term `MEMORY.md`
Distilled from diary: project architecture, effective prompt patterns, Claude Code quirks, recurring quality issues.

### Topic notes `memory/xxx.md`
- `prompt-patterns.md` — proven prompt templates
- `claude-code-quirks.md` — known Claude Code behaviors
- `project-context.md` — project architecture notes

## Security

- Kill processes by PID or `lsof -ti:port | xargs kill`, never wildcard pkill
- Chrome profiles: read-only
- Production prompts: Admin approval first
- No API keys in diary