# OpenClaw 装备系统

> 2026-03-24 v4

---

## 它是什么

装备系统用 RPG 装备隐喻管理 14 个 AI Agent 的能力配置。每个 Agent 像游戏角色一样拥有固定槽位，技能以"装备"形式插拔，装上就有能力、卸下就没有。

通过 Dashboard（`http://localhost:18888`）可视化操作，拖拽即可完成装备变更，变更后 Agent 下次会话自动生效。

## 14 个 Agent 与三种工种

| 工种 | Agent | 职责 |
|------|-------|------|
| 🎭 **前台** | bot1 ~ bot11 | 面向公众：产出内容、运营账号、与读者互动 |
| 🦅 **管理** | bot_main | 全局管理：监控 agent、调度任务、审批变更 |
| 🔧 **内务** | mcp_publisher, coder | 后勤保障：发布执行、基础设施、研发支持 |

工种是 Agent 的底层角色定位，自动写入 SOUL.md，不可变更。

## 槽位体系

每个 Agent 有 11 个装备槽位：

| 槽位 | 中文 | 数量 | 含义 | 示例 |
|------|------|:----:|------|------|
| ⛑️ helm | 头盔 | 1 | 工种（系统分配） | 前台 / 管理 / 内务 |
| 👔 armor | 衣服 | 1 | 核心职业能力 | 小红书运营、发布中心 |
| 💍 accessory | 饰品 | 2 | 人设风格 | 宣妈风格、记录灵感、自我复盘 |
| ⚔️ weapon | 武器 | 6 | 研究技能 | 财报横评、资金流向、深度研究 |
| 👢 boots | 靴子 | 1 | 策略模块 | 尚未启用 |

**装备效果**：Agent 会话启动时读取 `EQUIPPED_SKILLS.md`，其中列出所有已装备技能的名称、描述和文档路径。Agent 按需 `Read` 具体 SKILL.md 获取详细操作指令。

## 技能（Skill）

### 什么是一个技能

一个技能 = 一个目录，核心文件：

- `skill.json` — 元数据：名称、图标、槽位类型、描述、依赖
- `SKILL.md` — 详细操作文档（Agent 实际读取和执行的内容）
- 可选子文档 — 复杂技能拆分为多个子模块

skill.json 示例：

```json
{
  "name": "财报横评",
  "icon": "📊",
  "slot": "weapon",
  "desc": "行业财报横向对比与核心观点提取",
  "requires": ["research-mcp"]
}
```

### 两种技能类型

| 类型 | 能否卸下 | 占槽位 | 用途 |
|------|:------:|:------:|------|
| **装备技能** | 可以 | 是 | 主要能力模块，可按需搭配 |
| **基础设施** | 不可以 | 否 | 底层能力，所有 bot 始终拥有 |

当前基础设施技能：印务局投稿（`submit-to-publisher`）、养号互动（`xhs-nurture`）、异常上报（`report-incident`）、技能网关（`skill-gateway`）。

### 通用技能 vs 专属技能

**通用技能**存放在 `workspace/skills/`，通过 symlink 分发给各 bot。修改源文件一处改、所有 bot 同步生效。

**专属技能**直接放在某个 bot 的 `workspace-botN/skills/` 下，仅该 bot 可见。用于体现个性化能力，如：

| Bot | 专属技能 |
|-----|---------|
| bot1 | 每日复盘 |
| bot5 | 宣妈封面生成、宣妈内容风格 |
| bot6 | James 封面生成、James 内容风格 |
| bot7 | 大飞哥风格、能化跟踪 |
| bot_main | 管理运维、开发参考、安全审计 |
| coder | Claude Code 研发 |

### 复合技能（subSkills）

大型技能可以包含子模块。以 `xhs-op`（小红书运营）为例：

| 子模块 | 文档 | 功能 |
|--------|------|------|
| 🔧 MCP 工具 | `mcp-tools.md` | 登录、浏览、搜索、互动 |
| ⚠️ 发帖前必读 | `发帖前必读.md` | 平台规则、敏感词红线 |
| 💡 内容策划 | `内容策划.md` | 选题推荐、内容生成 |
| 📦 素材积累 | `素材积累.md` | 素材巡逻、灵感池 |
| 🤝 养号互动 | `养号互动.md` | 搜索→点赞→评论→回复 |
| 📮 投稿发布 | `投稿发布.md` | 通过印务局提交 |

子模块自动列在 EQUIPPED_SKILLS.md 中，Agent 按需读取对应文档。

## 自动生成的文件

装备变更后系统自动更新两个文件：

### EQUIPPED_SKILLS.md

写入 `workspace-botN/EQUIPPED_SKILLS.md`，列出 armor → accessory → weapon → boots 所有已装备技能的名称、描述、文档路径和子模块。Agent 启动时读取此文件了解自己"会什么"。

### SOUL.md 工种标记

在 SOUL.md 顶部自动注入工种信息（用 HTML 注释标记对保护，不影响手写内容）：

```markdown
<!-- ROLE:START -->
> **工种：前台** — 面向公众的内容创作者：产出内容、运营账号、与读者互动
>
> 详细职责定义：Read `skills/frontline/SKILL.md`
<!-- ROLE:END -->
```

## Dashboard 操作

| 操作 | 方式 | 效果 |
|------|------|------|
| **装备** | 拖拽技能到槽位 | 创建 symlink + 写入装备状态 + 重新生成 manifest |
| **卸下** | 点击已装备技能 | 删除 symlink + 清空槽位 + 重新生成 manifest |
| **换位** | 同类型槽位间拖拽 | 交换两个槽位内容 |
| **同步** | 点击同步按钮 | 以磁盘为准重建全部装备状态（14 个 Agent 一起刷新） |

保护机制：
- 基础设施技能不可卸下（UI 禁用 + 服务端拒绝）
- 技能只能装入对应类型的槽位（weapon 不能放到 armor 槽）
- 槽位满时多余技能进入 overflow 列表，等待手动调整

## 运维速查

### 新增通用技能

1. 在 `workspace/skills/` 下创建目录，写 `skill.json` + `SKILL.md`
2. 给目标 bot 创建 symlink：`ln -s ../../workspace/skills/xxx workspace-botN/skills/xxx`
3. Dashboard 同步 → 自动出现在装备面板

### 新增专属技能

在 `workspace-botN/skills/` 下直接创建真实目录（非 symlink），同步后仅该 bot 可见。

### 删除技能

1. 删除所有 bot 的 symlink：`find workspace-*/skills/ -name "xxx" -type l -delete`
2. 删除源目录：`rm -rf workspace/skills/xxx`
3. Dashboard 同步 → 自动从装备中移除

---

*基于 dashboard/server.js，2026-03-24*
