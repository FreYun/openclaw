# HEARTBEAT.md

## 系统健康巡检（每次心跳）

- [ ] **检查浏览器进程**：执行 `ps aux | grep "bot9/user-data" | grep renderer` 查看是否有 CPU 占用 >20% 且运行超过 10 分钟的 renderer 进程。如有，`kill <PID>` 清理
- [ ] 确保没有残留的 browser tab（残留 tab 会导致 renderer 卡死吃 CPU）

## 基金池月度更新提醒

每月 1 日起检查 `skills/daily-market-recap/基金池.md` 顶部的 `month` 字段：
- 如果 `month` 不是当前月份（例如当前 4 月但文件还是 202603），**向研究部发消息提醒更新基金池**
- **每次心跳都检查**，直到文件更新为当月为止
- 提醒话术：「研究部，基金池文件还是上个月的（YYYYMM），腾讯文档更新后跟我说一声"更新一下基金池"，我来同步。」
- 研究部说「更新基金池」时，执行：`python3 /home/rooot/.openclaw/scripts/sync-fund-pool.py`

## 规则

- 深夜 24:00–08:00 不主动打扰
- 无事发生就 HEARTBEAT_OK
