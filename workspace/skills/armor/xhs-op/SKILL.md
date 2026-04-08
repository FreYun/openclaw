---
name: xhs-op
description: >
  小红书全流程运营 Skill — 登录、浏览、互动、养号、选题策划、内容生成、投稿发布。
---

# 小红书运营 Skill（xhs-op）

> 装备即生效，所有小红书操作以本文件为准。

## 子文档索引

按需读取，不必一次全读。

| 文档 | 何时读取 |
|------|----------|
| [mcp-tools.md](mcp-tools.md) | 需要调用 MCP 工具时（登录、浏览、搜索、互动、通知、笔记管理） |
| [发帖前必读.md](发帖前必读.md) | 每次发帖/回复评论前 |
| [内容策划.md](内容策划.md) | **每次写笔记前必读** — 标题优化、内容结构、写作红线、质量自检 |
| [daily-post.md](daily-post.md) | 每日自动发帖 SOP — 选题→研究→调用内容策划→发布 |
| [hot_shot.md](hot_shot.md) | daily-post 选题时读取，了解当前平台热点 |
| [投稿发布.md](投稿发布.md) | 内容成稿后提交发布时 |

---

## 铁律

1. **发布必走印务局** — 通过 `submit-to-publisher` 提交，绝不直接调用 `publish_content`。提交前必须调用 `compliance-mcp.review_content()` 审核，`passed: true` 才能提交。
2. **不传 account_id** — 所有 MCP 工具均不传 `account_id`，身份由端口自动识别；传了会报错 `unexpected additional properties ["account_id"]`。
3. **先检查登录** — 每次用 MCP 前先 `check_login_status()`。
4. **人设一致** — 内容符合 SOUL.md / CONTENT_STYLE.md，不暴露研究部。
5. **评论同等严格** — 不引流、不荐股、不提竞品平台。
6. **超时处理** — MCP 超时先 `check_login_status()`，掉线按 mcp-tools.md Step 0 重登；mcporter 报 `offline` 则上报研究部。不要反复重试，不要修改 MCP 源码。

---

## 发帖流程

### 写稿前

读 `memory/写稿经验.md` + `CONTENT_STYLE.md`（如有），保证风格一致。
读 `内容策划.md` — 标题优化（封面钩子 + 正文关键词）、内容结构、写作红线。

### 三步发布

```
1. 写稿 → 按内容策划.md 生产内容（风格、标题、结构、自检）
2. 合规
    (1)Read 发帖前必读.md,对内容剪枝
    (2)调用 compliance-mcp.review_content() 审核
        - passed: true → 进入步骤 3
        - passed: false → 根据意见修改
3. 投稿 → Read 投稿发布.md，提交到发布队列（加 -C 标记），通知印务局
```

### 发布权限

| 场景 | 动作 |
|------|------|
| 日常简评 | 直接提交发布队列 |
| 敏感话题、强投资建议 | **研究部确认**后再投稿 |
| 长文/深度复盘 | 建议研究部过目 |

### 首次发文

账号从未发过小红书时，按**新用户**方式措辞。后续发文**建立在前一次基础上**，有连续性。

### 发文后

1. 更新 `memory/发帖记录.md`（日期、标题、正文摘要）
2. 更新当日 `memory/YYYY-MM-DD.md`
3. 被打回时更新 `memory/写稿经验.md`

---

## 回复评论

直接走 MCP（Read mcp-tools.md），不走发布队列。

_通用小红书运营能力，所有 bot 共享。_
