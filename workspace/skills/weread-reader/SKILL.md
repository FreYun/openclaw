---
name: weread-reader
description: >
  微信读书网页版阅读 skill。通过浏览器访问已登录的微信读书，搜索书籍、查看书架、
  逐页阅读书籍内容。内容通过截图方式获取（DOM 文字被自定义字体加密，无法直接提取）。
---

# 微信读书阅读 Skill

通过 OpenClaw 浏览器访问已登录的微信读书网页版，实现搜索、浏览书架、逐章逐页阅读。

> 所有 browser 命令中的 `profile` 参数使用你自己的 `account_id`（从 TOOLS.md 获取）。

---

## 前置条件

- 你的浏览器 profile 已启动且已登录微信读书（weread.qq.com）
- 启动浏览器：`openclaw browser start --browser-profile your_account_id`
- 如未登录，需请研究部协助扫码登录
- 非付费会员账号每本书仅可免费阅读前 N 章（`maxFreeChapter`），超出部分会显示"试读结束"

---

## 核心限制：内容获取方式

微信读书使用**自定义字体 + Canvas 渲染**防盗版：
- DOM `innerText` 拿到的是空或乱码
- `Selection.toString()` 返回空
- 章节 API 的签名由 WASM 计算，无法直接调用

**因此，阅读内容只能通过截图方式获取。** 用 `browser snapshot` 截图后，靠视觉能力读取页面上的中文文字。截图文字清晰度完全满足阅读需求。

### 速度参考

| 操作 | 耗时 |
|------|------|
| 打开一本书（首次加载） | ~6 秒 |
| 截图 | ~80ms |
| 翻页（点击 + 等待动画） | ~600ms |
| 截图 + 理解内容 | 3-6 秒/页 |
| 一章（约 10-20 页） | 1-2 分钟 |

适合"指定章节精读"，不适合"通读整本书"。

---

## 操作流程

### 1. 搜索书籍

**方式 A：浏览器搜索页**
```
browser open url="https://weread.qq.com/web/search/books?keyword=思考快与慢" profile="your_account_id"
→ snapshot 查看搜索结果
```

**方式 B：API 搜索（更快，返回结构化数据）**
```javascript
// 在浏览器内执行
let resp = await fetch('/web/search/global?keyword=思考快与慢&maxIdx=0&count=10', {credentials: 'include'});
let data = await resp.json();
// data.books[].bookInfo: {bookId, title, author, cover, price, newRating, ...}
// data.totalCount, data.hasMore
```

翻页：`maxIdx` 递增 `count` 值。

### 2. 查看书架

**方式 A：浏览器页面**
```
browser open url="https://weread.qq.com/web/shelf" profile="your_account_id"
→ snapshot 查看书架
```

**方式 B：API（推荐，含阅读进度）**
```javascript
let resp = await fetch('/web/shelf/sync', {credentials: 'include'});
let data = await resp.json();
// data.books[]: {bookId, title, author, cover, price, ...}
// data.bookProgress[]: {bookId, progress(百分比), chapterIdx, chapterUid, readingTime(秒)}
```

### 3. 打开书籍

需要书的 `encodeId`（23 位 hex 字符串），获取方式：
```javascript
let resp = await fetch('/web/book/info?bookId=573975', {credentials: 'include'});
let data = await resp.json();
// data.encodeId: "af83263058c217af81f8979"
// data.title, data.chapterSize, data.maxFreeChapter
```

然后导航到阅读器：
```
browser open url="https://weread.qq.com/web/reader/{encodeId}" profile="your_account_id"
```

**自动续读**：直接打开书会自动跳到**上次阅读位置**。

### 4. 跳到指定章节

**方式 A：通过目录点击**
```
→ snapshot 看到右侧有目录按钮（三横线图标）
→ browser click ref="目录按钮ref" profile="your_account_id"
→ snapshot 看到目录列表
→ browser click ref="目标章节ref" profile="your_account_id"
→ 等 3 秒 → snapshot 确认已跳转
```

**方式 B：通过 URL 直跳**

URL 格式：`https://weread.qq.com/web/reader/{bookEncodeId}k{chapterEncodeId}`

章节 encodeId 可通过翻页时观察 URL 变化获取——每次跨章节时 URL 会更新。

**方式 C：通过 JS 点击目录项**
```javascript
// 打开目录
document.querySelector('.readerControls_item.catalog').click();
// 等 1 秒
let items = document.querySelectorAll('.readerCatalog_list_item');
// 点击指定索引的章节
items[目标index].click();
```

### 5. 逐页阅读

核心循环：
```
1. snapshot — 截图，读取当前页内容
2. 记录/理解内容
3. browser click ref="下一页按钮ref" profile="your_account_id"  （或用 JS: document.querySelector('.renderTarget_pager_button_right').click()）
4. 等待 0.6 秒
5. 重复 1-4 直到读完目标范围
```

**翻页规则**：
- 同一章节内翻页：URL 不变，靠"下一页"按钮逐页前进
- 跨章节翻页：URL 自动更新为新章节的 encodeId
- 没有"跳到第 N 页"的功能，只能从章节头部逐页翻

### 6. 指定阅读范围的处理

