---
name: zsxq-reader
description: >
  知识星球话题阅读 skill。通过浏览器访问已登录的知识星球，浏览、提取、筛选星球话题内容。
  支持分类浏览、滚动加载全部话题、展开长内容、提取附件列表。
---

# 知识星球话题阅读 Skill

通过 OpenClaw 浏览器（profile: `bot11`，CDP 端口 `18811`）访问已登录的知识星球网页版，提取话题内容。

---

## 前置条件

- 浏览器 profile `bot11` 已启动且已登录知识星球（wx.zsxq.com）
- 启动浏览器：`openclaw browser start --browser-profile bot11`

## 已加入的星球

| 星球名 | URL |
|--------|-----|
| 黑马调研（免费） | https://wx.zsxq.com/group/51111221541414 |
| 土狗和他的朋友们 | https://wx.zsxq.com/group/452241841488 |

> 如有新加入的星球，补充到此表。

---

## 页面结构与关键选择器

### 星球话题列表页（`/group/{groupId}`）

| 元素 | 选择器 | 说明 |
|------|--------|------|
| 分类标签栏 | `.menu-container .item` | 最新、精华、纪要、只看星主、问答、文件… |
| 当前激活的分类 | `.menu-container .item.actived` | 带 `actived` class 的为当前选中 |
| 话题容器 | `.topic-container` | 第一个是包含分类栏+置顶的容器，后续每个是一条话题 |
| 置顶话题 | `.sticky-topic-container` | 置顶内容 |
| 作者名 | `.author` | 含作者名，可能尾部带日期文本 |
| 发布时间 | `.date` | 格式：`2026-03-16 16:32` |
| 话题正文 | `.talk-content-container .content` | 可能被截断，需配合"展开全部" |
| 展开/收起 | `.showAll` | 文字为"展开全部"或"收起" |
| 标签 | `.tag` | 如 `纪要` |
| 附件文件名 | `.file-name` | PDF/文档附件名 |
| 图片 | `.image-container img` | 话题内图片 |
| 操作按钮 | `.like` / `.comment` / `.subscribe` | 点赞、评论、收藏 |
| 查看详情 | `.details-container` | 点击后在右侧弹出详情面板 |

### 详情面板

| 元素 | 选择器 | 说明 |
|------|--------|------|
| 面板容器 | `app-topic-detail` | 右侧弹出的详情面板 |
| 内容区 | `app-topic-detail .content` | 详情面板中的正文 |
| 展开全部 | `app-topic-detail .showAll` | 面板中也可能需要展开 |

---

## 操作流程

### 1. 打开星球

```
openclaw browser navigate "https://wx.zsxq.com/group/{groupId}" --browser-profile bot11
```

等待 2-3 秒让页面加载完成。

### 2. 切换分类

通过 JS 点击分类标签：

```javascript
// 点击"精华"分类
const items = document.querySelectorAll('.menu-container .item');
for (const item of items) {
  if (item.textContent.trim() === '精华') {
    item.click();
    break;
  }
}
```

可用分类（视星球设置而定）：最新、精华、纪要、只看星主、问答、打卡、作业、文件、图片，以及星球自定义的标签分类。

### 3. 提取当前可见话题

```javascript
const topics = document.querySelectorAll('.topic-container');
let result = [];
for (let i = 1; i < topics.length; i++) { // 跳过 i=0（分类栏容器）
  const t = topics[i];
  result.push({
    author: (t.querySelector('.author') || {}).textContent?.trim(),
    date: (t.querySelector('.date') || {}).textContent?.trim(),
    content: (t.querySelector('.talk-content-container .content') || t.querySelector('.content') || {}).textContent?.trim(),
    tags: [...t.querySelectorAll('.tag')].map(tg => tg.textContent.trim()),
    files: [...t.querySelectorAll('.file-name')].map(f => f.textContent.trim()),
    imageCount: t.querySelectorAll('.image-container img').length,
    hasMore: !!t.querySelector('.showAll')
  });
}
```

### 4. 滚动加载更多话题

知识星球使用**滚动懒加载**，每次触底加载约 20 条：

```javascript
// 滚动到底部
window.scrollTo(0, document.documentElement.scrollHeight);
// 等待 2 秒后再次提取
```

**循环加载模式**（获取大量话题）：

```javascript
async function loadTopics(maxRounds = 5) {
  for (let round = 0; round < maxRounds; round++) {
    const beforeCount = document.querySelectorAll('.topic-container').length;
    window.scrollTo(0, document.documentElement.scrollHeight);
    await new Promise(r => setTimeout(r, 3000 + Math.random() * 2000)); // 3-5秒随机间隔
    const afterCount = document.querySelectorAll('.topic-container').length;
    if (afterCount === beforeCount) break; // 没有更多了
  }
  return document.querySelectorAll('.topic-container').length;
}
```

每轮加载约 20 条。单次 5 轮 ≈ 100 条。

**批量续载（200+ 条）的正确做法：**

1. **不要刷新页面** — 已加载的话题保留在 DOM 中，滚动位置和数据不会丢失
2. 第一批：调用 `loadTopics(5)`，加载约 100 条，**停下来等 2-3 分钟**
3. 第二批：在同一页面再调用 `loadTopics(5)`，从第 100 条接着往下加载到约 200 条
4. 如果中途 `afterCount === beforeCount`，说明已经到底，无需继续

**关键原则：同一页面会话内连续操作，不要导航离开或刷新，否则会从头开始。**

### 5. 展开被截断的内容

列表中的长内容会被截断（`.ellipsis` + `.showAll`）。展开方式：

```javascript
// 展开所有截断的话题
document.querySelectorAll('.showAll').forEach(btn => {
  if (btn.textContent.trim() === '展开全部') btn.click();
});
```

