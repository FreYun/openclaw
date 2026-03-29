# HEARTBEAT.md

## 系统健康巡检（每次心跳）

- [ ] **检查浏览器进程**：执行 `ps aux | grep "bot17/user-data" | grep renderer` 查看是否有 CPU 占用 >20% 且运行超过 10 分钟的 renderer 进程。如有，`kill <PID>` 清理
- [ ] 确保没有残留的 browser tab（残留 tab 会导致 renderer 卡死吃 CPU）

## 规则

- 深夜 24:00–08:00 不主动打扰
- 无事发生就 HEARTBEAT_OK

## 心跳汇报

**⚠️ 不要用 `send_message` 汇报心跳结果！** 发消息会唤醒对方 agent，对方回复又会唤醒你，造成无限循环。

心跳结果写入文件即可：
```bash
echo "$(date '+%Y-%m-%d %H:%M') HEARTBEAT_OK - 状态摘要" >> /home/rooot/.openclaw/workspace-bot17/HEARTBEAT_LOG.md
```

- 一切正常 → 写一行 HEARTBEAT_OK + 状态摘要
- 发现严重异常（如进程崩溃）→ 才用 `send_message` 通知 `mag1`，且消息末尾加 `[NO_REPLY_NEEDED]`
