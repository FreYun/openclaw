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

**其余所有工具（登录、浏览、搜索、笔记管理、通知等）仍需传 `account_id: "botX"`。**

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
- **主站**（`web_session`）：用于浏览、搜索、点赞、评论等
- **创作者平台**（`galaxy_creator_session_id`）：用于发布笔记、查看数据、管理账号

Chrome profile 自动持久化 cookies，服务重启后无需重新登录。

**先检查两个平台的登录状态：**

```bash
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'bot')"
```

根据结果按以下情况处理：

### 情况 A：两个平台都未登录 → 用 get_both_login_qrcodes 同时获取两张二维码

**必须用此工具，不要分开调用**（分开调用会锁冲突超时）：

```bash
npx mcporter call "xiaohongshu-mcp.get_both_login_qrcodes(account_id: 'bot')"
```

工具会同时返回两张二维码图片并保存至 media 文件夹。发送时：

```
message(action="send", message="需要登录两个平台，请依次扫码：
1️⃣ 小红书主站", media="/home/rooot/.openclaw/media/xhs-qr-bot.png")
message(action="send", message="2️⃣ 小红书创作者平台", media="/home/rooot/.openclaw/media/xhs-creator-qr-bot.png")
```

### 情况 B：仅主站未登录 → 获取主站二维码

```bash
npx mcporter call "xiaohongshu-mcp.get_login_qrcode(account_id: 'bot')"
```

```
message(action="send", message="请用小红书 App 扫码登录主站 👇", media="/home/rooot/.openclaw/media/xhs-qr-bot.png")
```

### 情况 C：仅创作者平台未登录 → 获取创作者平台二维码

```bash
npx mcporter call "xiaohongshu-mcp.get_creator_login_qrcode(account_id: 'bot')"
```

```
message(action="send", message="请用小红书 App 扫码登录创作者平台 👇", media="/home/rooot/.openclaw/media/xhs-creator-qr-bot.png")
```

### 重置登录

```bash
npx mcporter call "xiaohongshu-mcp.delete_cookies(account_id: 'bot')"
```

---

## Calling Convention

**管理/浏览类工具** 需传 `account_id`：

```bash
npx mcporter call "xiaohongshu-mcp.list_notes(account_id: 'botX')"
npx mcporter call "xiaohongshu-mcp.search_feeds(account_id: 'botX', keyword: '黄金')"
```

**互动类工具**（like_feed、post_comment_to_feed、reply_comment_in_feed、favorite_feed）**不传 account_id**：

```bash
npx mcporter call "xiaohongshu-mcp.like_feed(feed_id: '...', xsec_token: '...')"
npx mcporter call "xiaohongshu-mcp.post_comment_to_feed(feed_id: '...', xsec_token: '...', content: '评论内容')"
```

---

## Available Tools

### Authentication
| Tool | Description |
|------|-------------|
| `check_login_status` | 检查登录状态（分别报告主站 + 创作者平台）|
| `get_login_qrcode` | 获取主站登录二维码（自动保存 `/home/rooot/.openclaw/media/xhs-qr-botX.png`）|
| `get_both_login_qrcodes` | 同时获取主站 + 创作者平台二维码（两个都未登录时用）|
| `get_creator_login_qrcode` | 获取创作者平台登录二维码（自动保存 `/home/rooot/.openclaw/media/xhs-creator-qr-botX.png`）|
| `delete_cookies` | 重置登录状态 |

### Browse & Search
| Tool | Key Parameters |
|------|----------------|
| `list_feeds` | — |
| `search_feeds` | `keyword`, optional `filters` |
| `get_feed_detail` | `feed_id`, `xsec_token` |
| `user_profile` | `user_id`, `xsec_token` |

### Creator Stats
| Tool | Description |
|------|-------------|
| `get_creator_home` | 获取创作者后台首页：昵称、账号号码、关注/粉丝/获赞收藏数 |

### Note Management
| Tool | Key Parameters |
|------|----------------|
| `list_notes` | — 返回笔记列表，含👁浏览/💬评论/❤️点赞/⭐收藏/🔄转发数据 |
| `manage_note` | `feed_id`, `action`（delete/pin）|

### Social Interactions
| Tool | Key Parameters |
|------|----------------|
| `post_comment_to_feed` | `feed_id`, `xsec_token`, `content` |
| `reply_comment_in_feed` | `feed_id`, `xsec_token`, `comment_id`, `content` |
| `like_feed` | `feed_id`, `xsec_token`; optional: `unlike: true`（取消点赞）|
| `favorite_feed` | `feed_id`, `xsec_token`; optional: `unfavorite: true`（取消收藏）|

### Notifications
| Tool | Key Parameters |
|------|----------------|
| `get_notification_comments` | — |
| `reply_notification_comment` | `comment_index`（0-based）, `content` |

---

## Important Notes

- **`account_id: "botX"`**：管理/浏览类工具必填，互动类工具（like/comment/reply/favorite）不传
- **`feed_id` 和 `xsec_token`** 只能从 feed 列表获取，不要编造
- **通知回复** 用 `comment_index`（从 0 开始），必须先 `get_notification_comments`
- **删帖前** 先 `list_notes` 获取 feed_id，再 `manage_note` 操作
- **点赞/收藏** 默认执行操作，传 `unlike: true` 或 `unfavorite: true` 可取消
