---
name: weread-reader
description: >
  微信读书 MCP 阅读 skill。通过 weread-mcp 工具搜索书籍、查看书架、逐页阅读。
  内容通过截图获取（DOM 文字被加密），用视觉能力阅读截图中的文字。
---

# 微信读书阅读 Skill

通过 weread-mcp 提供的 MCP 工具操作微信读书，实现搜索、阅读、翻页。

> **重要：必须使用 mcporter call 调用 weread-mcp 的工具，不要用 browser 工具操作微信读书。**

## 前置条件

- weread-mcp 服务已运行（端口 18100，mcporter.json 已配置）
- 已扫码登录。未登录时调 `weread_login_qrcode` 获取二维码图片路径，把图片发给研究部扫码

## 调用格式

**所有参数必须用 `key=value` 格式，不支持位置参数。** 示例：

```bash
# 搜索
npx mcporter call weread-mcp weread_search keyword=龙头价值赛道

# 获取书籍信息（book_id 从搜索结果获取）
npx mcporter call weread-mcp weread_book_info book_id=3300192225

# 打开阅读器（chapter_index=0 序言，1 第一章，-1 续读）
npx mcporter call weread-mcp weread_read_page book_id=3300192225 chapter_index=1

# 翻页
npx mcporter call weread-mcp weread_turn_page book_id=3300192225 direction=next

# 其他
npx mcporter call weread-mcp weread_check_login
npx mcporter call weread-mcp weread_login_qrcode
npx mcporter call weread-mcp weread_shelf
npx mcporter call weread-mcp weread_bookmarks book_id=3300192225
```

## 阅读流程

### 1. 搜索并获取书籍信息

```bash
npx mcporter call weread-mcp weread_search keyword=书名关键词
# → 从结果中找到 bookId

npx mcporter call weread-mcp weread_book_info book_id=3300192225
# → 获取目录结构、章节数、免费章节数
```

### 2. 打开指定章节

```bash
npx mcporter call weread-mcp weread_read_page book_id=3300192225 chapter_index=1
# → 返回截图 + 章节标题
# chapter_index: 0=序言, 1=第一章, -1=续读上次位置
```

**用视觉能力阅读截图中的文字内容。**

### 3. 逐页翻阅

```bash
npx mcporter call weread-mcp weread_turn_page book_id=3300192225 direction=next
# → 返回截图 + 章节标题 + 是否跨章/试读结束/书尾
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
4. **登录态** — 只要 MCP 服务不重启就保持登录。如果 API 返回 -2010 "用户不存在"或 errCode -2010，说明需要重新登录
5. **适合精读** — 每页截图+理解约 3-6 秒，一章约 1-2 分钟。适合"指定章节精读"，不适合通读整本书
6. **阅读笔记** — 每次阅读内容记录到 `memory/weread/` 目录，文件名格式 `{书名}-读书笔记.md`
