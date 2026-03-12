---
name: xiaohongshu-mcp
description: Operate Xiaohongshu (小红书) via MCP tools — login, browse feeds, search, publish image/video/longform posts (with text-to-image/文字配图, scheduled publishing/定时发布, original declaration/原创声明, product linking/带货商品), comment, reply, like/unlike, favorite/unfavorite, manage notes, view notifications, reply from notification page, and view creator home stats. Use when the user asks to 发小红书、写长文、文字生图、定时发布、看通知、回复评论、搜索笔记、点赞收藏、删帖、置顶、查账号信息, or any Xiaohongshu content operation. **IMPORTANT: Always prefer MCP over browser automation for Xiaohongshu tasks.**
---

# Xiaohongshu MCP Skill

## ⚠️ 最重要的规则：始终传 account_id

**你是 bot3，调用所有 xiaohongshu-mcp 工具时必须传 `account_id: "bot3"`，不可省略。**

---

## Step -1: 确认服务在运行（每次使用前先检查）

```bash
curl -s http://localhost:18060/health
```

- 返回 `{"success":true,...}` → 服务正常，直接使用
- 连接失败 / 无响应 → 服务未启动，执行下方命令启动

### 启动服务

```bash
nohup /home/rooot/MCP/xiaohongshu-mcp/xiaohongshu-mcp -headless=true -port=:18060 > /tmp/xiaohongshu-mcp.log 2>&1 &
```

启动后等 2 秒再确认：

```bash
sleep 2 && curl -s http://localhost:18060/health
```

### 查看日志 / 停止服务

```bash
tail -f /tmp/xiaohongshu-mcp.log
pkill -f "xhs-mcp"
```

---

## Step 0: 登录（首次或 cookie 失效时）

小红书有**两个独立的登录体系**，必须分别登录：
- **主站**（`web_session`）：用于浏览、搜索、点赞、评论等
- **创作者平台**（`galaxy_creator_session_id`）：用于发布笔记、查看数据、管理账号

Chrome profile 自动持久化 cookies，服务重启后无需重新登录。

**先检查两个平台的登录状态：**

```bash
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'bot3')"
```

根据结果按以下情况处理：

### 情况 A：两个平台都未登录 → 用 get_both_login_qrcodes 同时获取两张二维码

**必须用此工具，不要分开调用**（分开调用会锁冲突超时）：

```bash
npx mcporter call "xiaohongshu-mcp.get_both_login_qrcodes(account_id: 'bot3')"
```

工具会同时返回两张二维码图片并保存至 media 文件夹。发送时：

```
message(action="send", message="需要登录两个平台，请依次扫码：
1️⃣ 小红书主站", media="/home/rooot/.openclaw/media/xhs-qr-bot3.png")
message(action="send", message="2️⃣ 小红书创作者平台", media="/home/rooot/.openclaw/media/xhs-creator-qr-bot3.png")
```

### 情况 B：仅主站未登录 → 获取主站二维码

```bash
npx mcporter call "xiaohongshu-mcp.get_login_qrcode(account_id: 'bot3')"
```

```
message(action="send", message="请用小红书 App 扫码登录主站 👇", media="/home/rooot/.openclaw/media/xhs-qr-bot3.png")
```

### 情况 C：仅创作者平台未登录 → 获取创作者平台二维码

```bash
npx mcporter call "xiaohongshu-mcp.get_creator_login_qrcode(account_id: 'bot3')"
```

```
message(action="send", message="请用小红书 App 扫码登录创作者平台 👇", media="/home/rooot/.openclaw/media/xhs-creator-qr-bot3.png")
```

### 重置登录

```bash
npx mcporter call "xiaohongshu-mcp.delete_cookies(account_id: 'bot3')"
```

---

## Calling Convention

所有工具均需传 `account_id: "bot3"`：

```bash
npx mcporter call "xiaohongshu-mcp.list_notes(account_id: 'bot3')"
npx mcporter call "xiaohongshu-mcp.publish_content(account_id: 'bot3', title: '标题', content: '内容', images: ['url'])"
```

---

## Available Tools (20 Total)

