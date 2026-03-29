---
name: cron-daily-model-report
description: "OpenClaw cron task: 每天中午12点通报各 bot 当前使用的模型序列号，整理成表格 announce 到飞书群。Job ID: caffb0d4-f51d-4e9c-b10a-de2bcce28cb5。类型: cron-task。"
---

# cron-daily-model-report

## 基本信息

| 字段 | 值 |
|------|-----|
| Job ID | `caffb0d4-f51d-4e9c-b10a-de2bcce28cb5` |
| 状态 | **enabled** |
| Session | isolated |
| 投递 | announce → 飞书群 |

## 触发条件

每天 12:00

```cron
0 12 * * *    tz: Asia/Shanghai
```

## Payload Message

```
通报各 bot 当前使用的模型序列号。执行以下脚本获取数据，然后整理成简洁表格播报：

python3 -c "
import json, os, glob
agents_dir = '/home/rooot/.openclaw/agents'
for agent_dir in sorted(glob.glob(f'{agents_dir}/*/sessions')):
    agent = agent_dir.split('/')[-2]
    files = [f for f in glob.glob(f'{agent_dir}/*.jsonl') if not any(x in f for x in ['.deleted', '.reset', '.lock'])]
    if not files: print(f'{agent}: 无活跃会话'); continue
    latest = max(files, key=os.path.getmtime)
    with open(latest) as fh:
        for i, line in enumerate(fh):
            if i > 5: break
            d = json.loads(line.strip())
            if 'modelId' in d:
                print(f'{agent}: {d.get(\"provider\",\"?\")}/{d[\"modelId\"]}')
                break
        else: print(f'{agent}: 未知')
"

播报格式：
【模型序列号日报】
| Agent | Provider | Model |
按 bot1-10 → 系统 agent 排列。
```

## 异常处理

脚本执行失败时应在播报中注明错误信息。
