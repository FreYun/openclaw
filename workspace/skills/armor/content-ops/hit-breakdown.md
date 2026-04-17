---
name: hit-breakdown
description: 跨领域采集小红书高互动帖子，拆解通用爆款规律（标题、开头、结构、情绪、互动设计），沉淀为可复用的模式库。
---

# 🔍 爆款拆解

> 不是"抄爆款"，是"读懂爆款的结构"。拆出来这些"做对的事"，才能复用。

爆款的底层特征跨领域通用——标题钩子、情绪曲线、互动设计的底层逻辑不分垂类。本 skill 只关心"怎么写才有人看"，不关心"写什么"。

## 目录结构

```
hit-breakdown/
├── patterns/       ← 核心输出：通用模式库
│   ├── INDEX.md                    速查表（<100 行）
│   └── titles/openings/structures/emotions/interactions/visuals/failures.md
├── samples/        ← 人可读拆解卡片存档（可选）
└── summaries/      ← 每批次分析摘要（frontmatter 记 batch 边界）
```

## 数据源

**Spider_XHS/datas/xhs.db** 是唯一数据源（由 `Spider_XHS/batch_collect.py` 滚动写入）。环境无 `sqlite3` CLI，用 `python3 -c 'import sqlite3; ...'`。

### posts 关键字段

| 字段 | 用途 |
|------|------|
| `note_id` PK, `title`, `desc`, `type` | 基础 |
| `image_count`, `cover_ratio` | 视觉（`cover_ratio` 已分类为"竖图/横图/方图"） |
| `tags_json` | 话题标签（JSON） |
| `fans_tier` | `素人(<1K)` / `小博主(1K-1W)` / `中腰部(1W-10W)` / `头部(>10W)` / `未知` |
| `likes`, `comments_count`, `collects`, `shares` | 四大互动 |
| `keyword`, `category` | 触发该条的关键词与大类 |
| `hit_count` | 被多个关键词命中次数 |
| **`first_seen_at`** | Spider 首次入库毫秒时间戳（INSERT 设，UPDATE 不动） |
| **`last_seen_at`** | Spider 最近一次刷到毫秒时间戳（**批次识别依据**） |
| `xhs_updated_at` | 小红书侧笔记更新时间，**不是** Spider 时间，别用它识别批次 |
| `published_at`, `comments_crawled_at` | — |

### comments 表

结构已建，可能为空。查前先 `SELECT COUNT(*) FROM comments WHERE note_id=?`；为空则在分析里标 `N/A - 评论未爬取`，别糊弄。

## 批次自动识别

一次爬虫运行会在较短窗口内刷一大片 `last_seen_at`，两次运行之间有空档。从 `MAX(last_seen_at)` 往回走，遇到第一个 > 阈值的 gap 就是本批起点。

```python
import sqlite3
DB = '/home/rooot/.openclaw/Spider_XHS/datas/xhs.db'

def find_latest_batch(gap_hours=6):
    """返回 (batch_start_ms, batch_end_ms, count) 或 None"""
    conn = sqlite3.connect(DB); cur = conn.cursor()
    rows = [r[0] for r in cur.execute(
        'SELECT DISTINCT last_seen_at FROM posts '
        'WHERE last_seen_at IS NOT NULL ORDER BY last_seen_at DESC')]
    if not rows: return None
    gap_ms = gap_hours * 3600 * 1000
    start = end = rows[0]
    for i in range(1, len(rows)):
        if rows[i-1] - rows[i] > gap_ms: break
        start = rows[i]
    (n,) = cur.execute('SELECT COUNT(*) FROM posts WHERE last_seen_at BETWEEN ? AND ?',
                       (start, end)).fetchone()
    conn.close()
    return (start, end, n)
```

**边界**：Spider 连跑不停 → 调小 `gap_hours`；想看"本批首次入库"而非"本批刷到" → 用 `first_seen_at` 替代 `last_seen_at`；想看历史某批 → 手动指定边界。迁移前（2026-04-13 前）的 857 行 `first/last_seen_at` 是从 `xhs_updated_at` 回填的近似值，不要当真实批次。

## 分析流程

### Step 1 — 鸟瞰（SQL 聚合）

先跑聚合拿分布，不要 `SELECT *` 全拉回来。

