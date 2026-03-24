# 发布工具 API

> 印务局通过 `mcporter call` 调用对应 bot 的 MCP 服务执行发布。

## Calling Convention

```bash
# 服务名 = "xhs-" + account_id
npx mcporter call "xhs-bot5.publish_content(account_id: 'bot5', title: '...', ...)"
npx mcporter call "xhs-bot7.publish_longform(account_id: 'bot7', title: '...', ...)"
```

**超时必设**：`npx mcporter call --timeout 180000` + 在 exec 层面也设 `timeout: 180`。

---

## Publish Tools

| Tool | 适用场景 |
|------|---------|
| `publish_content` | 图文笔记（含文字配图）|
| `publish_with_video` | 视频笔记（本地视频文件）|
| `publish_longform` | 长文笔记（自动排版）|

---

## `publish_content` — 图文笔记

### 参数表

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `account_id` | string | ✓ | 账号 ID，如 `bot5` |
| `title` | string | ✓ | 标题（≤20 中文字）|
| `content` | string | ✓ | 图片下方的正文文字 |
| `images` | []string | 条件 | 图片 URL 或本地路径；`text_to_image=true` 时可不填 |
| `tags` | []string | — | 话题标签，如 `["黄金", "投资"]` |
| `schedule_at` | string | — | 定时发布，ISO8601，如 `2026-03-20T10:00:00+08:00` |
| `is_original` | bool | — | 是否声明原创 |
| `visibility` | string | — | `公开可见`（默认）/ `仅自己可见` / `仅互关好友可见` |
| `products` | []string | — | 带货商品关键词 |
| `text_to_image` | bool | — | `true` = 文字配图模式（自动生成图片）|
| `text_image` | string | — | 图片卡片上的文字（仅 `text_to_image=true` 时有效）；不填则用 `content` 前100字 |
| `image_style` | string | — | 图片风格：`基础`（默认）/ `光影` / `涂写` / `书摘` / `涂鸦` / `便签` / `边框` / `手写` / `几何` |

### 两种模式

**普通图文**（`text_to_image: false` 或不填）：
- `images` 必填（URL 或本地路径）
- `content` = 图片下方显示的正文
- `text_image` 忽略

**文字配图**（`text_to_image: true`）：
- `images` 可不填（小红书自动将文字生成图片）
- `text_image` = 图片卡片上的文字（每张卡片用 `\n\n` 分隔多张）
- `content` = 图片下方的正文
- `image_style` 控制图片风格

### Tag 规则

- 话题标签**只通过 `tags` 参数**传，不要在 `content` 或 `text_image` 中写 `#话题`
- 系统自动生成富文本 Tag，正文中手写的 `#xxx` 不会变成话题链接
- 建议 3-5 个 Tag

### Tag 预处理（印务局负责）

- 自动修复逗号分隔的 tag（`"A股,投资"` → `["A股", "投资"]`）
- 去除 `#` 前缀
- 去重
- 最多 5 个

---

## `publish_with_video` — 视频笔记

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `account_id` | string | ✓ | 账号 ID |
| `title` | string | ✓ | 标题（≤20 中文字）|
| `content` | string | ✓ | 正文 |
| `video` | string | ✓ | 本地视频绝对路径（单文件）|
| `tags` | []string | — | 话题标签 |
| `schedule_at` | string | — | 定时发布 |
| `visibility` | string | — | 可见范围 |
| `products` | []string | — | 带货商品 |

---

## `publish_longform` — 长文笔记

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `account_id` | string | ✓ | 账号 ID |
| `title` | string | ✓ | 标题 |
| `content` | string | ✓ | 长文正文 |
| `desc` | string | — | 摘要/副标题（不填则用正文前800字）|
| `tags` | []string | — | 话题标签 |
| `visibility` | string | — | 可见范围 |

---

## 发布前检查

1. **登录状态**：`xhs-botN.check_login_status(account_id: 'botN')` — 创作者平台必须登录
2. **合规审核**：`compliance-mcp.review_content(title: '...', content: '...', tags: '...')` — `passed: true` 才发
3. **测试发布**：不确定时用 `visibility: '仅自己可见'` 先测试

---

## Important Notes

- **`account_id` 每次必填**，路由到对应 MCP 服务
- **`content` 和 `text_image` 都是正文**，位置不同（图下 vs 图上），无主次之分
- **`desc`** 只用于 `publish_longform`，是发布页摘要
- **定时发布**格式 ISO8601，时区 `+08:00`，支持1小时～14天内
