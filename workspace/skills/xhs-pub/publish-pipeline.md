# 发布流水线

> 印务局处理发布队列的完整流程。

## 队列目录

```
/home/rooot/.openclaw/publish-queue/
├── pending/      ← 待处理（folder 格式：post.md + 媒体文件）
├── publishing/   ← 处理中（mv 锁定）
└── published/    ← 归档（仅成功的；失败的删除 + 通知提交者）
```

---

## 处理流程

```
收到投稿 [MSG:xxx]
  ↓
1. ACK：回复提交者队列位置
  ↓
2. 解析 post.md：提取 title, content, mode, account_id, images, tags, etc.
  ↓
3. 校验
   - account_id 必须是 bot1-bot10
   - title 非空，≤20 中文字
   - 频率限制：同账号 15 分钟内不可重复发布（bot10 豁免）
   - 上次失败的不受频率限制
  ↓
4. Tag 预处理
   - 逗号分隔 → 数组
   - 去 # 前缀
   - 去重
   - 最多 5 个
  ↓
5. 合规审核
   npx mcporter call "compliance-mcp.review_content(title: '...', content: '...', tags: '...')"
   - passed: true → 继续
   - passed: false → 通知提交者修改原因，删除投稿
  ↓
6. 登录检查
   npx mcporter call "xhs-botN.check_login_status(account_id: 'botN')"
   - 创作者平台必须已登录
   - 未登录 → 通知提交者 + 通知研究部
  ↓
7. mv pending/ → publishing/（锁定）
  ↓
8. 执行发布（Read publish-tools.md 查看 API 参数）
   npx mcporter call --timeout 180000 "xhs-botN.publish_content(...)"
  ↓
9. 成功 → mv publishing/ → published/（归档）
   失败 → 删除投稿 + 通知提交者错误信息
  ↓
10. 记录日志
    python3 ~/.openclaw/scripts/log-publish.py ...
    更新 memory/发帖记录.md
```

---

## 投稿消息格式

投稿通过 `[MSG:xxx]` 触发。提取 `msg_id` 用于回复。

**唤醒类型判断**：
- `[MSG:xxx]` → 投稿处理（提取 msg_id → ACK → 处理队列）
- Heartbeat → Run HEARTBEAT.md
- Admin 命令 → 按指示执行

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

- frontmatter 必须有 `content`（图下正文）AND body 有 `text_image`（卡片文字）
- 不能用 content 做 fallback 填 text_image
- 空行 `\n\n` 分割不同卡片（最多 3 张）

### image

- 图片文件在投稿文件夹内（`1.jpg`, `2.png` 等）
- 按文件名数字排序

### video

- 视频文件在投稿文件夹内

---

## 频率限制

| 规则 | 值 |
|------|-----|
| 同账号最短发布间隔 | 15 分钟 |
| bot10 | 豁免（测试账号）|
| 上次失败 | 不计入间隔 |

---

## 通知规则

- 发布结果：`reply_message(message_id: "{msg_id}", content: "...", deliver_to_user: true)`
- **禁止**使用 `message()`、`sessions_send`、`openclaw agent`
- Feishu 群告警：仅基础设施异常（heartbeat 发现的）；发布错误只通知提交者
