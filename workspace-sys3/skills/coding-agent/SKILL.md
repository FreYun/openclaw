# Claude Code 研发 Skill

> 我不写代码。我把需求传达给 Claude Code，它写完我验收。

## 三步流程

```
收到需求 → ① 传达需求 → ② 调用 Claude Code → ③ 验收
```

### ① 传达需求

把研究部的需求传给 Claude Code，同时**附上项目基本信息**帮它快速进入状态。

**传需求时附带的项目信息：**
- 项目路径和语言（如 `/home/rooot/MCP/xiaohongshu-mcp/`，Go）
- 构建/测试命令（如 `go build .`、`npm run build`）
- 需求涉及的大致模块或文件区域（如"publish 相关的代码"）
- 项目特殊约定（如"用 Rod 做浏览器自动化"、"单进程多租户架构"）

自己要熟悉项目结构才能提供这些信息，但**不需要把这些写成结构化模板**——用自然语言告诉 Claude Code 就行。

**不要做的：**
- 不要把需求重写为 Goal/Files/Context/Constraint 模板
- 不要替 Claude Code 做详细代码分析（它自己会探索）
- 不要预设实现方案（除非研究部指定了）
- 需求不清楚时先问研究部，不要自己猜

### ② 调用 Claude Code

通过 tmux 下发需求，详见 [tmux-ops.md](tmux-ops.md)。

核心就是：
```bash
SOCKET="/tmp/coding-agents.sock"
tmux -S "$SOCKET" send-keys -t session-name \
  "unset CLAUDECODE && claude -p '需求内容' --output-format text --dangerously-skip-permissions" Enter
```

### ③ 验收

Claude Code 跑完后检查结果，详见 [qa-checklist.md](qa-checklist.md)。

核心就是：
- 看 diff，确认改动和需求一致
- 跑 build/test 确认没挂
- Pass → 合并；Fail → 修正需求重试一次；再 Fail → 报告研究部

---

## 铁律

1. **所有改动在沙盒中** — `git worktree add` 创建，QA Pass 后合并
2. **两轮不过就停** — 不要磨，报告研究部
3. **Production 改动先报批**
4. **只读命令可以直接跑** — git status/diff/log、tree、ls 等

## 项目速查

| 项目 | 路径 | 语言 |
|------|------|------|
| XHS MCP | `/home/rooot/MCP/xiaohongshu-mcp/` | Go |
| Profile Demo | `/home/rooot/MCP/profile-demo/` | Go |
| OpenClaw 主仓 | `/home/rooot/.openclaw/` | TS, Shell, MD |
| OpenClaw CLI | `/home/rooot/.openclaw/openclaw/` | TS |

## 安全

- Never `pkill -9 -f "chrome.*xhs-profiles"`
- Never `pkill -f "xhs-mcp"`
- 精确杀进程：`lsof -ti:端口号 | xargs kill`
- Chrome profiles 只读
