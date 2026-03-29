---
name: weread-reader
description: >
  微信读书 MCP 阅读 skill。通过 weread-mcp 工具搜索书籍、查看书架、逐页阅读。
  内容通过截图获取（DOM 文字被加密），用视觉能力阅读截图中的文字。
---

# 微信读书阅读 Skill

通过 weread-mcp 提供的 MCP 工具操作微信读书，实现搜索、阅读、翻页。

> **重要：必须使用 mcporter call 调用 weread-mcp 的工具，不要用 browser 工具操作微信读书。**
> 调用方式：`npx mcporter call weread-mcp <tool_name> [args]`

## 前置条件

- weread-mcp 服务已运行（端口 18100，mcporter.json 已配置）
- 已扫码登录。未登录时调 `weread_login_qrcode` 获取二维码图片路径，把图片发给研究部扫码

## 工具列表

| 工具 | 用途 |
|------|------|
| `weread_check_login` | 检查登录状态 |
| `weread_login_qrcode` | 获取登录二维码 |
| `weread_search` | 搜索书籍，返回 bookId、书名、作者、评分 |
| `weread_shelf` | 获取书架和阅读进度 |
| `weread_book_info` | 获取书籍详情 + 完整目录（需要 bookId） |
| `weread_read_page` | 打开书籍阅读器并截图（可指定章节） |
| `weread_turn_page` | 翻页并截图（自动随机延迟） |
| `weread_bookmarks` | 获取划线和笔记 |

## 阅读流程

### 1. 搜索并获取书籍信息

```
weread_search(keyword="书名关键词")
→ 从结果中找到 bookId

weread_book_info(book_id="3300192225")
→ 获取 encodeId、章节数、免费章节数、目录结构
```

### 2. 打开指定章节

```
weread_read_page(book_id="3300192225", chapter_index=0)
→ 返回截图 + 章节标题
→ chapter_index: 0=第一个目录项（通常是序言），-1=续读上次位置
```

**用视觉能力阅读截图中的文字内容。**

### 3. 逐页翻阅

```
weread_turn_page(book_id="3300192225", direction="next")
→ 返回截图 + 章节标题 + 是否跨章/试读结束/书尾
```

重复调用 `weread_turn_page` 直到读完目标范围。

### 4. 读完后总结

每读完一章，向研究部汇报该章要点。

## 阅读场景

| 研究部指令 | 操作 |
|-----------|------|
| "读这本书的第3章" | book_info 获取目录 → read_page(chapter_index=对应索引) → 逐页 turn_page |
| "从上次的地方继续" | read_page(chapter_index=-1) → 逐页 turn_page |
| "帮我搜一本书" | weread_search → 向研究部展示结果 |
| "看看我的书架" | weread_shelf |
| "这本书有什么划线" | weread_bookmarks |

## 注意事项

1. **内容只能通过截图获取** — 微信读书用自定义字体加密，DOM 文字无法提取，必须靠视觉能力读截图
2. **翻页有随机延迟** — MCP 自动添加 400-900ms 随机延迟，模拟人类行为，不需要你手动等待
3. **免费章节限制** — `maxFreeChapter` 表示非会员可读章数，超出会提示试读结束
4. **登录态** — 只要 MCP 服务不重启就保持登录。如果 API 返回 -2010 "用户不存在"，说明需要重新登录
5. **适合精读** — 每页截图+理解约 3-6 秒，一章约 1-2 分钟。适合"指定章节精读"，不适合通读整本书
6. **阅读笔记** — 每次阅读内容记录到 `memory/weread/` 目录，文件名格式 `{书名}-读书笔记.md`