```python
start, end, n = find_latest_batch()
args = (start, end)

# 本批规模
cur.execute('SELECT COUNT(*) FROM posts WHERE last_seen_at BETWEEN ? AND ?', args)

# keyword × fans_tier 互动分布
cur.execute('''
  SELECT keyword, fans_tier, COUNT(*) n, AVG(likes) avg_l, AVG(comments_count) avg_c
  FROM posts WHERE last_seen_at BETWEEN ? AND ?
  GROUP BY keyword, fans_tier ORDER BY avg_l DESC
''', args)

# 深读候选：素人/小博主爆款 + 头部异常高的
cur.execute('''
  SELECT note_id, title, likes, comments_count, fans_tier, keyword
  FROM posts WHERE last_seen_at BETWEEN ? AND ?
    AND ((fans_tier IN ('素人(<1K)','小博主(1K-1W)') AND likes > 1000)
      OR (fans_tier IN ('中腰部(1W-10W)','头部(>10W)') AND likes > 10000))
  ORDER BY likes DESC LIMIT 40
''', args)
```

产出：分布表 + 25-40 篇深读候选名单。

### Step 2 — 深读（分批拉正文）

按 keyword 或 fans_tier 分批，每批 8-12 篇：

```python
cur.execute('SELECT title, desc, tags_json, cover_ratio, likes, comments_count '
            'FROM posts WHERE note_id IN ({})'.format(','.join('?'*len(ids))), ids)
```

每批用 **6 维度框架**分析，直接提炼该批共性 + 亮点，**不逐篇出卡片**。评论维度先查 `comments` 表；同批内对比高低分帖找差异。

### 6 维度框架

| 维度 | 观察点 |
|------|--------|
| **标题** | 钩子类型（痛点/反直觉/数字/悬念/身份/情绪/争议）、字数、情绪词 |
| **开头**（前 3 行） | 抓人方式（故事/直给/冲突/自嘲/提问/场景） |
| **结构** | 类型（故事/清单/对比/自述/教程/争议/反转）、段落骨架 |
| **情绪曲线** | 类型（开高走平/低开高走/过山车/持续升温）+ 关键转折点 |
| **互动设计** | 结尾钩子（提问/征集/抛争议/开放）、评论区特征、高赞评论（查 `comments` 表） |
| **视觉排版** | 封面风格、段落密度、emoji 密度 |

### Step 3 — 归纳写 patterns/

出现 ≥3 次的手法 → 提炼为模式写入 `patterns/<维度>.md`。模式结构：

```markdown
### {模式名}
> {一句话定义}

**适用场景**：...
**案例**：1. 《标题》👍N 💬N > 关键摘录  2. ...
**反面案例**：{常见失败版}
**使用要点**：- ...
```

素人案例优先（内容力 > 影响力）。同时写 `summaries/YYYY-MM-DD.md` 记录本次发现。

### summaries frontmatter

```markdown
---
analyzed_at: 2026-04-13
batch_start_ms: 1775900000000
batch_end_ms:   1775920000000
posts_in_batch: 127
keywords_touched: ["内卷", "一人食"]
---
```

下次分析前扫最新 summary 的 `batch_end_ms`，若 `MAX(last_seen_at) <= batch_end_ms` 则说明没有新批次，退出。

## 增量迭代规则

patterns/ 是活文档，新批次到来时增量更新不重写：

| 新旧对比 | 处理 |
|----------|------|
| 新证据支持已有模式 | 补案例、更新计数 |
| 发现子变体或适用边界 | 拆子模式或加注条件 |
| 新数据与已有模式矛盾 | 标争议，保留两种证据 |
| 出现全新手法（≥3 次） | 新增条目 |
| 连续 3+ 批次未观察到 | 标 "待验证" |

**单批 < 20 篇**：数据不足以归纳，用单篇拆解卡片写入 `samples/` 即可。
**单批 > 200 篇**：按 keyword/fans_tier 切片分析。

## 与其他 skill 集成

- **draft-review**：打磨标题/结构时只读 `patterns/INDEX.md` 速查表，按 ID 前缀（T→titles, S→structures）按需展开详情
- **content-calendar**：周度排期参考最近哪类结构/情绪在跑量
- **bot 写稿**：今日选题.md 附带"推荐参考模式"（标注模式 ID 即可）

## 铁律

1. 拆结构不搬正文，patterns/ 只留关键摘录
2. 跨领域优先，美食帖的标题技巧可能比理财帖更值得学
3. 高赞 ≠ 值得学：纯靠颜值/争议的没结构可学，跳过
4. 模式会过时，标观察时间；每月清理"待验证"条目
5. 30+ 篇拆解后规律才会浮现，前几次看不出别慌
