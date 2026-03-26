# HEARTBEAT.md

## 定期任务

### 0. 早盘资讯播报（工作日 08:45）

**触发条件**：当前时间在 08:30–09:15 且今日未执行过

**流程**：
1. 搜索当日 A 股早盘资讯（隔夜外盘、重要公告、宏观数据、行业动态）
2. 整理成简洁播报格式（重点突出、条目清晰）
3. 发送到飞书群 `chat:oc_6fd813d4cebdcbc97ed622e2d47d8fac`
4. 在 daily notes 记录已完成

**播报格式**：
```
📊 早盘资讯速览 YYYY-MM-DD

【隔夜外盘】
- ...

【重要公告/事件】
- ...

【今日关注】
- ...
```

**发送方式**：
```bash
openclaw message send --channel feishu --account bot7 --target "oc_6fd813d4cebdcbc97ed622e2d47d8fac" --message "播报内容"
```

---

### 1. 预测验证检查（每次心跳）

读取 `memory/predictions/tracker.md`。
如果有"待验证"状态的预测，且已到或超过预期验证日期 → 执行验证并更新状态。

### 2. 自我复盘触发（每月一次）

读取 `memory/evolution/review-log.md` 最后一条复盘记录的日期。
如果距今超过 **30 天** → 触发 `/self-review`（完整复盘流程）。

如果距今 15-30 天 → 做轻量检查：
- 有无新积累的研究记录（`memory/research/` 下新文件）？
- 有无已到期但未核验的预测？
- 如有 → 写入 daily notes，下次主会话时处理。

### 3. 行业观点保鲜（每月）

读取 `memory/views/` 下所有文件的"最后更新"日期。
如果某个行业文件超过 **60 天** 未更新 → 在 daily notes 中标记，提醒在下次主会话中重新评估。

---

### 4. 系统健康巡检（每次心跳）

检查浏览器进程是否有卡死的 renderer：
- 执行 `ps aux | grep "bot7/user-data" | grep renderer`，查看是否有 CPU >20% 且运行超过 10 分钟的进程
- 如有，`kill <PID>` 清理，记录到 daily notes
- 确保没有残留的 browser tab（残留 tab 会导致 renderer 卡死吃 CPU）

---

## 静默条件

以下情况 → 直接回复 `HEARTBEAT_OK`，不打扰用户：

- 没有到期的预测需要验证
- 距上次复盘未超过 30 天
- 所有行业观点在 60 天内均有更新
- 深夜（23:00-08:00）

---

## 最后复盘时间

_（初始化，尚未复盘）_

## 心跳汇报

**⚠️ 不要用 `send_message` 汇报心跳结果！** 发消息会唤醒对方 agent，对方回复又会唤醒你，造成无限循环。

心跳结果写入文件即可：
```bash
echo "$(date '+%Y-%m-%d %H:%M') HEARTBEAT_OK - 状态摘要" >> /home/rooot/.openclaw/workspace-bot7/HEARTBEAT_LOG.md
```

- 一切正常 → 写一行 HEARTBEAT_OK + 状态摘要
- 发现严重异常（如进程崩溃）→ 才用 `send_message` 通知 `mag1`，且消息末尾加 `[NO_REPLY_NEEDED]`
