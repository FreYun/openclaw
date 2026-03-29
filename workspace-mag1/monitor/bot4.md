# bot4（研报搬运工阿泽）

- **最后活动**：2026-03-27 00:58:58
- **会话 ID**：`f79cb185-d4f8-49da-889e-f87a6902d1ab`
- **来源**：? / ?

---

## 对话内容

**👤 用户**

[Thu 2026-03-26 17:44 GMT+8] [Conversation history with mag1 — last 1 messages, use get_message(message_id) for details]
  mag1 (2026-03-26T09:44:40.305Z): 圣上口谕：根据你自己的生图风格，用 image-gen-mcp 为自己生成一张头像，保存到你自己的 workspace 下。具体调用方式：npx mcporte…  [id:ODIu2NWJAtPEecU3QfW4b]

[MSG:ODIu2NWJAtPEecU3QfW4b] from=mag1: 圣上口谕：根据你自己的生图风格，用 image-gen-mcp 为自己生成一张头像，保存到你自己的 workspace 下。具体调用方式：npx mcporter call 'image-gen-mcp.generate_image(style: "你的风格", content: "你的头像描述")'，生成后把图片复制到你的 workspace 目录。速办。

---

**🤖 助手**

{
  "status": "error",
  "tool": "read",
  "error": "ENOENT: no such file or directory, access '/home/rooot/.openclaw/workspace-bot4/skills/image-gen-mcp/SKILL.md'"
}

---

**🤖 助手**

Command still running (session plaid-glade, pid 322914). Use process (list/poll/log/write/kill/clear/remove) for follow-up.

---

**🤖 助手**

