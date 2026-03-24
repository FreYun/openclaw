# Claude Code 研发 Skill

> 我不写代码。我写 prompt 让 Claude Code 写好代码。所有改动在沙盒中进行。

## 子文档索引

| 文档 | 何时读取 | 用途 |
|------|---------|------|
| [context-scan.md](context-scan.md) | **每次收到需求后第一步** | 了解项目状态再动手 |
| [prompt-craft.md](prompt-craft.md) | **写 prompt 前必读** | Scope Lock、模板、约束 |
| [qa-checklist.md](qa-checklist.md) | **Claude Code 跑完后** | 验收改动是否合格 |
| [tmux-ops.md](tmux-ops.md) | **需要操作 tmux 时** | 沙盒创建、会话管理、并行任务 |

---

## 铁律

1. **所有改动在沙盒中进行** — 先 `git worktree add` 创建沙盒，QA Pass 后合并回主分支
2. **只通过 tmux + Claude Code 操作** — 不直接改代码、跑 build/test/lint、做 git commit/push
3. **只读命令可以直接跑** — git status/diff/log、tree、ls、head、cat（仅用于了解项目状态）
4. **每个 prompt 必须有 Don't 条款** — 不说"不要做什么"，Claude Code 就会自由发挥
5. **两轮不过就停** — Round 1 fail 修 prompt 重试，Round 2 fail 停下报告 Admin
6. **Production 改动先报批** — 影响线上的 prompt 必须 Admin 确认后再发

---

## 工作流程（7 步）

```
收到需求 → ① Context Scan → ② Scope Lock → ③ Create Sandbox → ④ Write & Send Prompt → ⑤ QA → ⑥ Merge/PR → ⑦ Cleanup
```

### ① Context Scan
Read [context-scan.md](context-scan.md) — 跑 git status/diff/tree 或 `project-tree.py`，输出 Context Summary。

### ② Scope Lock
Read [prompt-craft.md](prompt-craft.md) — 用一句话锁定范围，需求明确可跳过 Admin 确认。

### ③ Create Sandbox
```bash
cd /path/to/project
git worktree add -b sandbox/任务简述 /tmp/sandbox-任务简述 main
```
Explore 类（纯读不改代码）可跳过沙盒。

### ④ Write & Send Prompt
Read [prompt-craft.md](prompt-craft.md) — 按模板写 prompt（Goal + Files + Context + Constraint + Don't + Acceptance）。
Read [tmux-ops.md](tmux-ops.md) — tmux session 的 workdir 指向沙盒目录。

### ⑤ QA
Read [qa-checklist.md](qa-checklist.md) — 在沙盒中 diff 回顾 + 完整性检查 + 正确性检查。

### ⑥ Merge / PR
- QA Pass → 合并沙盒分支回主分支，或创建 PR（重要改动推荐 PR）
- Round 1 fail → 在同一沙盒中修 prompt 重试
- Round 2 fail → 停止，清理沙盒，报告 Admin

### ⑦ Cleanup
```bash
git worktree remove /tmp/sandbox-xxx
git branch -d sandbox/xxx
```

---

## 任务分类

| 类型 | 特征 | 沙盒 | Scope 控制 |
|------|------|------|-----------|
| **Fix** | 有明确症状和目标文件 | 必须 | Strict: prompt 写死文件路径 |
| **Feature** | 有明确需求描述 | 必须 | Medium: 列出文件，Admin 确认 |
| **Explore** | 不确定怎么做 | 跳过 | 只读分析，不改任何文件 |

---

## 项目速查

| 项目 | 路径 | 语言 |
|------|------|------|
| XHS MCP | `/home/rooot/MCP/xiaohongshu-mcp/` | Go |
| Profile Demo | `/home/rooot/MCP/profile-demo/` | Go |
| OpenClaw 主仓 | `/home/rooot/.openclaw/` | TS, Shell, MD |
| OpenClaw CLI | `/home/rooot/.openclaw/openclaw/` | TS |

## 安全

- Never `pkill -9 -f "chrome.*xhs-profiles"` — 会杀掉所有 bot Chrome
- Never `pkill -f "xhs-mcp"` — 会杀掉所有 MCP
- 精确杀进程：`lsof -ti:端口号 | xargs kill`
- Chrome profiles (`/home/rooot/.xhs-profiles/botN/`) — 只读
- 不在日记里记 API key / cookie / password
