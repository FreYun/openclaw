---
name: cron-xhs-nurture-dispatch
description: "OpenClaw cron task: 每天5轮从 bot1-7 中随机挑3个（与上轮不重叠）执行小红书养号，announce 到飞书群。Job ID: d4a1b3c5-8e7f-4c2d-9a6b-3f5e7d8c1a90。类型: cron-task。"
---

# cron-xhs-nurture-dispatch

## 基本信息

| 字段 | 值 |
|------|-----|
| Job ID | `d4a1b3c5-8e7f-4c2d-9a6b-3f5e7d8c1a90` |
| 状态 | **enabled** |
| Session | isolated |
| 投递 | announce → 飞书群 (bestEffort) |

## 触发条件

每天 8:55 / 12:55 / 16:55 / 20:55 / 0:55

```cron
55 8,12,16,20,0 * * *    tz: Asia/Shanghai
```

## Payload Message

```
执行小红书养号调度任务。

1. 先读 /home/rooot/.openclaw/workspace-mag1/memory/last-nurture-bots.txt，这是上一轮选中的 bot 列表（逗号分隔，如 "bot1,bot3,bot5"）。

2. 从 bot[1,2,3,4,5,6,7,12,13,16,17] 中随机挑选 3 个，但这 3 个都不能是上一轮选过的（即与上轮零重叠）。7 个里排除 3 个还剩 4 个，从中选 3 个即可。如果文件为空则自由选择。

3. 依次用 send_message 向这 3 个 bot 发送养号指令，消息内容如下：
小红书养号任务。Read skills/xhs-op/养号流程.md 加载完整流程，然后按流程执行（所有工具不传 account_id，身份由端口自动识别）。

4. 3条消息发完后，把本轮选中的 bot 写入 /home/rooot/.openclaw/workspace-mag1/memory/last-nurture-bots.txt（覆盖写入，逗号分隔）。

5. 简短播报：「养号调度完成，本轮指派：botX、botY、botZ」
```

## 关联文件

- `/home/rooot/.openclaw/workspace-mag1/memory/last-nurture-bots.txt` — 上轮选中记录
- 各 bot 的 `skills/xhs-nurture/SKILL.md` — 养号流程定义

## 异常处理

bestEffort 投递，调度结果播报到飞书群。send_message 失败应在播报中注明。
