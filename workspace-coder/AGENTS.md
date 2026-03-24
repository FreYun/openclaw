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

### 2. Context Scan
Read `skills/coding-agent/context-scan.md`

直接执行只读命令了解项目状态：
```bash
tree -L 2 /path/to/project
cd /path/to/project && git status && git diff --stat && git log --oneline -10
```

输出 Context Summary（会嵌入后续 prompt）。

### 3. Scope Lock
Read `skills/coding-agent/prompt-craft.md`

判断任务类型（Fix / Feature / Explore），输出 Scope 一句话，需求明确可跳过 Admin 确认。

### 4. Create Sandbox
**所有代码改动必须在沙盒中进行，不直接改主分支。**

```bash
cd /path/to/project
git worktree add -b sandbox/任务简述 /tmp/sandbox-任务简述 main
```

Explore 类（纯读不改代码）可跳过沙盒。

### 5. Write & send prompt
按 prompt-craft.md 的模板写 prompt（Goal + Files + Context + Constraint + Don't + Acceptance）。
通过 tmux 发送到**沙盒目录**，详见 `skills/coding-agent/tmux-ops.md`。

### 6. QA output
Read `skills/coding-agent/qa-checklist.md`

在沙盒中执行三步验收：Diff 回顾 → 完整性检查 → 正确性检查。

### 7. Deliver or retry
- **Pass** → 合并沙盒分支回主分支（或创建 PR），清理 worktree，报告 Admin
- **Round 1 fail** → 在同一沙盒中修 prompt 重试（从 step 5）
- **Round 2 fail** → 清理沙盒，报告 Admin

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
