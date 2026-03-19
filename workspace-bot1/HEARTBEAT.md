# HEARTBEAT.md

## 系统健康巡检（每次心跳）

- [ ] **检查浏览器进程**：执行 `ps aux | grep "bot1/user-data" | grep renderer` 查看是否有 CPU 占用 >20% 且运行超过 10 分钟的 renderer 进程。如有，`kill <PID>` 清理
- [ ] 确保没有残留的 browser tab（残留 tab 会导致 renderer 卡死吃 CPU）

## 小红书养号（每次心跳轮换执行）

> 目的：保持账号活跃度，提升权重。每次心跳随机挑 **1-2 项** 执行，不要每次全做。
> **⚠️ 前置检查：先用 `check_login_status` 确认主站已登录。如果主站未登录，跳过全部养号任务，仅汇报登录状态即可。不要在后台重试或调用 get_login_qrcode。**

1. **刷首页 + 点赞**：先读 `skills/xiaohongshu-mcp/SKILL.md`，然后 `list_feeds` 浏览首页，挑 1-2 条与自己人设相关的内容点赞（`like_feed`）
2. **搜索 + 互动**：用 `search_feeds` 搜一个与自己领域相关的关键词，挑一条优质内容点赞或留下真诚评论（`post_comment_to_feed`）
3. **回复通知**：`get_notification_comments` 查看是否有新评论，有则用心回复 1-2 条

### 养号规则
- **评论要自然**：用自己的说话风格，不要模板化，像真人一样互动
- **不要刷量**：每次心跳最多点赞 2 个、评论 1 条
- **不评论竞品/敏感内容**
- **失败不重试**：MCP 调用失败就跳过，下次心跳再来

## 规则

- 深夜 24:00–08:00 不主动打扰
- 无事发生就 HEARTBEAT_OK

## 心跳汇报

**⚠️ 不要用 `send_message` 汇报心跳结果！** 发消息会唤醒对方 agent，对方回复又会唤醒你，造成无限循环。

心跳结果写入文件即可：
```bash
echo "$(date '+%Y-%m-%d %H:%M') HEARTBEAT_OK - 状态摘要" >> /home/rooot/.openclaw/workspace-bot1/HEARTBEAT_LOG.md
```

- 一切正常 → 写一行 HEARTBEAT_OK + 状态摘要
- 发现严重异常（如进程崩溃）→ 才用 `send_message` 通知 `bot_main`，且消息末尾加 `[NO_REPLY_NEEDED]`
