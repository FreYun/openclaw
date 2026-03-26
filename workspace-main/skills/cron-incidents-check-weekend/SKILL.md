---
name: cron-incidents-check-weekend
description: "OpenClaw cron task: 周末早晚各一次检查 incidents.jsonl 异常，announce 到飞书群。Job ID: b4e7a1c3-6d92-4f8e-a315-c7d8e9f0b234。类型: cron-task。"
---

# cron-incidents-check-weekend

## 基本信息

| 字段 | 值 |
|------|-----|
| Job ID | `b4e7a1c3-6d92-4f8e-a315-c7d8e9f0b234` |
| 状态 | **disabled** |
| Session | isolated |
| 投递 | announce → 飞书群 |

## 触发条件

周末 8 点和 23 点

```cron
7 8,23 * * 6,0    tz: Asia/Shanghai
```

## Payload Message

```
Read HEARTBEAT.md
```

## 说明

周末精简版异常检查，仅早晚各一次。逻辑同 `cron-incidents-check`。

## 异常处理

同工作日版，announce 投递飞书群。
