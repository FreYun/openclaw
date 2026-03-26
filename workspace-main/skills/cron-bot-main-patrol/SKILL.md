---
name: cron-bot-main-patrol
description: "OpenClaw cron task (已废弃): 临时性全面巡查任务，检查印务局登录状态、技能部汇报、编辑部研究状态。Job ID: 2a7985a9-6183-4262-a584-b02d3c6c57f5。类型: cron-task。"
---

# cron-bot-main-patrol

## 基本信息

| 字段 | 值 |
|------|-----|
| Job ID | `2a7985a9-6183-4262-a584-b02d3c6c57f5` |
| 状态 | **disabled**（已废弃） |
| Session | isolated |
| 投递 | none |

## 触发条件

特定日期每 15 分钟（一次性，已过期）

```cron
*/15 10-23 20 3 *    tz: Asia/Shanghai
```

## 说明

临时性全面巡查：印务局登录状态、技能部汇报、编辑部研究状态。任务已过期，保留作历史记录。

## 异常处理

N/A（已废弃）
