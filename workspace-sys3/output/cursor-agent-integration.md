# Cursor CLI 接入 OpenClaw Agent 系统 — 实现文档

## 1. 背景

OpenClaw 当前用 Claude Code CLI (`claude -p`) 作为 agent 运行时。Cursor 现已推出 `cursor-agent` CLI，支持 headless 模式、MCP、Rules 系统，具备接入 OpenClaw 的基本条件。

## 2. 能力对比

| 能力 | Claude Code | Cursor CLI | 差异 |
|------|------------|------------|------|
| Headless 模式 | `claude -p "prompt"` | `cursor-agent -p "prompt"` | 对等 |
| 文件修改 | 默认允许（`--dangerously-skip-permissions`） | 需 `--force` 显式开启 | Cursor 更保守 |
| MCP 支持 | mcporter.json | `.cursor/mcp.json`（项目级/全局） | 配置格式不同 |
| Rules 系统 | CLAUDE.md | `.cursor/rules/` 目录 | Cursor 支持嵌套作用域 |
| 模型选择 | 固定 Claude | `-m sonnet-4/gpt-5` 等 | Cursor 多模型 |
| 输出格式 | 纯文本 | `--output-format text/stream-json` | Cursor 支持结构化输出 |
| 认证 | `ANTHROPIC_API_KEY` | `CURSOR_API_KEY` | 各自独立 |
| 进程退出 | 正常退出 | **已知 bug：可能挂起不退出** | 阻塞风险 |
| 工具上限 | 无硬限制 | ~40 个 MCP tools | Cursor 有上限 |

## 3. 架构设计

```
OpenClaw Gateway
├── agent: sys3 (Claude Code)     ← 现有
├── agent: sys4 (Cursor CLI)      ← 新增
│   ├── runtime: cursor-agent -p --force
│   ├── workspace: workspace-sys4/
│   ├── MCP: .cursor/mcp.json（指向同一套 MCP 服务）
│   ├── rules: .cursor/rules/（从 SOUL.md 等转换）
│   └── 消息总线: 复用 send_message/reply_message
└── bot1-10 (Claude Code)
```

Cursor agent 和 Claude Code agent 并列，共享 OpenClaw 基础设施（消息总线、MCP 服务、飞书通道），各自独立执行任务。

## 4. 实现步骤

### 4.1 安装 Cursor CLI

```bash
curl https://cursor.com/install -fsS | bash
# 验证
cursor-agent --version
```

### 4.2 创建 workspace

```bash
N=sys4
mkdir -p /home/rooot/.openclaw/workspace-${N}/{.cursor/rules,skills,memory,config}

# 基础文件
touch /home/rooot/.openclaw/workspace-${N}/{IDENTITY.md,SOUL.md,USER.md,TOOLS.md,MEMORY.md,AGENTS.md}
```

### 4.3 配置 MCP（复用现有服务）

写入 `.cursor/mcp.json`，指向 OpenClaw 已有的 MCP 服务：

```json
{
  "mcpServers": {
    "xiaohongshu": {
      "url": "http://localhost:18060/mcp/sys4"
    },
    "agent-messaging": {
      "command": "npx",
      "args": ["mcporter", "--config", "/home/rooot/.openclaw/workspace-sys4/config/mcporter.json"]
    }
  }
}
```

### 4.4 Rules 映射

OpenClaw 的 MD 文件体系需要转换为 Cursor 的 `.cursor/rules/` 格式：

| OpenClaw 文件 | Cursor Rules 映射 |
|--------------|------------------|
| SOUL.md | `.cursor/rules/soul.mdc` |
| AGENTS.md | `.cursor/rules/workflow.mdc` |
| TOOLS.md | `.cursor/rules/tools.mdc` |
| USER.md | `.cursor/rules/user.mdc` |
| EQUIPPED_SKILLS.md | `.cursor/rules/skills.mdc` |

或者更简单的方案：写一条 root rule，让 Cursor 启动时去读现有的 MD 文件：