{
  "output_dir": "/tmp/image-gen/20260326_174451_一位理性的研报解读专家_戴着眼镜在看股票图表_背景有券商研报和_K_线图_专业且",
  "files": [
    "/tmp/image-gen/20260326_174451_一位理性的研报解读专家_戴着眼镜在看股票图表_背景有券商研报和_K_线图_专业且/001.png"
  ],
  "model": "mgg-9",
  "prompt": "Style: 扁平插画风\n\nContent: 一位理性的研报解读专家，戴着眼镜在看股票图表，背景有券商研报和 K 线图，专业且亲和力强\n\nImage size: 960x1280",
  "text_reply": "<think>\n**Reflecting on the Vision**\n\nI am now focusing on the image's overall style, specifically the flat illustration aesthetic, concentrating on clean lines, simple shapes, and solid color blocks. The subject matter involves an expert examining stock charts, the central figure needing a rational demeanor.\n\n\n **Conceptualizing the Scene**\n\nI am now designing the expert's characteristics and environment. I am planning a flat design featuring a woman in a professional but casual outfit, examining complex stock charts on a tablet. I intend to place her in a modern office setting.\n\n\n **Developing the Scene's Details**\n\nI am now focusing 

_（内容过长已截断）_

---

**🤖 助手**

(no output)

---

**🤖 助手**

{
  "message_id": "9lMR7eBB7L2TUydVLCbue",
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

[Fri 2026-03-27 00:55 GMT+8] [Conversation history with mag1 — last 3 messages, use get_message(message_id) for details]
  mag1 (2026-03-26T09:44:40.305Z): 圣上口谕：根据你自己的生图风格，用 image-gen-mcp 为自己生成一张头像，保存到你自己的 workspace 下。具体调用方式：npx mcporte…  [id:ODIu2NWJAtPEecU3QfW4b]
  bot4 (2026-03-26T09:45:33.158Z): 圣上，头像已生成完毕。  [id:9lMR7eBB7L2TUydVLCbue]
  mag1 (2026-03-26T16:55:12.769Z): 小红书养号任务。Read skills/xhs-nurture/SKILL.md 加载完整流程，然后按流程执行（所有工具不传 account_id，身份由端口自…  [id:AUQPErEeztRhi1JyelRDO]

[MSG:AUQPErEeztRhi1JyelRDO] from=mag1: 小红书养号任务。Read skills/xhs-nurture/SKILL.md 加载完整流程，然后按流程执行（所有工具不传 account_id，身份由端口自动识别）。

---

**🤖 助手**

{
  "status": "error",
  "tool": "read",
  "error": "ENOENT: no such file or directory, access '/home/rooot/.openclaw/workspace-bot4/skills/xhs-nurture/SKILL.md'"
}

---

**🤖 助手**

lrwxrwxrwx  1 rooot rooot   29  3月 23 14:08 xhs-op -> ../../workspace/skills/xhs-op

---

**🤖 助手**

---
name: xhs-op
description: >
  小红书全流程运营 Skill — 登录、浏览、互动、养号、选题策划、内容生成、投稿发布。
  一个 skill 覆盖小红书运营的全部能力。装备此 skill 即具备小红书平台运营资格。
---

# 小红书运营 Skill（xhs-op）

> 装备即生效，所有小红书操作以本文件为准。

## 子文档索引

按需读取，不必一次全读。

| 文档 | 何时读取 |
|------|----------|
| [mcp-tools.md](mcp-tools.md) | 需要调用 MCP 工具时（登录、浏览、搜索、互动、通知、笔记管理） |
| [发帖前必读.md](发帖前必读.md) | 每次发帖/回复评论前 |
| [合规速查.md](合规速查.md) | 帖子被印务局打回时 |
| [内容策划.md](内容策划.md) | 策划内容 / heartbeat 推荐选题时 |
| [素材积累.md](素材积累.md) | 定时巡逻 / 随手记录灵感时 |
| [养号互动.md](养号互动.md) | 养号任务触发时 |
| [投稿发布.md](投稿发布.md) | 内容确认后提交发布时 |

---

## 铁律

1. **发布必走印务局** — 通过 `submit-to-publisher` 脚本提交，绝不直接调用 `publish_content`。合规由印务局负责。
2. **不传 account_id** — 身份由端口自动识别，传了会报错。
3. **先检查登录** — 每次用 MCP 前先 `check_login_status()`。
4. **人设一致** — 内容符合 SOUL.md / CONTENT_STYLE.md，不暴露研究部。
5. **评论同等严格** — 不引流、不荐股、不提竞品平台。

---

## 发帖流程

### 写稿前

读 `memory/发帖记录.md` + `memory/写稿经验.md` + `CONTENT_STYLE.md`（如有），保证连续性。

### 两步发布

```
1. 写稿 → 按 CONTENT_STYLE.md 检查风格、排版、封面
2. 投稿 → Read 投稿发布.md，写文件到发布队列，通知印务局
```

- **印

_（内容过长已截断）_

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

账号: xiaohongshu-mcp
主站: ✅ 已登录
创作者平台: ✅ 已登录

---

**🤖 助手**

Command still running (session fresh-tidepool, pid 1823503). Use process (list/poll/log/write/kill/clear/remove) for follow-up.

---

**🤖 助手**

(no new output)

Process still running.

---

**🤖 助手**

[mcporter] xiaohongshu-mcp appears offline (Call to xiaohongshu-mcp.search_feeds timed out after 60000ms. Override MCPORTER_CALL_TIMEOUT or pass --timeout to adj…).
[mcporter] Call to xiaohongshu-mcp.search_feeds timed out after 60000ms. Override MCPORTER_CALL_TIMEOUT or pass --timeout to adjust.
Error: Call to xiaohongshu-mcp.search_feeds timed out after 60000ms. Override MCPORTER_CALL_TIMEOUT or pass --timeout to adjust.
    at attemptCall (file:///home/rooot/.npm-global/lib/node_modules/mcporter/dist/cli/call-command.js:250:19)
    at async handleCall (file:///home/rooot/.npm-global/lib/node_modules/mcporter/dist/cli/call-command.js:77:22)
    at async runCli (file:///home/rooot/.npm-global/lib/node_modules/mcporter/dist/cli.js:143:13)
    at async main (file:///home/rooot/.npm-global/lib/node_modules/mcporter/dist/cli.js:201:5)

Process exited with code 1.

---

**🤖 助手**

{"success":true,"data":{"account":"ai-report","service":"xiaohongshu-mcp","status":"healthy","timestamp":"now"},"message":"服务正常"}

---

**🤖 助手**

{
  "feeds": [
    {
      "xsecToken": "ABbCLHT5s3qlM3EnEPlnWhUFTWr2MQyMCaW7lj0jnouvY=",
      "id": "64ba3ad8000000001201a407",
      "modelType": "note",
      "noteCard": {
        "type": "normal",
        "displayTitle": "听说你很好奇封神训练营到底是怎么样的？",
        "user": {
          "userId": "63fb1f67000000001001c1d5",
          "nickname": "陈牧驰",
          "nickName": "陈牧驰",
          "avatar": "https://sns-avatar-qc.xhscdn.com/avatar/63fb22906c9e16b482ed6e09.jpg"
        },
        "interactInfo": {
          "liked": false,
          "likedCount": "2.6万",
          "sharedCount": "",
          "commentCount": "",
          "collectedCount": "",
          "collected": false
        },
        "cover": {
          "width": 1280,
          "height": 1705,
          "url": "",
          "fileId": "",
          "urlPre": "http://sns-webpic-qc.xhscdn.com/202603270056/db3277d5f8d185b959b528d57cf4f11c/1040g00830mphtm5q4c005ovr3tjk3gel64slj2o!nc_n_webp_prv_1",
          "urlDefault": "http://sns-

_（内容过长已截断）_

---

**🤖 助手**

Command still running (session nimble-summit, pid 1830520). Use process (list/poll/log/write/kill/clear/remove) for follow-up.

---

**🤖 助手**

(no new output)

Process still running.

---

**🤖 助手**

[mcporter] xiaohongshu-mcp appears offline (Call to xiaohongshu-mcp.like_feed timed out after 60000ms. Override MCPORTER_CALL_TIMEOUT or pass --timeout to adjust.).
[mcporter] Call to xiaohongshu-mcp.like_feed timed out after 60000ms. Override MCPORTER_CALL_TIMEOUT or pass --timeout to adjust.
Error: Call to xiaohongshu-mcp.like_feed timed out after 60000ms. Override MCPORTER_CALL_TIMEOUT or pass --timeout to adjust.
    at attemptCall (file:///home/rooot/.npm-global/lib/node_modules/mcporter/dist/cli/call-command.js:250:19)
    at async handleCall (file:///home/rooot/.npm-global/lib/node_modules/mcporter/dist/cli/call-command.js:77:22)
    at async runCli (file:///home/rooot/.npm-global/lib/node_modules/mcporter/dist/cli.js:143:13)
    at async main (file:///home/rooot/.npm-global/lib/node_modules/mcporter/dist/cli.js:201:5)

Process exited with code 1.

---

**🤖 助手**

null

---

**🤖 助手**

Command still running (session grand-otter, pid 1835662). Use process (list/poll/log/write/kill/clear/remove) for follow-up.

---

**🤖 助手**

TIMEOUT_OR_ERROR

Process exited with code 0.

---

**🤖 助手**

{
  "message_id": "C0iB_kedcmRsGjsg4SxNi",
  "status": "sent"
}

---

**🤖 助手**

NO_REPLY

---
