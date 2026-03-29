# OpenClaw Agent 通讯框架

> 2026-03-23

## 为什么需要通讯框架

多 Agent 系统中，Agent 之间需要协作（bot7 让 bot11 查数据、印务局审核后通知创作 Bot），执行结果需要通知到人。没有统一框架，每对 Agent 之间写专线，系统会变成面条式的点对点调用，加一个 Bot 就要改一堆地方。通讯框架把这些交互标准化——Agent 间用消息总线，通知用飞书统一出口——系统在 15 个 Agent 的规模下保持可维护、可扩展。

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent 层                                 │
│   mag1    bot1-11    sys1    skills    coder       │
└──────┬──────────┬──────────┬───────────────┬────────┬──────────┘
       │          │          │               │        │
       ▼          ▼          ▼               ▼        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Redis 消息总线                                │
│                                                                 │
│  inbox:{agent_id}    Stream     每个 Agent 一个收件箱            │
│  outbox:{agent_id}   Stream     每个 Agent 一个发件箱            │
│  detail:{msg_id}     Hash       消息详情（from/to/content/trace）│
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    飞书通知层                                    │
│  WebSocket 长连接 · per-bot 去重 · 结果/告警/状态推送到运营人员    │
└─────────────────────────────────────────────────────────────────┘
```

## 消息模型

```
message_id              唯一标识
from / to               发送方 / 接收方 Agent ID
type                    request / reply / forward
status                  pending / delivered / replied
content                 消息内容
created_at              时间戳
reply_to_message_id     关联的原始消息
trace                   链路追踪数组（核心设计，见下文）
metadata                扩展元数据
```

## 为什么选 Redis Streams

| | Pub/Sub | Redis Streams |
|--|---------|---------------|
| 持久化 | 不持久化，错过即丢 | 持久化，可回溯 |
| 历史查询 | 不支持 | XRANGE/XREVRANGE 按时间查 |
| 消费确认 | 无 | 支持 ACK |

Agent 可能不在线（session 结束了），消息需要存下来等下次唤醒时消费。Pub/Sub 做不到这一点。

## 通讯工具集

| 工具 | 用途 |
|------|------|
| `send_message` | 发起新请求，写入目标 inbox |
| `reply_message` | 回复消息，根据 trace 自动路由到上游 |
| `forward_message` | 转发给其他 Agent，trace 自动追加当前节点 |
| `get_message` / `list_messages` | 查询消息详情 / 收件箱 |

## Trace 链路追踪

这是消息总线最核心的设计。每条消息携带 trace 数组，记录经过的所有节点：

```
1. HQ → bot7:  send_message
   trace: [{agent:"mag1", reply_channel:"feishu", reply_to:"ou_xxx"}]

2. bot7 → bot11:  forward_message
   trace: [{mag1...}, {agent:"bot7"}]          ← 自动追加

3. bot11 reply → 根据 trace 自动路由回 bot7
4. bot7 reply  → 根据 trace 自动路由回 HQ → 推送飞书
```

**reply_message 不需要指定目标**，根据 trace 自动回溯到上游发起者，最终通过 `reply_channel` 推送到运营人员的飞书。

多跳转发场景下，trace 完整记录每一跳，任何一条消息都能追溯完整请求路径。

## 通讯纪律

通过 TOOLS_COMMON.md 对所有 Agent 强制执行：

- **唯一通道**：send/reply/forward_message，禁止 CLI 直调、shell 脚本
- **严格单轮**：一个请求 = 一条完整回复，不拆分多条
- **必须 reply_message**：收到 `[MSG:xxx]` 必须用 reply_message 回复，纯文本回复发送方收不到
- **必须带 trace**：每条消息包含来源链路，reply 自动路由依赖于此

## 飞书通知层

消息总线的出口。reply_message 根据 trace 中的 `reply_channel: "feishu"` 自动同步推送到运营人员。

- WebSocket 长连接保证实时性
- per-bot 去重文件（`feishu/dedup/botN.json`）防止飞书 API 重复投递
- 覆盖场景：Cron 执行结果、发布状态、异常告警、消息回复

## 监控

Dashboard（:18888）通过 Redis Lua 脚本批量查询 inbox/outbox，实时展示 Agent 间消息流。JSONL session 日志记录每次 Agent 执行的完整对话，可回放排查问题。
