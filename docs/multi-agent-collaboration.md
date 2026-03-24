# OpenClaw 多 Agent 协作体系

> 2026-03-23

## 架构总览

11 个内容 Bot + 4 个系统 Agent，1 人管理，7×24 自动运转。

```
                    ┌─────────────────────────┐
                    │   研究部 HQ (bot_main)    │
                    │   调度 · 监控 · 协作编排   │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
  ┌──────────────┐     ┌──────────────┐      ┌──────────────┐
  │ 内容 Bot ×11  │     │  系统 Agent   │      │  基础设施     │
  │ 独立人格/账号  │     │  印务局(发布)  │      │  Redis 消息线 │
  │ 独立记忆/技能  │     │  技能部(巡检)  │      │  Cron 调度器  │
  │ 独立浏览器    │     │  Coder(开发)  │      │  Dashboard   │
  └──────────────┘     └──────────────┘       └──────────────┘
```

## 核心设计

### 1. 独立人格，非模板复制

每个 Bot 有完整的人格文件体系：

| 文件 | 作用 |
|------|------|
| SOUL.md | 价值观、行为底线（Bot 不可自改） |
| IDENTITY.md | 名字、人设、风格 |
| MEMORY.md + memory/ | 长期记忆 + 每日日记，跨会话连续 |
| skills/ | symlink 共享技能 + 独有技能 |

bot5（宣妈慢慢变富，基金理财）和 bot7（老K投资笔记，行业研究）写出来的内容天然不同——语气、选题、结构都有差异。

### 2. 能力分层（RBAC）

Research Gateway 按角色分配数据访问权限：

| 角色 | Bot | 可用工具范围 |
|------|-----|------------|
| full_access | bot2/7/8/11 | 个股、行业、债券、宏观全量 |
| fund_advisor | bot3/5 | 基金、宏观 |
| content_creator | bot1/4/6/9/10 | 新闻、研报、基础行情 |

YAML 声明式配置，改完 `reload_permissions` 即时生效。

### 3. 发布流水线

所有内容必须经过印务局（mcp_publisher）合规审核：

```
Bot 创作 → submit-to-publisher → pending/
    → mcp_publisher 审核
    → ✓ 调用小红书 MCP 发布 → published/
    → ✗ 修改意见返回 Bot → 修改后重新提交
```

支持 text_to_image / image / longform / video 四种格式。

### 4. 技能共享（Symlink）

```
workspace/skills/xhs-op/              ← 源文件，改一处全生效
workspace-bot7/skills/xhs-op → ../../workspace/skills/xhs-op (symlink)
workspace-bot7/skills/stock-watcher/  ← bot7 独有
```

通用技能改源文件即刻同步所有 Bot，独有技能体现专业方向。

### 5. 自动化运营

Cron 调度器 JSON 声明式配置，驱动全部自动化：

| 任务 | 频率 | Bot |
|------|------|-----|
| 养号互动 | 每 3h | bot1-7 |
| 系统巡检 | 每 3h | bot_main |
| 行情速递 | 工作日盘前 | bot7 |
| 技能巡检 | 每日 | skills |

每个任务在独立 session 中执行，互不干扰。

### 6. 故障隔离

- 每 Bot 独立 MCP 端口（18061-18071），单点故障不扩散
- 每 Bot 独立 Chrome Profile，浏览器崩溃不互相影响
- Session 级别隔离，Cron 任务互不干扰

## 扩展性

新增 Bot：创建 workspace → symlink 通用技能 → 配 IDENTITY/SOUL → 启动。边际成本约 30 分钟。
