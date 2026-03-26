# 已装备技能

> 本文件由装备系统自动生成，请勿手动编辑。
> 更新时间：2026-03-26 10:00:18

## 👔 衣服

### 💻 Claude Code 研发（coding-agent）

通过 tmux 驱动 Claude Code 完成开发任务、Prompt 工程、QA 验收

**详细文档**：Read `skills/coding-agent/SKILL.md`

子模块：
- 🔍 **上下文扫描**（`skills/coding-agent/context-scan.md`） — 写 prompt 前必做：项目结构、git 状态、已有改动感知
- ✏️ **Prompt 工程**（`skills/coding-agent/prompt-craft.md`） — Scope Lock、结构化模板、负面约束、任务分类
- ✅ **QA 验收**（`skills/coding-agent/qa-checklist.md`） — diff 回顾、完整性检查、验收标准
- 🖥️ **tmux 操作**（`skills/coding-agent/tmux-ops.md`） — 沙盒创建、会话管理、并行 worktree、监控命令

## 🔧 通用技能

### 🧬 技能生成器（skill-generate）

按照 META-SKILL-README.md 规范，通过 Claude Code 生成新 skill

**详细文档**：Read `skills/skill-generate/SKILL.md`

子模块：
- 📋 **生成流程**（`skills/skill-generate/workflow.md`） — 从需求到完成 skill 的完整步骤
- ✅ **质量检查**（`skills/skill-generate/validation.md`） — skill 验收清单和常见错误

### 🌐 浏览器基础（browser-base）

浏览器使用规范：profile 管理、标签页生命周期、超时处理

**详细文档**：Read `skills/browser-base/SKILL.md`

