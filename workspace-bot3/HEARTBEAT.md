# HEARTBEAT.md

## 系统健康巡检（每次心跳）

- [ ] **检查浏览器进程**：执行 `ps aux | grep "bot3/user-data" | grep renderer` 查看是否有 CPU 占用 >20% 且运行超过 10 分钟的 renderer 进程。如有，`kill <PID>` 清理
- [ ] 确保没有残留的 browser tab（残留 tab 会导致 renderer 卡死吃 CPU）

## 规则

- 深夜 24:00–08:00 不主动打扰
- 无事发生就 HEARTBEAT_OK

## 心跳汇报

心跳完成后，使用 `send_message` 工具将巡检结果发送给 `bot_main`（魏忠贤）。

- 一切正常 → 发送简短的 "HEARTBEAT_OK" + 状态摘要
- 发现异常 → 发送详细的异常报告
- 格式：`send_message(to="bot_main", content="[bot_id] 心跳汇报: ...")`