| 研究部指令 | 操作方式 |
|-----------|---------|
| "读第5章" | 通过目录跳到第5章，逐页读到章节结束 |
| "从上次的地方继续" | 直接 `browser open` 书的 URL，自动续读 |
| "读到第10章结束" | 从当前位置翻页，观察章节标题变化，读完第10章停止 |
| "读第3章到第5章" | 目录跳到第3章，逐页读到第5章末尾 |
| "读这本书的序言" | 目录跳到"序言"章节 |

**判断当前位置**：截图左上角或顶部显示当前章节标题，翻页后章节标题会随之变化。

### 7. 获取书籍元数据

```javascript
// 书的详细信息
let resp = await fetch('/web/book/info?bookId={bookId}', {credentials: 'include'});
// → title, author, publisher, isbn, intro, chapterSize, maxFreeChapter, totalWords, encodeId

// 书的目录结构
let resp = await fetch('/web/book/outline', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'include',
    body: JSON.stringify({bookId: '{bookId}'})
});

// 用户的划线/笔记
let resp = await fetch('/web/book/bookmarklist?bookId={bookId}&syncKey=0', {credentials: 'include'});
```

---

## 关键 CSS 选择器

### 阅读器页面

| 选择器 | 用途 |
|--------|------|
| `.renderTargetPageInfo_header_chapterTitle` | 当前章节标题 |
| `.renderTarget_pager_button_right` | "下一页"按钮 |
| `.renderTarget_pager_button` | "上一页"按钮 |
| `.readerControls_item.catalog` | 目录按钮（右侧栏） |
| `.readerCatalog_list_item` | 目录中每个章节项 |
| `.readerCatalog_list_item_title_text` | 章节标题文字 |
| `.readerCatalog_list_item_selected` | 当前选中的章节 |
| `.readerTopBar_title_link` | 顶栏书名 |
| `.wr_horizontal_reader_needPay_container` | "试读结束"付费提示 |

### 搜索结果页

| 选择器 | 用途 |
|--------|------|
| `.wr_bookList_item` | 单个搜索结果 |
| `.wr_bookList_item_title` | 书名 |
| `.wr_bookList_item_author` | 作者 |
| `.wr_bookList_item_desc` | 简介 |
| `.wr_bookList_item_reading` | 阅读人数 |

### 书架页

| 选择器 | 用途 |
|--------|------|
| `.shelf_list` | 书架列表 |
| `.shelfBook` | 单本书 |

---

## URL 模式

| 页面 | URL |
|------|-----|
| 首页 | `https://weread.qq.com` |
| 搜索 | `https://weread.qq.com/web/search/books?keyword={关键词}` |
| 书架 | `https://weread.qq.com/web/shelf` |
| 书详情 | `https://weread.qq.com/web/bookDetail/{encodeId}` |
| 阅读器 | `https://weread.qq.com/web/reader/{encodeId}` |
| 阅读器（指定章节） | `https://weread.qq.com/web/reader/{bookEncodeId}k{chapterEncodeId}` |

---

## ID 系统

| ID 类型 | 格式 | 用途 |
|---------|------|------|
| `bookId` | 数字字符串（如 `"573975"`） | 所有 API 参数 |
| `encodeId` | 23位 hex（如 `"af83263058c217af81f8979"`） | URL 路径 |

两者通过 `/web/book/info?bookId={id}` 可互查。

---

## 常用场景

### 场景 A：研究部指定书目精读

1. 搜索书籍 → 获取 bookId 和 encodeId
2. 查看 `maxFreeChapter` 确认可读范围
3. 打开阅读器 → 目录跳到指定章节
4. 逐页 snapshot 阅读，记笔记/提取要点
5. 读到指定范围结束
6. **关闭浏览器**

### 场景 B：从上次读到的地方继续

1. API 获取书架进度（`/web/shelf/sync`），找到目标书的 progress 和 chapterIdx
2. 打开阅读器（自动续读到上次位置）
3. 逐页阅读
4. **关闭浏览器**

### 场景 C：浏览书架推荐

1. 打开书架页 → snapshot 查看已有书目
2. 或用 API 获取完整书单 + 进度
3. 向研究部汇报书架内容和阅读进度
4. **关闭浏览器**

### 场景 D：搜索并评估新书

1. 搜索关键词 → 查看结果列表
2. 打开书详情页 → snapshot 查看评分、简介、评论
3. 向研究部推荐并说明理由
4. **关闭浏览器**

---

## 注意事项

1. **用完必须关浏览器** — `browser close profile="your_account_id"`，无论成功或失败
2. **付费限制** — 非会员账号仅可读免费章节，遇到"试读结束"提示时停止，告知研究部
3. **登录态** — Cookie 存在 Chrome profile 中，长时间不用可能过期，需研究部扫码重新登录
4. **页面加载慢** — 首次打开书约 6 秒，耐心等待后再 snapshot
5. **没有"跳到第 N 页"** — 只能按章节定位，然后在章节内逐页翻。如需从特定段落开始，先跳到对应章节再翻页找到
6. **频率控制** — 翻页间隔保持 0.5-1 秒，不要连续高速翻页
7. **阅读记录** — 每次阅读内容应记录到 `memory/weread/` 目录下，文件名格式 `{书名}-读书笔记.md`
