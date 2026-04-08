---
name: cron-incidents-check
description: "OpenClaw cron task: 工作日每3小时检查 incidents.jsonl 是否有新 ERROR 异常，announce 到飞书群。Job ID: a3f8c2e1-9b47-4d6a-8e05-f7c3d2a19b84。类型: cron-task。"
---

# cron-incidents-check

## 基本信息

| 字段 | 值 |
|------|-----|
| Job ID | `a3f8c2e1-9b47-4d6a-8e05-f7c3d2a19b84` |
| 状态 | **disabled** |
| Session | isolated |
| 投递 | announce → `chat:oc_e59188e3ecdb04acd9b33843870a2249` |

## 触发条件

工作日 8/11/14/17/20/23 点

```cron
7 8,11,14,17,20,23 * * 1-5    tz: Asia/Shanghai
```

## Payload Message

```
Read HEARTBEAT.md
```

## 说明

通过 isolated session 读取 HEARTBEAT.md 触发心跳检查流程，检测 incidents.jsonl 中的新 ERROR。结果 announce 到飞书群。

## 异常处理

检查结果由 announce 投递到飞书群；如有异常会在播报中体现。
