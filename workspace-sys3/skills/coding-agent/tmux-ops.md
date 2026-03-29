# tmux 操作手册

## 创建沙盒

```bash
cd /path/to/project
git worktree add -b sandbox/任务简述 /tmp/sandbox-任务简述 main
```

## 启动 Claude Code

```bash
SOCKET="/tmp/coding-agents.sock"

# 创建 session，workdir 指向沙盒
tmux -S "$SOCKET" new-session -d -s task-name -c /tmp/sandbox-任务简述

# 下发需求
tmux -S "$SOCKET" send-keys -t task-name \
  "unset CLAUDECODE && claude -p '需求内容' --output-format text --dangerously-skip-permissions" Enter
```

## 监控

```bash
# 看最新输出
tmux -S "$SOCKET" capture-pane -p -t task-name -S -30

# 检查是否跑完（看到 shell prompt 说明完成）
tmux -S "$SOCKET" capture-pane -p -t task-name -S -3

# Claude Code 问了问题就回答
tmux -S "$SOCKET" send-keys -t task-name "y" Enter
```

## 合并 & 清理

```bash
# QA Pass → 合并
cd /path/to/project
git merge sandbox/任务简述

# 清理
tmux -S "$SOCKET" kill-session -t task-name
git worktree remove /tmp/sandbox-任务简述
git branch -d sandbox/任务简述
```

## 注意事项

- **tmux workdir 指向沙盒**，不是主项目
- 必须 `unset CLAUDECODE`，否则嵌套检测会拒绝启动
- 必须 `--dangerously-skip-permissions`
- 不要在 openclaw workspace 目录启动（会读到 SOUL.md 等配置）
- 跑超 5 分钟先 `capture-pane` 看状态，别急着杀
