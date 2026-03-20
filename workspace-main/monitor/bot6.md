# bot6（bot6）

- **最后活动**：2026-03-20 10:52:37
- **会话 ID**：`2104c523-b346-452e-9c38-a1b52b13a4eb`
- **来源**：feishu / direct

---

## 对话内容

**👤 用户**

System: [2026-03-20 10:08:28 GMT+8] Feishu[bot6] DM from ou_074424f50af60a65b17f699a5d5ebfb5: /model glm-5-turbo
System: [2026-03-20 10:08:46 GMT+8] Feishu[bot6] DM from ou_074424f50af60a65b17f699a5d5ebfb5: 你现在去逛一下小红书 随便逛逛

Conversation info (untrusted metadata):
```json
{
  "timestamp": "Fri 2026-03-20 10:08 GMT+8"
}
```

[message_id: om_x100b54fe8c004894b3111ae0e1ece77]
邱海生: 你现在去逛一下小红书 随便逛逛

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

**🤖 助手**

{"success":true,"data":{"account":"ai-report","service":"xiaohongshu-mcp","status":"healthy","timestamp":"now"},"message":"服务正常"}

---

**🤖 助手**

服务正常，先看看首页推荐流。

---

**🤖 助手**

{
  "feeds": [
    {
      "xsecToken": "ABdAukYQdCY8A4FXe6ic2dHGnLIeNPOWTaOnClkziGHuE=",
      "id": "69a46708000000002602df46",
      "modelType": "note",
      "noteCard": {
        "type": "normal",
        "displayTitle": "抖音账号被封了，登陆不上去",
        "user": {
          "userId": "611cd6da0000000001006a89",
          "nickname": "YearN",
          "nickName": "YearN",
          "avatar": "https://sns-avatar-qc.xhscdn.com/avatar/611cd746f4ff0f5421ae46be.jpg"
        },
        "interactInfo": {
          "liked": false,
          "likedCount": "52",
          "sharedCount": "",
          "commentCount": "",
          "collectedCount": "",
          "collected": false
        },
        "cover": {
          "width": 1172,
          "height": 2532,
          "url": "",
          "fileId": "",
          "urlPre": "http://sns-webpic-qc.xhscdn.com/202603201008/bff19b87a4d9fee2182f66e1689c1d09/notes_pre_post/1040g3k031t67p73n5a105o8sqrd08qk9lon5gug!nc_n_webp_prv_1",
          "urlDefault": "

_（内容过长已截断）_

---

**👤 用户**

System: [2026-03-20 10:52:37 GMT+8] Feishu[bot6] DM from ou_074424f50af60a65b17f699a5d5ebfb5: 你在干嘛呀

Conversation info (untrusted metadata):
```json
{
  "timestamp": "Fri 2026-03-20 10:52 GMT+8"
}
```

[message_id: om_x100b54ff298c9488b27f8d8c4a8d0a9]
邱海生: 你在干嘛呀

---
