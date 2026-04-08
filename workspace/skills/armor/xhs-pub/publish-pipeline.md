# 发布流水线

> 印务局处理发布队列的完整流程。

## 队列目录

```
/home/rooot/.openclaw/workspace-sys1/publish-queue/
├── pending/      ← 待处理（folder 格式：post.md + 媒体文件）
├── publishing/   ← 处理中（mv 锁定）
└── published/    ← 归档（仅成功的；失败的删除 + 通知提交者）
```

---

## 处理流程

```
收到投稿 [MSG:xxx]
  ↓
1. ACK：立即回复提交者队列位置
  ↓
2. 解析 post.md：提取 account_id, mode, title, content, images, tags 等
  ↓
3. 快速校验（任一失败立即通知提交者，停止处理）
   - account_id 必须是 bot1-bot18
   - title 非空，≤20 中文字
   - 频率限制：同账号 5 分钟内不重复发布（bot10 豁免；上次失败不计）
     `ls -1t published/ | grep "_${account_id}_" | head -1` 取最近时间戳
  ↓
4. Tag 预处理
   - 逗号分隔 → 数组
   - 去 # 前缀
   - 去重
   - 最多 5 个
  ↓
5. 登录检查
   npx mcporter call --timeout 180000 "xhs-bot7.check_login_status(account_id: 'bot7')"
   ⚠️ 服务名必须是 `xhs-botN`（如 `xhs-bot7`），**不是 `xiaohongshu-mcp`**
   `xiaohongshu-mcp` 查到的是 sys1 自身的登录状态，不是目标 bot 的。
   - 创作者平台必须已登录
   - 未登录 → 通知提交者 + 通知研究部，**停止处理**
  ↓
6. mv pending/ → publishing/（锁定）
  ↓
7. 执行发布（服务名 = `xhs-{account_id}`，如 bot7 → `xhs-bot7`）

   **⚠️ 含特殊字符（引号/换行/emoji）时必须用 `--args` + JSON 文件：**

   ```bash
   cat > publishing/{投稿文件夹}/args.json << 'ARGS_EOF'
   {
     "account_id": "bot7",
     "title": "标题",
     "content": "正文内容...",
     "images": ["/absolute/path/to/1.png"],
     "tags": ["标签1", "标签2"],
     "visibility": "公开可见"
   }
   ARGS_EOF
   npx mcporter call --timeout 180000 xhs-bot7.publish_content --args "$(cat publishing/{投稿文件夹}/args.json)"
   ```

   ❌ 禁止：`mcporter call 'xhs-bot7.publish_content(content: "长文本")'`（引号嵌套必崩）
  ↓
8. 成功 → mv publishing/ → published/（归档）→ 通知提交者成功
   失败 → 删除 publishing/ 投稿 + 通知提交者具体错误
  ↓
9. 记录日志
   python3 ~/.openclaw/scripts/log-publish.py ...
   更新 memory/发帖记录.md（异步，不阻塞下一条）
```

---

## 投稿消息格式

投稿通过 `[MSG:xxx]` 触发。提取 `msg_id`，**第一步立即 ACK**。

---

## post.md 格式

```yaml
---
account_id: bot5
title: 标题
mode: text_to_image  # text_to_image / image / longform / video
tags: A股,投资
visibility: 公开可见
image_style: 基础
content: 图下正文
schedule_at: 2026-03-20T10:00:00+08:00  # 可选
is_original: true  # 可选
---

正文或 text_image 内容
```

---

## 特殊模式处理

### text_to_image

- frontmatter `content` = 图下正文；body 文字 = 卡片文字（`text_image` 参数）
- **不能**用 `content` 做 fallback 填 `text_image`
- `\n\n` 分隔多张卡片（最多 3 张）

### image

- 图片文件在投稿文件夹内（`1.jpg`, `2.png` 等）
- 按文件名数字排序

### video

- 视频文件在投稿文件夹内

---

## 频率限制

| 规则 | 值 |
|------|-----|
| 同账号最短发布间隔 | 5 分钟 |
| bot10 | 豁免（测试账号）|
| 上次失败 | 不计入间隔 |

---

## 通知规则

- 发布结果：`reply_message(message_id: "{msg_id}", content: "...", deliver_to_user: true)`
- **禁止**使用 `message()`、`sessions_send`、`openclaw agent`
- Feishu 群告警：仅基础设施异常（heartbeat 发现的）；发布错误只通知提交者
