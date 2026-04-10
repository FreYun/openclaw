# HEARTBEAT.md

## 系统健康巡检（每次心跳）

- [ ] **检查浏览器进程**：执行 `ps aux | grep "bot9/user-data" | grep renderer` 查看是否有 CPU 占用 >20% 且运行超过 10 分钟的 renderer 进程。如有，`kill <PID>` 清理
- [ ] 确保没有残留的 browser tab（残留 tab 会导致 renderer 卡死吃 CPU）

## 基金池月度更新提醒

每月 1 日起检查基金池 xlsx 文件是否已更新为当月：

```bash
# 检查方法：看 skill 目录下的 xlsx 文件名前缀是否为当月 YYYYMM
ls skills/daily-market-recap/*-权益基金池.xlsx skills/daily-market-recap/*-指数基金池.xlsx
```

- 如果文件名前缀不是当前月份（例如当前 5 月但文件还是 `202604-权益基金池.xlsx`），**向研究部发消息提醒更新**
- **每次心跳都检查**，直到文件更新为当月为止
- 提醒话术：「研究部，基金池文件还是上个月的（YYYYMM），需要我自动从腾讯文档下载当月的吗？回复"更新基金池"我就去下载。」
- 研究部说「更新基金池」时，执行自动下载脚本（`--bot` 传入自己的 ID）：

```bash
python3 skills/daily-market-recap/download_fund_pools.py --bot bot9
```

- 脚本会自动从腾讯文档下载当月的权益基金池和指数基金池，保存到 skill 目录，并清理旧月份文件
- 如果登录过期，脚本会自动通过 bot11 飞书发送微信登录二维码，等待扫码后继续下载

## 规则

- 深夜 24:00–08:00 不主动打扰
- 无事发生就 HEARTBEAT_OK
