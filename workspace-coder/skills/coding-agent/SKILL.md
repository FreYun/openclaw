# Coding Agent (后台编程智能体)

通过 tmux 后台运行 Claude Code，实现并行编码任务。

## 核心模式：tmux + workdir 隔离

```bash
SOCKET="/tmp/coding-agents.sock"

# 创建隔离 session（必须用目标项目目录，不要用 openclaw workspace）
tmux -S "$SOCKET" new-session -d -s task-name -c ~/project

# 下发 prompt（必须 unset CLAUDECODE 绕过嵌套检测）
tmux -S "$SOCKET" send-keys -t task-name \
  "unset CLAUDECODE && claude -p 'prompt内容' --output-format text --dangerously-skip-permissions" Enter

# 监控进度（最后30行输出）
tmux -S "$SOCKET" capture-pane -p -t task-name -S -30

# 检查是否完成（看到 shell prompt 说明跑完了）
tmux -S "$SOCKET" capture-pane -p -t task-name -S -3

# 发送输入（如果 agent 问了问题）
tmux -S "$SOCKET" send-keys -t task-name "y" Enter

# 杀掉会话
tmux -S "$SOCKET" kill-session -t task-name

# 列出所有会话
tmux -S "$SOCKET" list-sessions
```

**为什么用 workdir 隔离？** Agent 只看到目标目录的文件，不会误读 workspace 的 SOUL.md 等配置文件。

---

## 关键注意事项

- **必须 `unset CLAUDECODE`** — 否则 Claude Code 检测到嵌套会拒绝启动
- **必须 `--dangerously-skip-permissions`** — 否则会卡在权限审批上
- **不要在 openclaw workspace 目录里启动** — 会读到配置文件产生混乱，用目标项目目录或 /tmp

---

## 并行修复多个 Issue（git worktree + tmux）

```bash
# 1. 为每个 issue 创建 worktree（隔离分支）
git worktree add -b fix/issue-78 /tmp/issue-78 main
git worktree add -b fix/issue-99 /tmp/issue-99 main

# 2. 每个 worktree 启动一个 tmux session
SOCKET="/tmp/issue-fixes.sock"
tmux -S "$SOCKET" new-session -d -s fix-78 -c /tmp/issue-78
tmux -S "$SOCKET" new-session -d -s fix-99 -c /tmp/issue-99

# 3. 下发 prompt
tmux -S "$SOCKET" send-keys -t fix-78 \
  "unset CLAUDECODE && claude -p 'Fix issue #78: <description>. Run tests after fix.' --output-format text --dangerously-skip-permissions" Enter
tmux -S "$SOCKET" send-keys -t fix-99 \
  "unset CLAUDECODE && claude -p 'Fix issue #99: <description>. Run tests after fix.' --output-format text --dangerously-skip-permissions" Enter

# 4. 监控
tmux -S "$SOCKET" capture-pane -p -t fix-78 -S -30
tmux -S "$SOCKET" capture-pane -p -t fix-99 -S -30

# 5. 完成后创建 PR
cd /tmp/issue-78 && git push -u origin fix/issue-78
gh pr create --repo user/repo --head fix/issue-78 --title "fix: ..." --body "..."

# 6. 清理
tmux -S "$SOCKET" kill-server
git worktree remove /tmp/issue-78
git worktree remove /tmp/issue-99
```

---

## 规则

1. **只通过 tmux + Claude Code 操作** — 不直接读代码、改代码、跑命令
2. **耐心等待** — 不要因为"慢"就杀进程
3. **用 capture-pane 监控** — 不打断 agent 执行
4. **并行没问题** — 可以同时跑多个 Claude Code session
5. **不要在 openclaw workspace 目录里启动 agent** — 用目标项目目录或 /tmp