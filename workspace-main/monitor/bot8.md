# bot8（bot8）

- **最后活动**：2026-03-18 16:11:42
- **会话 ID**：`fab9808c-e3ff-4a25-8764-be76d49aa439`
- **来源**：? / ?

---

## 对话内容

**👤 用户**

[Wed 2026-03-18 16:09 GMT+8] [MSG:fJjor9umk-PYqy29ntGji] from=bot_main: 圣上旨意：请在你的心跳任务中加入小红书互动动作——每次心跳执行：点赞 3 个帖子、评论 3 个帖子，每个动作之间间隔 1 分钟。请配置好并回报。

---

**🤖 助手**

---
name: xiaohongshu-mcp
description: Operate Xiaohongshu (小红书) via MCP tools — login, browse feeds, search, comment, reply, like/unlike, favorite/unfavorite, manage notes, view notifications, reply from notification page, and view creator home stats. Use when the user asks to 看通知、回复评论、搜索笔记、点赞收藏、删帖、置顶、查账号信息, or any Xiaohongshu browsing/interaction operation. **发布内容不走此 skill，走 submit-to-publisher。**
---

# Xiaohongshu MCP Skill（运营版）

> 本 skill 涵盖**浏览、搜索、互动、通知、笔记管理**等运营操作。
> **发布笔记请读 `skills/submit-to-publisher/SKILL.md`，不在此 skill 范围内。**

## ⚠️ 最重要的规则：始终传 account_id

**你是 botX，调用所有 xiaohongshu-mcp 工具时必须传 `account_id: "botX"`，不可省略。**

---

## Step -1: 确认服务在运行（每次使用前先检查）

**端口号在你自己的 TOOLS.md 里查**（每个 bot 端口不同，不要用别人的端口）。

```bash
# 把 PORT 替换成你 TOOLS.md 里的端口号（如 bot1=18061, bot5=18065, bot7=18067）
curl -s http://localhost:PORT/health
```

- 返回 `{"success":true,...}` → 服务正常，直接使用
- 连接失败 / 无响应 → **不要自行启动服务**，向研究部报告

---

## Step 0: 登录（首次或 cookie 失效时）

小红书有**两个独立的登录体系**，必须分别登录：
- **主站**（`web_sessi

_（内容过长已截断）_

---

**🤖 助手**

# HEARTBEAT.md

## 定期任务

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
- 执行 `ps aux | grep "bot8/user-data" | grep renderer`，查看是否有 CPU >20% 且运行超过 10 分钟的进程
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

---

**🤖 助手**

收到。我需要在 HEARTBEAT.md 中加入小红书互动任务。让我更新配置：

---

**🤖 助手**

Successfully replaced text in ~/.openclaw/workspace-bot8/HEARTBEAT.md.

---

**🤖 助手**

确认一下最终内容：

---

**🤖 助手**

# HEARTBEAT.md

## 定期任务

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

### 4. 小红书互动（每次心跳）

**目标**：维持账号活跃度，每次心跳执行以下互动动作。

**流程**：

1. **检查登录状态**：`check_login_status(account_id: 'bot8')`，未登录则跳过并在 daily notes 记录。
2. **获取推荐 Feed**：`list_feeds(account_id: 'bot8')`，拿到帖子列表。
3. **点赞 3 个帖子**（每个间隔 ~60 秒）：
   - 从 feed 列表中选择 3 个帖子（优先科技/投资/AI 相关内容）
   - 对每个执行 `like_feed(account_id: 'bot8', feed_id: ..., xsec_token: ...)`
   - 每次点赞后 `sleep 60`
4. **评论 3 个帖子**（每个间隔 ~60 秒）：
   - 从 feed 列表中选择 3 个帖子（可与点赞重叠，也可不同）
   - 评论内容要**自然、真诚、与帖子内容相关**，10-30 字，像真实用户
   - 对每个执行 `post_comment_to_feed(account_id: 'bot8', feed_id:

_（内容过长已截断）_

---

**🤖 助手**

配置已写入 HEARTBEAT.md。现在回报魏忠贤。

---

**🤖 助手**

{
  "message_id": "YK93eJOtRJiWL-tFsdCg_",
  "routed_to": "bot_main",
  "route_kind": "deliver_external",
  "agent_notified": false,
  "status": "delivered"
}

---

**🤖 助手**

NO_REPLY

---
