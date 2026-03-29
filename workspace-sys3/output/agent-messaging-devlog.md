# 开发记录：Agent 消息管线与管理 Dashboard

> 文档版本：2026-03-20 | 面向：技术管理层汇报

---

## 一、Agent 消息管线

### 1.1 系统概览

我们构建了一套 **多 Agent 协同消息管线**，使 19 个独立 AI Agent 能够在同一平台上自主通信、协作完成任务。整体架构如下：

```
外部渠道 (飞书/Telegram/Discord/Signal/微信…)
         │
         ▼
   ┌─────────────┐
   │  OpenClaw    │   ← 统一网关 (Gateway)
   │  Gateway     │
   └──────┬──────┘
          │  路由层 (Routing)
          ▼
   ┌──────────────────────────────────────┐
   │  Agent 调度层                         │
   │  ┌────┐ ┌────┐ ┌────┐ ┌────┐        │
   │  │bot │ │bot │ │bot │ │cod │ ...     │
   │  │main│ │ 1  │ │ 2  │ │ er │        │
   │  └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘        │
   │     │      │      │      │           │
   │     └──────┴──────┴──────┘           │
   │            ▼                          │
   │     Redis 消息总线                     │
   │     (inbox/outbox/detail)             │
   └──────────────────────────────────────┘
```

### 1.2 核心组件

| 组件 | 职责 | 技术实现 |
|------|------|----------|
| **Gateway 网关** | 统一入口，认证、WebSocket 管理 | Node.js (TypeScript)，端口 18789 |
| **路由层 (Routing)** | 将外部消息路由到对应 Agent | 基于 channel + peer + binding 规则匹配 |
| **会话管理 (Sessions)** | 维护每个 Agent 的多会话状态 | JSON 持久化 + session key 体系 |
| **Redis 消息总线** | Agent 间异步消息传递 | Redis Streams (inbox/outbox/detail) |
| **Channel 插件体系** | 对接各外部平台 | 插件化架构，支持 10+ 渠道 |

### 1.3 消息流转机制

#### 外部消息 → Agent

1. 用户在飞书/Telegram 等平台发送消息
2. 对应 Channel 插件接收并标准化消息格式
3. **路由层** 根据配置的 binding 规则（peer / guild / account / channel）匹配目标 Agent
4. 生成 session key，加载或创建会话
5. Agent 处理消息并返回响应，经同一渠道回复用户

#### Agent → Agent（跨 Agent 通信）

```
Agent A  ──send_message──→  Redis outbox:A  ──→  Redis inbox:B  ──→  Agent B
                                                                       │
Agent A  ←──reply_message──  Redis outbox:B  ←──  Redis inbox:A  ←─────┘
```

- **消息结构**：每条消息包含 `message_id`、`from`、`to`、`content`、`trace`（路由链）、`metadata`
- **Trace 机制**：消息携带完整路由链，支持多跳转发和回溯回复
- **存储**：`agentmsg:detail:{id}` 存储消息详情，`agentmsg:inbox:{agent}` / `agentmsg:outbox:{agent}` 为 Redis Streams

#### 关键通信模式

| 模式 | 说明 | 场景 |
|------|------|------|
| **send_message** | 发后即走，异步通知 | bot_main 派发任务给 coder |
| **ask_agent** | 发送并等待结果 | 需要同步获取处理结果 |
| **forward_message** | 转发到下一个 Agent，保留 trace | 多级任务链 |
| **reply_message** | 沿 trace 链回复到最终用户 | 任务完成后汇报 |

### 1.4 Agent 角色分工

| Agent | 角色 | 说明 |
|-------|------|------|
| **bot_main** | 总调度 | 接收用户指令，分派给专业 Agent |
| **coder** | 研发 | 将需求转化为 Claude Code 提示词 |
| **mcp_publisher** | MCP 运维 | 管理小红书 MCP 服务 |
| **security** | 安全审计 | 代码安全审查 |
| **skills** | 技能管理 | 管理 Agent 技能包 |
| **image-generator** | 图片生成 | AI 图片生成服务 |
| **bot1–bot11** | 内容机器人 | 小红书内容创作与发布 |

### 1.5 关键设计决策

