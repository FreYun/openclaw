# bot5（宣妈慢慢变富）

- **最后活动**：2026-03-27 08:57:35
- **会话 ID**：`026e112d-18f0-4d3c-bdb2-d86e3f639eb8`
- **来源**：? / ?

---

## 对话内容

**👤 用户**

[Thu 2026-03-26 20:55 GMT+8] [Conversation history with mag1 — last 3 messages, use get_message(message_id) for details]
  mag1 (2026-03-26T09:44:40.324Z): 圣上口谕：根据你自己的生图风格，用 image-gen-mcp 为自己生成一张头像，保存到你自己的 workspace 下。具体调用方式：npx mcporte…  [id:GMJthNsx6tcwINWXYUWw2]
  bot5 (2026-03-26T09:45:45.448Z): 头像已生成，保存到 `workspace/avatar.png` ✅  [id:YqDK_V-xNqISX9LCdSsFq]
  mag1 (2026-03-26T12:55:15.738Z): 小红书养号任务。Read skills/xhs-nurture/SKILL.md 加载完整流程，然后按流程执行（所有工具不传 account_id，身份由端口自…  [id:m3w6zNyZYeCPvljNAN9oF]

[MSG:m3w6zNyZYeCPvljNAN9oF] from=mag1: 小红书养号任务。Read skills/xhs-nurture/SKILL.md 加载完整流程，然后按流程执行（所有工具不传 account_id，身份由端口自动识别）。

---

**🤖 助手**

{
  "status": "error",
  "tool": "read",
  "error": "ENOENT: no such file or directory, access '/home/rooot/.openclaw/workspace-bot5/skills/xhs-nurture/SKILL.md'"
}

---

**🤖 助手**

(no output)

---

**🤖 助手**

/home/rooot/.openclaw/workspace-bot5/skills
/home/rooot/.openclaw/workspace-bot5/skills/gold-tracker
/home/rooot/.openclaw/workspace-bot5/skills/xuanma-style
/home/rooot/.openclaw/workspace-bot5/skills/xuanma-cover

---

**🤖 助手**

总计 84
drwxrwxr-x  2 rooot rooot 4096  3月 26 17:41 .
drwxr-xr-x 28 rooot rooot 4096  3月 26 14:44 ..
-rw-rw-r--  1 rooot rooot 2486  3月 23 16:03 发帖前必读.md
-rw-rw-r--  1 rooot rooot 1621  3月 23 15:27 合规速查.md
-rw-rw-r--  1 rooot rooot 9955  3月 23 18:10 内容策划.md
-rw-rw-r--  1 rooot rooot 6856  3月 23 18:10 素材积累.md
-rw-rw-r--  1 rooot rooot 5532  3月 23 18:10 投稿发布.md
-rw-rw-r--  1 rooot rooot 2069  3月 26 17:41 养号互动.md
-rw-rw-r--  1 rooot rooot 6535  3月 23 16:51 extract_image_text.py
-rw-r--r--  1 rooot rooot 5939  3月 26 17:25 mcp-tools.md
-rw-rw-r--  1 rooot rooot 1330  3月 26 09:14 skill.json
-rw-rw-r--  1 rooot rooot 2833  3月 23 16:00 SKILL.md
-rwxrwxr-x  1 rooot rooot 8630  3月 26 17:41 submit-to-publisher.sh

---

**🤖 助手**

找到了 `养号互动.md`，读它：

---

**🤖 助手**

# 小红书养号互动流程

## 前置检查

1. **Read `skills/xhs-op/mcp-tools.md`** 加载 MCP 工具用法
2. **检查登录状态**：`check_login_status()`
   - 未登录 → 回复「botN 未登录，跳过」，**不重试、不报警、不调用 get_login_qrcode**
   - 已登录 → 继续执行

## 执行流程

### 1. 搜索帖子

用 `search_feeds(keyword: '关键词')` 搜索与自己人设相关的内容。

**关键词选择**：从自己擅长的领域随机选 1 个，例如：
- 金融类：研报解读、基金定投、A股分析、财报分析、投资笔记
- 科技类：AI算力、半导体、存储芯片、产业链
- 生活类：理财心得、黄金投资、消费复苏
- 其他：根据自己 IDENTITY.md 的定位选取

### 2. 点赞（随机 1-5 篇）

从搜索结果中随机选 1-5 篇优质帖子，逐个点赞：
```
like_feed(feed_id: '...', xsec_token: '...')
sleep <随机1-10秒>
```
**每次操作后 `sleep` 随机 1-10 秒**（不要固定间隔，模拟真人节奏）

### 3. 评论（随机 1-3 篇）

随机选 1-3 篇帖子发表评论：
```
post_comment_to_feed(feed_id: '...', xsec_token: '...', content: '评论内容')
sleep <随机1-10秒>
```

### 4. 查看通知（可选）

`get_notification_comments()` 查看新评论，有则回复 1-2 条。

## 评论铁律

- **用自己的人设说话**，不要模板化（禁止"写得好""学到了""干货满满"）
- **要有信息量**：补充数据、提出观点、分享经验，20-50 字为宜
- **不打广告、不引流、不荐股、不预测涨跌**
- **不评论竞品/敏感内容**
- 每条评论要基于帖子实际内容，像真人互动

## 工具注意事项

- **所有工具都不传 `account_id`**，身份由端口自动识别（传了会报错）
- 失败不重试，跳过即可

## 汇报

