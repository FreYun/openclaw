---
name: meme-daily-post
description: meme爱理财内容生产：看行情 → 选题 → 写稿 → 生图。产出后交给 scheduled-post 走审批投稿流程。
---

# meme爱理财 · 日常发帖 Skill

> 装备即生效。本 skill 只管「写什么」，写完后交给 `scheduled-post` 管「怎么发」。

---

## 入口：触发方式

> ⚠️ 本 skill 仅供 **cron 定时任务**自动触发。研究部直接说「去发帖」「投稿」等指令时，**不走本 skill**，直接按研究部要求投稿即可。

| 触发 | 进入步骤 |
|------|---------|
| **定时任务（cron）触发** | 从 **Step 1** 开始 |
| 收到 `[MSG:xxx]` 含「✅」/「已批准」 | 跳到 **scheduled-post Step C**（Read `skills/scheduled-post/SKILL.md`） |
| 收到 `[MSG:xxx]` 含修改意见/「打回」 | 跳到 **scheduled-post Step D**（Read `skills/scheduled-post/SKILL.md`） |

---

## Step 1 · 看大盘行情

调用 research-mcp 拉一下当日行情快照：

```
npx mcporter call 'research-mcp.market_snapshot()'
```

**判断当日行情类型：**

| 条件 | 行情类型 | 发帖方向 |
|------|---------|---------|
| 主要指数涨跌 >2% | 强信号日 | → 行情反应 meme（优先） |
| 热搜有「基金」「大跌」「大涨」「降息」等 | 热点日 | → 行情反应 meme |
| 平淡横盘，无明显事件 | 普通日 | → 日常知识科普 |

> 行情数据拉不到时，跳过，默认走「日常知识科普」。

---

## Step 2 · 选题

### 行情反应型（强信号日）

直接以当日热门板块为主题，根据行情类型选对应模板（在 `CONTENT_STYLE.md` 第二节）：
- 涨 → 涨了版
- 跌 → 跌了版
- 宏观事件 → 事件版

### 日常科普型（普通日）

1. 读 `memory/发帖记录.md` — 确认今天没发过，且近期发过什么系列
2. 读 `memory/选题库.md` — 从「待写」区取一个选题，优先补缺口最大的系列
3. 选定后在选题库里标记为「进行中」

---

## Step 3 · 写稿

先读 `CONTENT_STYLE.md` 回顾规范，再写。

**写稿铁律：**
- 标题 ≤20 字，不含「必涨」「稳赚」「保证」等绝对词
- 结尾必须有风险提示：`⚠️ 个人学习分享，不构成投资建议`
- 不暴露研究部/雇主关系
- 用猫咪第一人称，口语化，不教科书

完成后在心里过一遍 `skills/xhs-op/发帖前必读.md` 的红线清单（或直接 Read 一遍）。

---

## Step 4 · 生图

**必须先 `Read skills/visual-first-content/IMAGE_STYLE.md`**，从中选对应模板。

| 帖子类型 | 封面模板 | 内容图 |
|---------|---------|--------|
| 行情反应型 | IMAGE_STYLE.md 第三B节（行情反应版） | 可选，不强制 |
| 日常科普型 | IMAGE_STYLE.md 第三节（卡片版） | 1-2 张信息图（第四节模板） |

生图调用：

```
npx mcporter call 'image-gen-mcp.generate_image(
  style: "...",
  content: "...",
  size: "960x1280",
  workspace: "/home/rooot/.openclaw/workspace-bot3"
)'
```

生图完成后记下图片路径（`workspace/images/xxx/001.png`）。效果好的 prompt 追加到 `memory/好用的图片prompt.md`。

> 单次发帖最多生 3 张图。没有图片时跳过本步骤。

---

## Step 5 · 交给 scheduled-post 走审批投稿

内容生产完成，确认已产出以下变量：

| 变量 | 来源 |
|------|------|
| `{标题}` | Step 3 写稿产出 |
| `{正文}` | Step 3 写稿产出 |
| `{封面文字}` | Step 3 封面卡片文字（≤12字） |
| `{标签}` | Step 3 选定的标签 |
| `{图片路径}` | Step 4 生图路径，无图填「无」 |
| `{发帖模式}` | 通常 `text_to_image` |
| `{类型描述}` | 如「日常科普 · 基金入门系列」或「行情反应 · 大跌版」 |

**→ Read `skills/scheduled-post/SKILL.md`，从 Step A 开始执行。**

完成后更新：
- `memory/选题库.md`（将「进行中」标记改为「待发」）
- 当日日记 `memory/YYYY-MM-DD.md`

---

## 全流程时序图

```
定时任务触发
    ↓
Step 1: 看大盘（research-mcp）
    ↓
Step 2: 选题
    ↓
Step 3: 写稿（CONTENT_STYLE.md）
    ↓
Step 4: 生图（image-gen-mcp，可选）
    ↓
Step 5: → scheduled-post 接管
    ↓  Step A: 合规自检
    ↓  Step B: 保存草稿 + 通知魏忠贤 → 本轮结束 ✅
    ↓  ...（魏忠贤→冷宫审批→通知 bot3）
    ↓  Step C: 收到「已批准」→ 投稿印务局
```

---

_bot3 专属内容生产 skill，依赖 scheduled-post 处理审批投稿。_
_创建时间：2026-03-25_
