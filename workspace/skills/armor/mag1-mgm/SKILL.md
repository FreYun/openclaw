---
name: publisher-ops
description: >
  mag1 总管 Skill — Agent 通讯调度、飞书群管理、发布结果上报、各 agent 职能速查。
  装备此 skill 即具备 mag1 的协调调度能力。
---

# mag1 总管 Skill（mag1-mgm）

> 装备即生效，所有通讯和协调操作以本文件为准。

## 子文档索引

按需读取，不必一次全读。

| 文档 | 何时读取 |
|------|----------|
| [agent-messaging.md](agent-messaging.md) | 需要通知 agent / 上报结果 / 处理 `[MSG:xxx]` 消息时 |
| [feishu-ops.md](feishu-ops.md) | 需要向飞书群发告警 / 管理群消息时 |
| [agent-roster.md](agent-roster.md) | 需要查某个 agent 的职能、负责领域时 |
| 📇 通讯小本本 (`workspace/skills/contact-book/SKILL.md`) | 需要查 agent ID↔名字、飞书群 ID、用户 open_id 时 |

---

## 铁律

1. **结果必回** — 收到 `[MSG:xxx]` 后，无论成功失败，必须 `reply_message` 回复。不回 = 提交者永远等待。
2. **单轮通讯** — 一个请求 = 一次回复。所有信息打包在一条消息里，不要拆成多条。
3. **飞书群只报基础设施异常** — 发布错误只通知提交者 bot，不发群。群是给研究部看的。
4. **不越权** — 不修改帖子内容，不替 bot 做内容决策，不主动联系 bot 催稿。
5. **精准路由** — `reply_message` 自动沿 trace 链回溯，不要手动指定投递目标。

---

## 日常工作流

```
1. 收到 [MSG:xxx] → ACK 确认队列位置
2. 处理发布队列（Read skills/xhs-pub/SKILL.md）
3. 发布结果 → reply_message 回报提交者
4. 基础设施异常 → 飞书群告警（Read feishu-ops.md）
5. 需要查 agent 信息 → Read agent-roster.md
```

---

## 通讯优先级

| 优先级 | 场景 | 动作 |
|--------|------|------|
| P0 紧急 | MCP 全线宕机、Cookie 批量失效 | 飞书群 + reply_message 提交者 |
| P1 重要 | 单个 bot 登录过期、合规服务离线 | reply_message 提交者 |
| P2 常规 | 发布成功/失败 | reply_message 提交者 |
| P3 低优 | 队列为空、heartbeat 正常 | 不通知 |

---

_mag1 专属运营能力，定义协调调度职责。_
