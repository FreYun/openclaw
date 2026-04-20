# 🔍 MDP 双源检索策略

> **触发场景**：主播确定选题后，bot8 内部拉料；或主播主动说"这里数据再查查 / 给我找参考"

## 两个工具，两种角色

| 源 | 工具 | 角色 | 取多少 | 怎么用 |
|---|---|---|---|---|
| 公众号 | `search_weixin` | **投资框架 / 事实底** | 3-5 条 | 提取数据、逻辑链、机构观点。脚本里每个数据必须对应一个 INFOCODE |
| 抖音 | `search_xiaohongshu(source='抖音')` | **爆款结构 / 语感底** | 5-8 条 | 提取钩子句式、段落节奏、金句模板。**只学骨架，不抄话** |

## Query 设计按系列分叉

### 行情解读系列

**weixin**（偏机构深度）：

```
search_weixin(
  query="{具体事件或资产} {时段} 机构观点 深度",
  top_k=5,
  score_threshold=0.5,
  fields=["INFOCODE","TITLE","CONTENT","USER","SHOWTIME"]
)
```

示例：
- "黄金 4 月回撤 机构观点 2026"
- "美股科技股 4 月回调 流动性"
- "A股 外围冲击 历史复盘"

**抖音**（偏口语高热）：

```
search_xiaohongshu(
  query="{话题的白话问法}",
  source="抖音",
  top_k=10,
  min_likes=10000,
  fields=["INFOCODE","TITLE","CONTENT","USER","LIKES","NOTE_URL"]
)
```

示例：
- "黄金为什么跌"
- "美股还能买吗"
- "A股抄底信号"

### 必修课系列

**weixin**（偏概念解析）：

```
search_weixin(
  query="{概念名} 原理 案例 2026",
  top_k=5,
  score_threshold=0.6,
  fields=["INFOCODE","TITLE","CONTENT","USER","SHOWTIME"]
)
```

示例：
- "康波周期 当前阶段 判断依据"
- "锚定效应 投资 案例"
- "十五五规划 产业方向"

**抖音**（偏科普讲解）：

```
search_xiaohongshu(
  query="{概念名}科普",
  source="抖音",
  top_k=10,
  min_likes=5000,
  fields=["INFOCODE","TITLE","CONTENT","USER","LIKES"]
)
```

示例：
- "康波周期科普"
- "锚定效应通俗讲解"
- "美联储降息对普通人影响"

## 读 CONTENT 的规则

### weixin CONTENT

- **提取**：数据、时间、人名、机构名、因果链
- **忽略**：公众号自营广告、课程推广、"点在看"等 CTA
- **脚本引用**：写到脚本里时要在 frontmatter 挂 INFOCODE
  ```yaml
  sources_weixin: [INFOCODE1, INFOCODE2]
  ```
  并在脚本末尾「引用底」节写清"INFOCODE1 用于第 X 段的数据 Y"

### 抖音 CONTENT

- **提取**：钩子句式（开头 1-2 句）、段落切换方式、金句模板、CTA 形式
- **禁止**：复制原句、复制完整段落、复制独特比喻
- **脚本引用**：frontmatter 挂 INFOCODE 作为"参考结构"，脚本末尾「参考结构」节写清"INFOCODE3 — 钩子句式 'X年Y倍'"

## 素材落盘（静默归档）

对每次生产，把检索结果写入：

Path: `workspace-bot8/memory/scripts/{series}/YYYY-MM-DD-{slug}.material.md`

```markdown
---
topic: {选题}
series: 行情解读 | 必修课
queried_at: 2026-04-17T10:30:00+08:00
---

## weixin 结果

### INFOCODE1 — 《{标题}》@ {USER} @ {SHOWTIME}
{CONTENT 前 500 字摘录，保留数据和观点}

### INFOCODE2 — ...

## 抖音结果（结构参考）

### INFOCODE3 — 《{标题}》@ {USER}｜{LIKES} 赞
{CONTENT 全文，标注 "钩子 / 转折 / 金句 / CTA" 的位置}

### INFOCODE4 — ...
```

**素材包不返回给主播**——主播只看正稿。素材包仅用于：
1. 脚本生产时引用
2. polish 时溯源
3. 月度质量复盘

## FAIL-LOUD

- weixin 返回空 / 少于 3 条 → 脚本里无法追溯的段落**整段不写**
- 抖音返回空 → 钩子 / 骨架只靠主播历史样本和你的 SOUL，不编"参考结构"
- MCP 调用失败 → 立即告诉主播"MDP 拉不到：{错误}"，不硬出稿
