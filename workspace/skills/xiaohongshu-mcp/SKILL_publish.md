# Xiaohongshu MCP Skill（发布版）

> 本文件仅供**印务局（mcp_publisher）**使用。包含发布相关工具的完整参数说明。
> 运营操作（浏览/搜索/评论等）见 `SKILL.md`。

---

## Calling Convention

所有工具均需传对应 account_id，印务局根据 frontmatter 的 `account_id` 字段路由到对应 MCP 服务：

```bash
# 服务名 = "xhs-" + account_id
npx mcporter call "xhs-bot5.publish_content(account_id: 'bot5', title: '...', ...)"
npx mcporter call "xhs-bot7.publish_longform(account_id: 'bot7', title: '...', ...)"
```

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
| `content` | string | ✓ | 图片下方的正文文字（正文，非描述/副标题）|
| `images` | []string | 条件 | 图片 URL 或本地路径；`text_to_image=true` 时可不填 |
| `tags` | []string | — | 话题标签，如 `["黄金", "投资"]` |
| `schedule_at` | string | — | 定时发布，ISO8601，如 `2026-03-20T10:00:00+08:00` |
| `is_original` | bool | — | 是否声明原创 |
| `visibility` | string | — | `公开可见`（默认）/ `仅自己可见` / `仅互关好友可见` |
| `products` | []string | — | 带货商品关键词 |
| `text_to_image` | bool | — | `true` = 文字配图模式（自动生成图片）|
| `text_image` | string | — | 图片卡片上的文字（仅 `text_to_image=true` 时有效）；不填则用 `content` 前100字 |
| `image_style` | string | — | 图片风格：`基础`（默认）/ `光影` / `涂写` / `书摘` / `涂鸦` / `便签` / `边框` / `手写` / `几何` |

### 两种模式说明

**普通图文**（`text_to_image: false` 或不填）：
- `images` 必填（URL 或本地路径）
- `content` = 图片下方显示的正文
- `text_image` 忽略

**文字配图**（`text_to_image: true`）：
- `images` 可不填（小红书自动将文字生成图片）
- `text_image` = 图片卡片上的文字（每张卡片用 `\n\n` 分隔多张）
- `content` = 图片下方的正文
- `image_style` 控制图片风格

### 文字配图示例

```bash
npx mcporter call "xhs-bot5.publish_content(
  account_id: 'bot5',
  title: '黄金今天又涨了',
  content: '今天黄金价格创新高，背后的逻辑是什么？来聊聊我的看法。\n\n#黄金 #投资',
  text_to_image: true,
  text_image: '今天黄金又涨了\n\n背后逻辑是什么\n\n我来分析一下',
  image_style: '基础',
  tags: ['黄金', '投资'],
  visibility: '公开可见'
)"
```

> `text_image` 中用 `\n\n` 分隔多张卡片，`content` 是图片下方的正文，两者都是正文，位置不同。

### Tag 使用指南

- 话题标签**只通过 `tags` 参数**传，不要在 `content` 或 `text_image` 中写 `#话题`
- 系统自动生成富文本 Tag，正文中手写的 `#xxx` 会变成普通文字，不会变成话题链接
- 建议 3-5 个 Tag，太多会稀释权重

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
| `content` | string | ✓ | 长文正文，段落间用换行分隔 |
| `desc` | string | — | 发布页摘要/副标题（不填则用正文前800字）|
| `tags` | []string | — | 话题标签 |
| `visibility` | string | — | 可见范围 |

---

## 定时发布示例

```bash
# 明天早上 9 点发布
npx mcporter call "xhs-bot7.publish_content(
  account_id: 'bot7',
  title: '...',
  content: '...',
  images: ['/path/to/image.jpg'],
  schedule_at: '2026-03-14T09:00:00+08:00'
)"
```

---

## 发布前检查

1. **登录状态**：先 `xhs-botN.check_login_status(account_id: 'botN')` — 创作者平台必须登录
2. **合规审核**：先 `compliance-mcp.review_content(title: '...', content: '...', tags: '...')` — `passed: true` 才发
3. **测试发布**：不确定时用 `visibility: '仅自己可见'` 先测试

---

## Important Notes

- **`account_id` 每次必填**，路由到对应 MCP 服务
- **`content` 和 `text_image` 都是正文**，位置不同（图下 vs 图上），无主次之分
- **`desc`** 只用于 `publish_longform`，是发布页摘要；`publish_content` 没有 `desc` 参数
- **Tag 只通过 `tags` 参数**，不要在正文中硬写 `#话题`
- **定时发布**格式 ISO8601，时区 `+08:00`，支持1小时～14天内