### Authentication
| Tool | Description |
|------|-------------|
| `check_login_status` | 检查登录状态（分别报告主站 + 创作者平台）|
| `get_login_qrcode` | 获取主站登录二维码（自动保存 `/home/rooot/.openclaw/media/xhs-qr-bot3.png`）|
| `get_creator_login_qrcode` | 获取创作者平台登录二维码（自动保存 `/home/rooot/.openclaw/media/xhs-creator-qr-bot3.png`）|
| `delete_cookies` | 重置登录状态 |

### Creator
| Tool | Description |
|------|-------------|
| `get_creator_home` | 获取创作者后台首页：昵称、账号号码、关注/粉丝/获赞收藏数 |

### Browse & Search
| Tool | Key Parameters |
|------|----------------|
| `list_feeds` | — |
| `search_feeds` | `keyword`, optional `filters` |
| `get_feed_detail` | `feed_id`, `xsec_token` |
| `user_profile` | `user_id`, `xsec_token` |

### Publish
| Tool | Key Parameters |
|------|----------------|
| `publish_content` | `title`, `content`; optional: `images`, `text_to_image`, `text_content`, `tags`, `schedule_at`, `is_original`, `visibility`, `products` |
| `publish_with_video` | `title`, `content`, `video`（本地路径）; optional: `tags`, `schedule_at`, `visibility`, `products` |
| `publish_longform` | `title`, `content`; optional: `desc`, `tags`, `visibility` |

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

## publish_content 参数详解

| 参数 | 类型 | 说明 |
|------|------|------|
| `title` | string（必填）| 标题，≤20个中文字 |
| `content` | string（必填）| 正文，≤1000字 |
| `images` | array | 图片列表（HTTP URL 或本地绝对路径）。**文字配图模式时不填** |
| `text_to_image` | bool | **文字配图模式**：设为 `true` 时无需提供图片，由小红书 AI 根据文字自动生成配图 |
| `text_content` | string | 文字配图的卡片文字（可选），不填则取正文前 100 字 |
| `tags` | array | 话题标签，如 `["美食", "旅行"]` |
| `schedule_at` | string | 定时发布时间，ISO8601 格式（如 `"2025-12-01T10:00:00+08:00"`），支持 1 小时至 14 天内 |
| `is_original` | bool | 是否声明原创，默认 false |
| `visibility` | string | 可见范围：`"公开可见"`（默认）、`"仅自己可见"`、`"仅互关好友可见"` |
| `products` | array | 带货商品关键词或商品ID，如 `["面膜", "防晒霜SPF50"]`，需账号已开通商品功能 |

### 文字配图示例

```bash
npx mcporter call "xiaohongshu-mcp.publish_content(account_id: 'bot3', title: '春日出游指南', content: '...正文...', text_to_image: true)"
```

### 定时发布示例

```bash
npx mcporter call "xiaohongshu-mcp.publish_content(account_id: 'bot3', title: '..', content: '..', images: ['/path/img.jpg'], schedule_at: '2025-12-01T10:00:00+08:00')"
```

---

## Important Notes

- **`account_id: "bot3"` 每次必填**
- **`feed_id` 和 `xsec_token`** 只能从 feed 列表获取，不要编造
- **标题限制**：最多 20 个中文字
- **图文模式** 至少 1 张图片，支持 HTTP URL 和本地绝对路径；**文字配图模式**（`text_to_image: true`）无需图片
- **文字配图** 由小红书平台 AI 生成配图，约需 5 秒，仅支持无头模式直接发布
- **长文发布** 耗时约 50 秒；`desc` 为发布页简介描述（≤1000字）
- **通知回复** 用 `comment_index`（从 0 开始），必须先 `get_notification_comments`
- **可见性**：`"公开可见"`（默认）、`"仅自己可见"`、`"仅互关好友可见"`
- **删帖前** 先 `list_notes` 获取 feed_id，再 `manage_note` 操作
- **点赞/收藏** 默认执行操作，传 `unlike: true` 或 `unfavorite: true` 可取消
- **带货商品** 需账号已开通商品功能，填商品名称或ID，系统自动匹配第一个结果
