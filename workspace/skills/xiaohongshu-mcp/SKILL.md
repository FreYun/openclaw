---
name: xiaohongshu-mcp
description: Operate Xiaohongshu (小红书) via MCP tools — login, browse feeds, search, publish image/video/longform posts, comment, reply, like, favorite, view notifications, and reply from notification page. Use when the user asks to 发小红书、写长文、看通知、回复评论、搜索笔记、点赞收藏, or any Xiaohongshu content operation. **IMPORTANT: Always prefer MCP over browser automation for Xiaohongshu tasks. Using browser requires user approval.**
---

# Xiaohongshu MCP Skill

Interact with Xiaohongshu (小红书) through the `xiaohongshu-mcp` MCP server. The server provides 16 tools for login, content browsing, publishing, and social interactions.

## ⚠️ 优先使用 MCP

**所有小红书相关操作一律优先使用 MCP 工具。**

使用浏览器 (browser tool) 操作小红书需要用户审批，除非 MCP 不可用或用户明确要求，否则不要使用浏览器。

## Calling Convention

使用 `npx mcporter call` 调用 MCP 工具：

```bash
# 基本调用
npx mcporter call xiaohongshu-mcp.<tool_name> <param>=<value>

# 数组参数用 function-call 语法
npx mcporter call "xiaohongshu-mcp.publish_content(title: '标题', content: '内容', images: ['url1', 'url2'], visibility: '仅自己可见')"
```

## Prerequisites

The MCP server must be running at `http://localhost:18060/mcp` before calling any tool. If a tool call fails with a connection error, remind the user to start the server (from the xiaohongshu-mcp project folder so the server can find `cookies.json`).

---

## Step 0: Login (Required First Time)

The server uses cookie-based authentication. If cookies don't exist or have expired, you must log in first.

### 0.1 Check Login Status

Call `check_login_status`. If `is_logged_in` is `true`, skip to the tool you need.

### 0.2 Get QR Code and Save (Use the Script)

If not logged in, **run the automation script** in this skill folder. It requests the QR code from the MCP server and saves it as `qrcode.png` in the same folder.

From this skill directory:

```bash
cd xiaohongshu-mcp
python save_qrcode.py
```

Optional: custom server URL or output path:

```bash
python save_qrcode.py --url http://localhost:18060
python save_qrcode.py -o path/to/qrcode.png
```

Requires: `pip install requests`. The saved file is `qrcode.png` in this skill folder.

Then tell the user: **"QR code saved to this skill folder as `qrcode.png`. Open it and scan with the Xiaohongshu app, then confirm login on your phone."**

### 0.3 Wait and Verify

After the user confirms they scanned, wait 10-15 seconds, then call `check_login_status` again. The server saves cookies automatically upon successful login. The QR code expires in 4 minutes.

### 0.4 Delete Cookies (Reset Login)

Call `delete_cookies` to clear saved login and start fresh.

---

## Available Tools (16 Total)

### Authentication

| Tool | Description | Parameters |
|------|-------------|------------|
| `check_login_status` | Check if logged in | None |
| `get_login_qrcode` | Get login QR code (Base64 image) | None |
| `delete_cookies` | Reset login state | None |

### Browse & Search

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_feeds` | Get homepage feed list | None |
| `search_feeds` | Search content | `keyword`, optional `filters` (sort_by, note_type, publish_time) |
| `get_feed_detail` | Get note detail + comments | `feed_id`, `xsec_token`, optional `load_all_comments` |
| `user_profile` | Get user profile + notes | `user_id`, `xsec_token` |

### Publish

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `publish_content` | Publish image post | `title`, `content`, `images` (URLs or local paths), optional `tags`, `visibility`, `schedule_at` |
| `publish_with_video` | Publish video post | `title`, `content`, `video` (local path), optional `tags`, `visibility` |
| `publish_longform` | Publish long-form article | `title`, `content`, optional `desc` |

### Social Interactions

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `post_comment_to_feed` | Comment on a note | `feed_id`, `xsec_token`, `content` |
| `reply_comment_in_feed` | Reply to a specific comment | `feed_id`, `xsec_token`, `comment_id` or `user_id`, `content` |
| `like_feed` | Like / unlike a note | `feed_id`, `xsec_token`, optional `unlike` |
| `favorite_feed` | Favorite / unfavorite a note | `feed_id`, `xsec_token`, optional `unfavorite` |

### Notifications

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_notification_comments` | View comments & mentions on your notes | None |
| `reply_notification_comment` | Reply to a comment from notification page | `comment_index` (0-based), `content` |

---

## Common Workflows

### Browse and Interact

1. `list_feeds` → pick a note → `get_feed_detail` (with `feed_id` + `xsec_token` from the feed list)
2. Read the detail, then `like_feed`, `favorite_feed`, or `post_comment_to_feed`

### Search and Read

1. `search_feeds` with keyword → get results
2. `get_feed_detail` on the one the user wants to read

### Publish an Image Post

1. Prepare title, content, and image URLs/paths
2. `publish_content` with `title`, `content`, `images`
3. Optional: set `visibility` to `"仅自己可见"` for testing

### Publish a Long-Form Article

1. `publish_longform` with `title` and `content`
2. Optional: provide `desc` (max 1000 chars) for the publish page description; if omitted, the first 800 chars of content are used
3. The server handles the full flow: enter editor → fill title → fill body → one-click layout → select template → next step → fill description → publish
4. Takes ~50 seconds to complete

### Check and Reply to Comments (Daily Operations)

1. `get_notification_comments` → returns a list with `index`, `username`, `action`, `content`
2. Read through the comments, decide which to reply
3. `reply_notification_comment` with `comment_index` (from the list) and your `content`
4. Repeat for each comment you want to reply to

### Reply to a Specific Comment in a Note

1. `get_feed_detail` with `load_all_comments: true` to load all comments
2. Find the target comment's `id` and `userInfo.userId`
3. `reply_comment_in_feed` with `feed_id`, `xsec_token`, `comment_id`, `user_id`, `content`

---

## Important Notes

- **`feed_id` and `xsec_token`** are always obtained from feed lists (`list_feeds`, `search_feeds`, or `get_feed_detail`). Never fabricate them.
- **Title length limit**: max 20 Chinese characters for image/video posts. Longform titles have no strict limit but keep them concise.
- **Image posts require at least 1 image**. Supports HTTP URLs (auto-downloaded) and local file paths.
- **Longform publish** takes ~50s due to multi-step browser automation. Be patient.
- **Notification reply** uses `comment_index` (0-based) from `get_notification_comments`. Always fetch the list first.
- **Visibility options**: `"公开可见"` (default), `"仅自己可见"`, `"仅互关好友可见"` — available for image and video posts.
- All tools use headless browser automation (go-rod). If something fails, retry once — page structure may have changed or loaded slowly.