```
# .cursor/rules/bootstrap.mdc

On session start, read and follow these files in order:
1. AGENTS.md
2. SOUL.md
3. USER.md
4. TOOLS.md
5. EQUIPPED_SKILLS.md
6. MEMORY.md
```

### 4.5 启动脚本

```bash
#!/bin/bash
# /home/rooot/.openclaw/workspace-sys4/scripts/run.sh

export CURSOR_API_KEY="sk-xxx"
WORKSPACE="/home/rooot/.openclaw/workspace-sys4"

# 带超时保护（解决挂起 bug）
timeout 300 cursor-agent -p --force \
  --output-format text \
  -m sonnet-4 \
  "$1" \
  2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 124 ]; then
  echo "[ERROR] cursor-agent timed out after 300s"
fi
```

### 4.6 注册到 OpenClaw agent 系统

在 `agents/` 下创建 sys4 配置：

```json
{
  "agent_id": "sys4",
  "name": "Cursor Coder",
  "runtime": "cursor-agent",
  "command": "/home/rooot/.openclaw/workspace-sys4/scripts/run.sh",
  "workspace": "/home/rooot/.openclaw/workspace-sys4",
  "capabilities": ["code-edit", "code-review", "refactor"],
  "model": "sonnet-4"
}
```

### 4.7 消息总线适配

Cursor agent 通过 MCP 接入消息总线，与其他 agent 通信方式不变：
- 收消息：OpenClaw gateway 调用 `run.sh "prompt"` 唤醒
- 发消息：agent 内通过 MCP 调用 `send_message` / `reply_message`

## 5. 已知风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| **headless 挂起不退出** | agent 进程僵死，阻塞调度 | `timeout` 包裹，超时强杀 |
| **首次需交互式授权** | 新目录/MCP 首次使用需手动确认 | 部署时先跑一次交互式会话完成授权 |
| **MCP 工具上限 ~40** | 工具多了会被静默丢弃 | 精简 MCP tools，每个 server 5-10 个 |
| **无原生 CLAUDE.md 支持** | Cursor 不读 CLAUDE.md | 用 `.cursor/rules/` 或 bootstrap rule 替代 |
| **退出码不可靠** | 难以判断任务成功/失败 | 用 `--output-format stream-json` 解析结果状态 |
| **Cursor 订阅费用** | CLI 使用量计入 Cursor 订阅 | 评估成本，高频任务仍用 Claude Code |

## 6. 适用场景建议

**适合用 Cursor agent 做的：**
- 多模型对比（同一任务用 GPT-5 和 Sonnet 4 各跑一次）
- Cursor 独有能力（如 Cursor 特有的代码索引、跨文件理解）
- 负载分担（Claude Code 繁忙时分流）

**不适合的：**
- 高频自动化任务（挂起 bug 风险）
- 需要长时间运行的任务（超时问题）
- 与 OpenClaw 深度集成的运维操作（Claude Code 更原生）

## 7. 分阶段实施

### Phase 1：验证可行性（1-2 天）
- 安装 Cursor CLI
- 手动测试 `cursor-agent -p --force "简单任务"`
- 验证 MCP 连接、Rules 加载、进程退出

### Phase 2：最小集成（2-3 天）
- 创建 workspace-sys4
- 配置 MCP 和 Rules
- 写启动脚本（含 timeout 保护）
- 手动触发任务验证端到端

### Phase 3：接入调度（3-5 天）
- 注册到 agent 系统
- 消息总线对接
- mag1 能分发任务给 sys4
- 监控和告警

### Phase 4：生产稳定化
- 挂起检测和自动恢复
- 成本监控
- 与 sys3 (Claude Code) 的任务分配策略

---

*参考资料：*
- [Cursor Headless CLI Docs](https://cursor.com/docs/cli/headless)
- [Cursor CLI Overview](https://cursor.com/docs/cli/overview)
- [Cursor CLI MCP](https://cursor.com/docs/cli/mcp)
- [Cursor Agent CLI Blog](https://cursor.com/blog/cli)
- [Cursor CLI Parameters](https://cursor.com/docs/cli/reference/parameters)
