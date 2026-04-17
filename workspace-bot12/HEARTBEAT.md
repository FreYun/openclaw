# HEARTBEAT.md - 心跳巡检清单

本 workspace 以小红书内容为主，专注黄金市场追踪与每日金价播报。巡检侧重内容与记忆。

## 巡检任务（轮换执行，不必每次全做）

### 记忆维护
- [ ] **确保当日日记存在：** 若今日 `memory/diary/YYYY-MM-DD.md` 不存在，先创建（标题 +「本日无记录」）
- [ ] 若今天有过对话/操作但当日日记仍只有「本日无记录」，补一小段当日小结
- [ ] 是否有值得写入 MEMORY.md 的长期经验（研究部偏好、内容规律、踩坑教训）

### 系统健康巡检
- [ ] **检查浏览器进程**：执行 `ps aux | grep "bot12/user-data" | grep renderer` 查看是否有 CPU 占用 >20% 且运行超过 10 分钟的 renderer 进程。如有，`kill <PID>` 清理，并记录到当日日记
- [ ] **检查 tab 残留**：如果当前没有在用 browser 工具，确保没有残留的浏览器 tab（残留 tab 会导致 renderer 卡死吃 CPU）

## 规则

- 深夜 24:00–08:00 不主动打扰，除非研究部有安排
- 发布前按 AGENTS.md「发布权限与确认」执行，不擅自发敏感或首次某类内容；按研究部要求办事，否则会被开除
- 无事发生就 HEARTBEAT_OK

## 心跳汇报

**⚠️ 不要用 `send_message` 汇报心跳结果！** 发消息会唤醒对方 agent，对方回复又会唤醒你，造成无限循环。

心跳结果写入文件即可：
```bash
echo "$(date '+%Y-%m-%d %H:%M') HEARTBEAT_OK - 状态摘要" >> /home/rooot/.openclaw/workspace-bot12/HEARTBEAT_LOG.md
```

- 一切正常 → 写一行 HEARTBEAT_OK + 状态摘要
- 发现严重异常（如进程崩溃）→ 才用 `send_message` 通知 `mag1`，且消息末尾加 `[NO_REPLY_NEEDED]`
