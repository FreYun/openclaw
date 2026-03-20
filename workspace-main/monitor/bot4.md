# bot4（研报搬运工阿泽）

- **最后活动**：2026-03-20 11:06:34
- **会话 ID**：`560e28a1-fb69-48bb-a71b-c778d796326b`
- **来源**：feishu / direct

---

## 对话内容

**👤 用户**

System: [2026-03-20 11:06:34 GMT+8] Feishu[bot4] DM from ou_ea254c14c4dc1c4fefb116270f06c1b8: 发送登陆二维码

Conversation info (untrusted metadata):
```json
{
  "timestamp": "Fri 2026-03-20 11:06 GMT+8"
}
```

[message_id: om_x100b54ffd542a0a8b21803c4e920315]
顾云峰: 发送登陆二维码

---

**🤖 助手**

---
name: xiaohongshu-mcp
description: Operate Xiaohongshu (小红书) via MCP tools — login, browse feeds, search, comment, reply, like/unlike, favorite/unfavorite, manage notes, view notifications, reply from notification page, and view creator home stats. Use when the user asks to 看通知、回复评论、搜索笔记、点赞收藏、删帖、置顶、查账号信息, or any Xiaohongshu browsing/interaction operation. **发布内容不走此 skill，走 submit-to-publisher。**
---

# Xiaohongshu MCP Skill（运营版）

> 本 skill 涵盖**浏览、搜索、互动、通知、笔记管理**等运营操作。
> **发布笔记请读 `skills/submit-to-publisher/SKILL.md`，不在此 skill 范围内。**

## ⚠️ 最重要的规则：account_id 传参说明

**大部分工具需要传 `account_id: "botX"`，但以下 4 个互动工具已改为端口自动识别，不再接受 account_id 参数：**

| 不传 account_id 的工具 | 参数 |
|----------------------|------|
| `like_feed` | `feed_id`, `xsec_token`, 可选 `unlike: true` |
| `post_comment_to_feed` | `feed_id`, `xsec_token`, `content` |
| `reply_comment_in_feed` | `feed_id`, `xsec_token`, `comment_id`, `content` |
| `favorite_feed` | `feed_id`, `xsec_token`, 可选 `unfavorite: true` |

**其余所有工具（登录、浏览、搜索

_（内容过长已截断）_

---