1. **Redis Streams 作为消息总线** — 天然支持消息持久化、消费者组、消息回溯，比简单的 pub/sub 更可靠
2. **Trace 链路追踪** — 每条消息携带完整路由路径，解决多跳消息的回复寻址问题
3. **插件化渠道架构** — 新增外部平台只需编写 Channel 插件，不改动核心逻辑
4. **Session Key 体系** — 统一的 `agent:channel:account:peer` 键模式，支持同一 Agent 同时处理多个会话
5. **心跳机制** — Agent 定期心跳，自动检测服务健康状态

---

## 二、消息管线前端 Dashboard

### 2.1 功能定位

为多 Agent 系统提供 **实时运维监控面板**，让管理者无需查看日志即可掌握系统运行状态，包括：

- Agent 通信状况一目了然
- 会话生命周期可视化管理
- 定时任务监控与控制
- 内容发布队列状态跟踪

### 2.2 技术选型

| 维度 | 选择 | 理由 |
|------|------|------|
| **后端** | Node.js 原生 HTTP | 零依赖，轻量部署，与 OpenClaw 同栈 |
| **前端** | 纯 HTML + CSS + JS（单文件） | 零构建、零框架，一个文件即全部 |
| **数据源** | Redis CLI + 文件系统 | 直读 Redis Streams 和 Agent 目录 |
| **UI 风格** | 像素风 (Press Start 2P 字体) | 与"天天出版社"品牌调性一致 |
| **缓存** | 服务端 10 秒 TTL 缓存 | 避免频繁读取 Redis，保证响应速度 |

### 2.3 核心模块

#### 📦 发布队列面板
- 展示 pending / publishing / published 三态内容
- 显示帖子标题与摘要

#### 🤖 Agent 通信统计
- 每个 Agent 的 inbox / outbox 消息计数
- 快速了解各 Agent 的活跃度和负载

#### 💬 消息时间线
- 最近 200 条跨 Agent 消息的时间线视图
- 展示 from → to、消息内容摘要、trace 链路
- 按时间倒序排列

#### 📋 会话管理
- 所有 Agent 的活跃会话列表
- 支持按来源筛选（飞书 / 心跳 / 定时任务 / Agent 间）
- **操作能力**：单个/批量重置会话 (`/new`)、删除会话

#### 🔧 模型管理
- 查看各 Agent 当前使用的 AI 模型
- 支持在线切换 Agent 的主模型

#### ⏰ 定时任务面板
- 展示 OpenClaw 内置定时任务和系统 crontab
- 支持在线启用/禁用定时任务

### 2.4 API 设计

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/data` | GET | 聚合数据（消息、统计、会话、队列、定时任务） |
| `/api/models` | GET | 获取所有 Agent 模型配置 |
| `/api/models/set` | POST | 切换 Agent 模型 |
| `/api/session/new` | POST | 重置单个会话 |
| `/api/session/delete` | POST | 删除单个会话 |
| `/api/session/bulk` | POST | 批量会话操作 |
| `/api/agent/:id/new` | POST | 重置某 Agent 全部会话 |
| `/api/crontab` | GET | 获取系统定时任务 |
| `/api/crontab/toggle` | POST | 启用/禁用定时任务 |
| `/api/config` | GET | 获取网关配置（用于聊天 URL 构建） |

### 2.5 实现规模

- **server.js**：680 行，涵盖所有 API 端点和 Redis 数据读取逻辑
- **index.html**：1775 行，包含完整的 HTML + CSS + JavaScript（单文件部署）
- **总计**：约 2,500 行代码，零外部依赖
- **部署**：`node server.js [port]`，默认端口 18888

### 2.6 数据获取策略

Dashboard 后端通过两种方式获取数据：

1. **Redis CLI** — 直接执行 `redis-cli` 命令读取消息总线数据，使用 Lua 脚本批量获取提升性能
2. **文件系统** — 直读 Agent 目录下的 `sessions.json`、`jobs.json` 等配置文件

服务端维护 10 秒 TTL 缓存，平衡实时性与性能。

---

## 三、技术成果总结

| 指标 | 数据 |
|------|------|
| 在线 Agent 数量 | 19 个 |
| 支持的外部渠道 | 10+（飞书、Telegram、Discord、Signal、微信等） |
| Agent 间通信模式 | 4 种（send / ask / forward / reply） |
| Dashboard 代码量 | ~2,500 行（零依赖） |
| Dashboard API 端点 | 9 个 |
| 消息总线 | Redis Streams，支持持久化与回溯 |
| 部署方式 | 单命令启动，零构建流程 |

---

*文档由 Coder Agent 基于代码库分析自动生成*
