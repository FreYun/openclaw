---
name: xhs-pub-quickref
description: 小红书发布中心速查表：将路由、调用约定、Tag处理、登录检查、频率限制、通知方式等关键规则合并为单文档，无需翻阅三个子文档即可完成发布任务。
---

# 小红书发布速查表（xhs-pub-quickref）

> 自包含速查版。所有关键规则已内联，无需读取子文档即可完成发布任务。

---

## ① MCP 路由（30秒看懂）

```
服务名  = "xhs-" + account_id        （如 bot7 → xhs-bot7）
MCP URL = http://localhost:18060/mcp/{account_id}
```

支持：**bot1–bot18**（单进程多租户，同一 bot 串行、跨 bot 并行）

**铁律：`account_id` 必须与服务名/URL 完全匹配，路由错误是最高级别事故。**

---

## ② 调用约定（--args 是必选项，不是可选）

```bash
# ✅ 标准写法（含特殊字符/换行/emoji 时必须用文件）
cat > args.json << 'EOF'
{
  "account_id": "bot7",
  "title": "标题",
  "content": "正文…",
  "images": ["/abs/path/1.png"],
  "tags": ["标签1", "标签2"],
  "visibility": "公开可见"
}
EOF
npx mcporter call --timeout 180000 xhs-bot7.publish_content --args "$(cat args.json)"

# ✅ 简单参数（无特殊字符才可用内联）
npx mcporter call --timeout 180000 "xhs-bot5.publish_content(account_id: 'bot5', title: '测试', content: '正文')"

# ❌ 禁止：引号嵌套必崩
npx mcporter call 'xhs-bot7.publish_content(content: "含引号的内容")'
```

**`--timeout 180000` 每次必须带，不省略。**

---

## ③ 发布工具速查

| 工具 | 适用场景 | 核心必填参数 |
|------|---------|------------|
| `publish_content` | 图文 / 文字配图 | `account_id`, `title`, `content` |
| `publish_with_video` | 视频笔记 | `account_id`, `title`, `content`, `video`（绝对路径）|
| `publish_longform` | 长文笔记 | `account_id`, `title`, `content` |

---

## ④ publish_content 两种模式对比

| | 普通图文 | 文字配图 |
|--|---------|---------|
| `text_to_image` | false（默认）| **true** |
| `images` | **必填**（URL或本地路径）| 可不填 |
| `content` | 图片下方正文 | 图片下方正文 |
| `text_image` | 忽略 | 图片卡片上的文字（`\n\n`分隔多张）|
| `image_style` | 忽略 | `基础`/`光影`/`涂写`/`书摘`等 |

**⚠️ `text_image` ≠ `content`，位置不同，不能互相 fallback。**

---

## ⑤ Tag 处理（印务局负责预处理）

```
输入："A股,投资,#黄金"
↓ 逗号分隔 → 数组
↓ 去 # 前缀
↓ 去重
↓ 最多 5 个
输出：["A股", "投资", "黄金"]
```

- **只通过 `tags` 参数传**，绝不在 `content`/`text_image` 中写 `#话题`
- 正文手写 `#xxx` 不会变成话题链接

---

## ⑥ 登录检查（发布前必做）

```bash
# ⚠️ 服务名必须是 xhs-botN，不是 xiaohongshu-mcp
npx mcporter call --timeout 180000 "xhs-bot7.check_login_status(account_id: 'bot7')"
```

检查两个状态：
- `galaxy_creator_session_id` — **发布必须**已登录
- `web_session` — 主站登录（互动用）

未登录 → 通知提交者 + 通知研究部，**停止处理**。

---

## ⑦ 完整发布流水线（9步）

```
收到投稿 [MSG:xxx]
  ↓
1. ACK：立即 reply_message 回复队列位置（优先级最高）
  ↓
2. 解析 post.md frontmatter：account_id / mode / title / content / images / tags 等
  ↓
3. 快速校验（失败立即通知，停止）
   - account_id ∈ bot1-bot18
   - title 非空且 ≤20 中文字
   - 频率：同账号 5 分钟内不重复（bot10 豁免；上次失败不计）
     ls -1t published/ | grep "_${account_id}_" | head -1  → 取最近时间戳
  ↓
4. Tag 预处理（见⑤）
  ↓
5. 登录检查（见⑥）— 创作者平台必须已登录
  ↓
6. mv pending/ → publishing/（锁定，防并发）
  ↓
7. 执行发布（用 --args + JSON 文件，见②）
  ↓
8. 成功 → mv publishing/ → published/ → reply_message 通知提交者
   失败 → rm publishing/ 投稿 → reply_message 通知具体错误
  ↓
9. 记录日志（异步，不阻塞下一条）
   python3 ~/.openclaw/scripts/log-publish.py ...
```

---

## ⑧ 队列目录结构

```
/home/rooot/.openclaw/workspace-sys1/publish-queue/
├── pending/      ← 待处理（folder：post.md + 媒体文件）
├── publishing/   ← 处理中（mv 锁定）
└── published/    ← 归档（仅成功；失败则删除）
```

---

## ⑨ 频率限制

| 规则 | 值 |
|------|-----|
| 同账号最短间隔 | 5 分钟 |
| bot10 | 豁免（测试账号）|
| 上次失败 | 不计入间隔 |

---

## ⑩ 通知规则（铁律）

```python
# ✅ 唯一合法方式
reply_message(message_id="{msg_id}", content="...", deliver_to_user=True)

# ❌ 禁止
message()
sessions_send(...)
openclaw agent ...
```

---

## ⑪ post.md 格式参考

```yaml
---
account_id: bot5
title: 标题（≤20字）
mode: text_to_image   # text_to_image / image / longform / video
tags: A股,投资
visibility: 公开可见
image_style: 基础
content: 图片下方正文
schedule_at: 2026-03-20T10:00:00+08:00   # 可选
is_original: true                          # 可选
---

图片卡片文字（text_to_image 时）
\n\n 分隔多张卡片（最多3张）
```

---

## ⑫ 健康检查 & 故障处理

```bash
# 健康检查
curl -s --connect-timeout 5 http://localhost:18060/health
# 返回 {"success":true,...} = 正常

# 日志
tail -f /tmp/xhs-mcp-unified.log
grep "bot7" /tmp/xhs-mcp-unified.log | tail -20
```

**MCP 异常时禁止自行重启** → 上报 mag1，等待管理员处理。

---

## 铁律速览

| # | 规则 |
|---|------|
| 1 | 只执行，不修改内容 |
| 2 | `account_id` 路由错误 = 最高级事故 |
| 3 | `--timeout 180000` 每次必带 |
| 4 | 特殊字符必用 `--args` + JSON 文件 |
| 5 | 登录检查用 `xhs-botN`，不是 `xiaohongshu-mcp` |
| 6 | Tag 只走 `tags` 参数，不写在正文里 |
| 7 | 通知只用 `reply_message`，禁用其他方式 |
| 8 | MCP 异常禁止自行重启 |

---

_印务局专属速查版。原始完整文档见父技能 xhs-pub。_