完成后用 `send_messa

_（内容过长已截断）_

---

**🤖 助手**

---
name: xiaohongshu-mcp
description: Operate Xiaohongshu (小红书) via MCP tools — login, browse feeds, search, comment, reply, like/unlike, favorite/unfavorite, manage notes, view notifications, reply from notification page, and view creator home stats. Use when the user asks to 看通知、回复评论、搜索笔记、点赞收藏、删帖、置顶、查账号信息, or any Xiaohongshu browsing/interaction operation. **发布内容不走此 skill，走 submit-to-publisher。**
---

# Xiaohongshu MCP Skill（运营版）

> 本 skill 涵盖**浏览、搜索、互动、通知、笔记管理**等运营操作。
> **发布笔记请读 `skills/submit-to-publisher/SKILL.md`，不在此 skill 范围内。**

## ⚠️ 最重要的规则：不传 account_id

**所有工具都不需要传 `account_id`。** 每个 bot 通过 mcporter.json 中的 URL path 自动识别身份。

传 `account_id` 会报错 `unexpected additional properties ["account_id"]`。

唯一例外：`publish_content` 的 `account_id` 是可选参数，一般也不需要传。

---

## Step -1: 确认服务在运行（每次使用前先检查）

```bash
curl -s http://localhost:18060/health
```

- 返回 `{"success":true,...}` → 服务正常，直接使用
- 连接失败 / 无响应 → **不要自行启动服务**，向研究部报告

---

## Step 0: 登录（首次或 cookie 失效时）

小红书有**两个独立的登录体系**，必须分别登录：
- **主

_（内容过长已截断）_

---

**🤖 助手**

好，流程清楚了。先检查登录状态，然后按步骤执行养号。

---

**🤖 助手**

账号: xiaohongshu-mcp
主站: ❌ 未登录
创作者平台: ❌ 未登录

请使用 get_both_login_qrcodes 同时获取两张二维码登录。

---

**🤖 助手**

未登录，按流程回复研究部。

---

**🤖 助手**

{
  "message_id": "Ax5x6vOoQc8al0XtB4SOD",
  "routed_to": "mag1",
  "route_kind": "deliver_external",
  "agent_notified": false,
  "status": "delivered"
}

---

**🤖 助手**

NO_REPLY

---

**👤 用户**

[Fri 2026-03-27 08:55 GMT+8] [Conversation history with mag1 — last 5 messages, use get_message(message_id) for details]
  mag1 (2026-03-26T09:44:40.324Z): 圣上口谕：根据你自己的生图风格，用 image-gen-mcp 为自己生成一张头像，保存到你自己的 workspace 下。具体调用方式：npx mcporte…  [id:GMJthNsx6tcwINWXYUWw2]
  bot5 (2026-03-26T09:45:45.448Z): 头像已生成，保存到 `workspace/avatar.png` ✅  [id:YqDK_V-xNqISX9LCdSsFq]
  mag1 (2026-03-26T12:55:15.738Z): 小红书养号任务。Read skills/xhs-nurture/SKILL.md 加载完整流程，然后按流程执行（所有工具不传 account_id，身份由端口自…  [id:m3w6zNyZYeCPvljNAN9oF]
  bot5 (2026-03-26T12:55:46.250Z): bot5 小红书养号任务启动，但当前**主站和创作者平台都未登录**，无法执行互动操作。  [id:Ax5x6vOoQc8al0XtB4SOD]
  mag1 (2026-03-27T00:55:15.374Z): 小红书养号任务。Read skills/xhs-nurture/SKILL.md 加载完整流程，然后按流程执行（所有工具不传 account_id，身份由端口自…  [id:9FSQz3fnZtnQvDYcGaxBZ]

[MSG:9FSQz3fnZtnQvDYcGaxBZ] from=mag1: 小红书养号任务。Read skills/xhs-nurture/SKILL.md 加载完整流程，然后按流程执行（所有工具不传 account_id，身份由端口自动识别）。

---

**🤖 助手**

上次的养号文件已读过，直接检查登录状态并执行。

---

**🤖 助手**

账号: xiaohongshu-mcp
主站: ✅ 已登录
创作者平台: ✅ 已登录

---

**🤖 助手**

已登录，开始养号。先搜索黄金投资相关帖子：

---

**🤖 助手**

Command still running (session marine-lobster, pid 3321597). Use process (list/poll/log/write/kill/clear/remove) for follow-up.

---

**🤖 助手**

(no new output)

Process exited with signal SIGTERM.

---

**🤖 助手**

(no output recorded)

---

**🤖 助手**

超时了，换个关键词试试：

---

**🤖 助手**

Command still running (session tide-otter, pid 3323911). Use process (list/poll/log/write/kill/clear/remove) for follow-up.

---

**🤖 助手**

(no new output)

Process exited with signal SIGTERM.

---

**🤖 助手**

搜索超时，试试直接浏览信息流：

---

**🤖 助手**

获取Feeds列表失败: 没有捕获到 feeds 数据

---

**🤖 助手**

Command still running (session delta-crustacean, pid 3326957). Use process (list/poll/log/write/kill/clear/remove) for follow-up.

---

**🤖 助手**

(no new output)

Process exited with signal SIGTERM.

---

**🤖 助手**

小红书 MCP 搜索功能持续超时。向研究部汇报情况。

---

**🤖 助手**

{
  "message_id": "udj-YzWEjSS-9aZLg0yRl",
  "routed_to": "mag1",
  "route_kind": "deliver_external",
  "agent_notified": false,
  "status": "delivered"
}

---

**🤖 助手**

NO_REPLY

---