### 6. 查看话题详情

点击 `.details-container` 打开右侧详情面板：

```javascript
const topic = document.querySelectorAll('.topic-container')[targetIndex];
topic.querySelector('.details-container').click();
// 等待 1-2 秒
const detail = document.querySelector('app-topic-detail');
const fullContent = detail.textContent;
```

---

## 巡检输出格式

定时巡检完成后，**必须**按以下格式输出汇总（不是原始话题列表）：

```
📊 {星球名} {日期范围} 话题汇总

📍 滚动范围
从 {最新话题时间} 到 {最早话题时间}，共 {N} 条话题。

📈 话题分类统计

| 方向 | 话题数 | 核心内容 |
|------|--------|----------|
| {方向1} | N 条 | {关键词1}、{关键词2}、{关键词3} |
| {方向2} | N 条 | ... |
| ... | ... | ... |

🔥 核心主线聚焦
1️⃣ {主线名}（{定位描述}，{N} 条）
逻辑链：{完整传导链，用 → 连接}

核心标的：{相关股票/标的列表}
2️⃣ {主线名}（{定位描述}，{N} 条）
{催化剂/驱动力描述}

核心标的：{相关股票/标的列表}
3️⃣ ...

📊 关键数据速览（如有）
- {数据1，如：布油 103.9 美元，+42%}
- {数据2，如：DRAM 合约价 Q1 涨幅 90%-95%}
- {数据3，如：A股成交额 2.34 万亿}
- ...

📎 重点研报/附件（如有）
- {文件名1}
- {文件名2}
```

### 输出必含板块（缺一不可）

> **发送前自检：以下 5 个板块是否全部存在？缺任何一个就补上再发。**

| # | 板块 | 标识 | 是否可省略 |
|---|------|------|-----------|
| 1 | 滚动范围 | 📍 | 不可省略 |
| 2 | **话题分类统计** | 📈 | **不可省略** — 必须有方向/话题数/核心内容的表格 |
| 3 | 核心主线聚焦 | 🔥 | 不可省略 |
| 4 | 关键数据速览 | 📊 | 无数据时可省略，有数据必须列 |
| 5 | 重点研报/附件 | 📎 | 无附件时可省略，有附件必须列 |

**特别强调：「📈 话题分类统计」是必填项。** 它的作用是让小富龙一眼看到话题的全景分布，再看核心主线的深度分析。两者互补，缺一不可。即使某个方向只有 1 条话题，也要出现在分类统计表里。

### 输出规则

1. **分类归纳，不是逐条列举** — 把话题按投资/行业方向归类（如：中东局势/能源、科技/AI、医药、电力/储能、消费…），统计每个方向的话题数，提炼核心内容关键词。**这就是「📈 话题分类统计」表格的内容，必须输出。**
2. **核心主线要有深度** — 每条主线必须包含：
   - **逻辑链/传导链**（用 → 连接，如：霍尔木兹海峡封锁 → 布油+42% → 电解铝减产 → 化工品涨价）
   - **关键数据**（如融资金额、涨价幅度、政策目标数字等）
   - **核心标的**（话题中明确提到的公司/股票名，含目标价则注明）
3. **主线按重要性排序** — 话题数最多、市场影响最大的排第一，标注为"绝对主线"/"第二主线"等
4. **研报附件单独列出** — PDF 等文件名单独列出，方便小富龙按需查看
5. **不同星球分开输出** — 每个星球一个独立的汇总块
6. **关键数据单独汇总** — 话题中出现的具体数字（价格、涨跌幅、成交额、融资额、政策目标、产能数据等）提取到「关键数据速览」区，方便一眼扫到
7. **风格参考** — 像卖方晨会纪要/投研早报，简洁、有判断、有标的、有数据

## 常用场景

### 场景 A：定时巡检（主场景）

1. 启动浏览器，依次打开每个星球
2. 滚动加载自上次巡检以来的新话题（按日期截断）
3. 提取结构化数据
4. **按上述输出格式进行分类归纳和主线提炼**
5. **自检 5 个必含板块是否齐全（📍📈🔥📊📎）**
6. 分星球输出汇总，发送到飞书群
7. **存档：** 将本次汇总内容写入 `memory/zsxq/YYYY-MM-DD.md`（同一天多次巡检追加到同一文件，用 `### HH:MM 巡检` 标题分隔）

### 场景 B：按需深度阅读

1. 打开星球 → 切换到目标分类（如"精华"）
2. 循环滚动加载直到没有更多
3. 展开所有截断内容
4. 提取完整数据

### 场景 C：搜索特定关键词

1. 使用页面顶部搜索框（`textbox "搜索星球、文件、主题"`）
2. 输入关键词搜索
3. 提取搜索结果

---

## 频率控制

- **滚动间隔**：每次滚动加载等待 **3-5 秒**，不要连续快速滚动
- **单次批量上限**：单次任务最多加载 **100 条**（5 轮），避免行为异常
- **批量间隔**：两次批量操作之间间隔 **2-3 分钟**
- **原则**：模拟正常人浏览节奏，不要短时间内大量请求

---

## 注意事项

- **第一个 `.topic-container`** 是分类栏 + 置顶区域的容器，不是普通话题，提取时从 index=1 开始
- **作者文本**可能尾部粘连日期（如 `深度行研&调研纪要（* 2026-03-16 16:32`），用 `.date` 单独取日期更准确
- **图片只有 URL**，无法直接读取图中文字；如需 OCR 需额外处理
- **PDF 附件**只能看到文件名，无法直接下载/阅读内容
- **登录态依赖 cookie**，长时间不用可能过期，需重新扫码登录
