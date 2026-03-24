# 🖥️ tmux 操作

> 所有代码改动在 git worktree 沙盒中，通过 tmux + Claude Code 执行。

---

## 标准流程：创建沙盒 → 下发 prompt → QA → 合并/清理

### Step 1: 创建沙盒（git worktree）

```bash
cd /path/to/project

# 创建 worktree 沙盒（分支名 = 任务描述）
git worktree add -b sandbox/fix-tag-input /tmp/sandbox-fix-tag-input main

# 确认沙盒就绪
ls /tmp/sandbox-fix-tag-input/
```

**命名规范：** `sandbox/<任务简述>`，路径统一放 `/tmp/sandbox-*`

### Step 2: 在沙盒中启动 tmux session

```bash
SOCKET="/tmp/coding-agents.sock"

# session 的 workdir 指向沙盒，不是主项目
tmux -S "$SOCKET" new-session -d -s task-name -c /tmp/sandbox-fix-tag-input

# 下发 prompt（必须 unset CLAUDECODE + --dangerously-skip-permissions）
tmux -S "$SOCKET" send-keys -t task-name \
  "unset CLAUDECODE && claude -p 'prompt' --output-format text --dangerously-skip-permissions" Enter
```

### Step 3: 监控

```bash
# 最后 30 行输出
tmux -S "$SOCKET" capture-pane -p -t task-name -S -30

# 检查是否完成（看到 shell prompt 说明跑完了）
tmux -S "$SOCKET" capture-pane -p -t task-name -S -3

# 如果 Claude Code 问了问题
tmux -S "$SOCKET" send-keys -t task-name "y" Enter
```

### Step 4: QA（在沙盒中检查）

```bash
cd /tmp/sandbox-fix-tag-input
git diff --stat    # 改了哪些文件
git diff           # 具体改动
```

详见 `docs/qa-checklist.md`

### Step 5a: QA Pass → 合并回主分支

```bash
# 回到主项目
cd /path/to/project

# 合并沙盒分支
git merge sandbox/fix-tag-input

# 清理沙盒
tmux -S "$SOCKET" kill-session -t task-name
git worktree remove /tmp/sandbox-fix-tag-input
git branch -d sandbox/fix-tag-input
```

**或创建 PR（推荐用于重要改动）：**

```bash
cd /tmp/sandbox-fix-tag-input
git push -u origin sandbox/fix-tag-input
gh pr create --title "fix: tag input" --body "..."

# 清理 worktree（保留远程分支）
cd /path/to/project
tmux -S "$SOCKET" kill-session -t task-name
git worktree remove /tmp/sandbox-fix-tag-input
```

### Step 5b: QA Fail → 重试或放弃

```bash
# Round 1 fail: 在同一个沙盒中重试
tmux -S "$SOCKET" send-keys -t task-name \
  "unset CLAUDECODE && claude -p '修改后的 prompt' --output-format text --dangerously-skip-permissions" Enter

# Round 2 fail: 放弃，清理沙盒
tmux -S "$SOCKET" kill-session -t task-name
git worktree remove --force /tmp/sandbox-fix-tag-input
git branch -D sandbox/fix-tag-input
```

---

## ⚠️ 关键注意事项

| 规则 | 原因 |
|------|------|
| **tmux workdir 指向沙盒，不是主项目** | 防止 Claude Code 改到主分支 |
| 必须 `unset CLAUDECODE` | 否则 Claude Code 检测嵌套会拒绝启动 |
| 必须 `--dangerously-skip-permissions` | 否则卡在权限审批 |
| 不要在 openclaw workspace 目录启动 | Claude Code 会读到 SOUL.md 等配置文件 |
| 耐心等待 | 不要因为"慢"就杀进程 |

---

## 并行任务

多个独立任务可以并行跑，每个任务一个沙盒：

```bash
cd /path/to/project
git worktree add -b sandbox/fix-78 /tmp/sandbox-fix-78 main
git worktree add -b sandbox/fix-99 /tmp/sandbox-fix-99 main

SOCKET="/tmp/coding-agents.sock"
tmux -S "$SOCKET" new-session -d -s fix-78 -c /tmp/sandbox-fix-78
tmux -S "$SOCKET" new-session -d -s fix-99 -c /tmp/sandbox-fix-99

# 分别下发 prompt...
# 分别 QA...
# 分别合并或创建 PR...
# 分别清理...
```

---

## 长任务处理

如果 Claude Code 跑了超过 5 分钟：

1. `capture-pane -S -30` 看最新输出 — 确认还在跑（不是卡住了）
2. 如果卡住（同一行输出持续不变） → 发 `Ctrl+C`：`tmux -S "$SOCKET" send-keys -t task-name C-c`
3. 如果正常运行但慢 → 等待，不要杀
4. 如果需要人工决策 → 看清问题后 send-keys 回答

---

## 沙盒清理

定期检查残留沙盒：

```bash
# 列出所有 worktree
cd /path/to/project && git worktree list

# 清理不再需要的
git worktree remove /tmp/sandbox-xxx
git branch -d sandbox/xxx
```
