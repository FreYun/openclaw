---
name: trend-broadcast
description: >
  热门趋势播报 — 通过 opencli 抓取实时快讯、科技商业新闻、热门书籍等，
  整理成趋势播报。纯 CLI 调用，无需浏览器。
---

# 热门趋势播报（trend-broadcast）

> 抓取外部热门内容，整理成简洁的趋势播报。所有命令均为 PUBLIC 策略，直接 HTTP 请求，无需登录。

## 可用数据源

| 数据源 | 命令 | 内容类型 | 速度 |
|--------|------|---------|------|
| **新浪财经 7x24** | `opencli sinafinance news` | 实时快讯，带阅读量 | ~0.2s |
| **36氪** | `opencli 36kr news` | 科技/商业新闻，带摘要 | ~0.4s |
| **微信读书排行** | `opencli weread ranking` | 热门书籍排行榜 | ~0.1s |
| **微信读书搜索** | `opencli weread search "<关键词>"` | 书籍搜索 | ~0.2s |

## 通用参数

- `--limit N` — 返回条数（默认 20）
- `-f json` — JSON 格式输出（推荐，方便解析）
- `-f table` — 表格格式（默认，适合直接阅读）

## 使用场景

### 1. 获取实时热点快讯

```bash
opencli sinafinance news --limit 10 -f json
```

返回字段：`id`, `time`, `content`, `views`

适用：捕捉突发新闻、财经热点、社会事件，判断当下什么话题有热度。

### 2. 科技商业选题

```bash
opencli 36kr news --limit 10 -f json
```

返回字段：`rank`, `title`, `summary`, `date`, `url`

适用：了解科技/创业/商业领域最新动态，寻找内容角度。

### 3. 热门书籍话题

```bash
# 总榜
opencli weread ranking --limit 10 -f json

# 按关键词找书
opencli weread search "职场" --limit 5 -f json
```

ranking 返回字段：`rank`, `title`, `author`, `category`, `readingCount`, `bookId`
search 返回字段：`rank`, `title`, `author`, `bookId`, `url`

适用：发现当下读者关注的书籍话题，书评/读书笔记类内容选题。

## 选题工作流

当需要寻找选题灵感时，按以下顺序执行：

1. **扫快讯**：`opencli sinafinance news --limit 15 -f json` — 看当下什么事件正在发酵
2. **看科技**：`opencli 36kr news --limit 10 -f json` — 看有没有适合自己人设的科技/商业话题
3. **翻书榜**：`opencli weread ranking --limit 10 -f json` — 看热门书籍有没有可以结合的内容角度

从以上结果中筛选与自己人设匹配的话题，结合 SOUL.md 和 CONTENT_STYLE.md 判断是否适合发帖。

## 播报输出格式

执行完三个数据源后，整理成以下格式播报：

```
【热门趋势播报】{日期} {时段}

📰 实时快讯（新浪财经）
- {时间} {内容摘要}（{阅读量}）
- ...
（取阅读量最高的 5 条）

💡 科技商业（36氪）
- {标题}：{一句话摘要}
- ...
（取最新 5 条）

📚 热门书籍（微信读书）
- TOP{N} 《{书名}》{作者} — {分类}
- ...
（取 TOP 5）
```

播报要简洁，每条一行，不展开分析。目的是快速扫描当前热点。

## 注意事项

- **不要原样搬运**：这些数据是灵感来源，不是内容本身。如果用于创作，必须用自己的人设和风格重新加工。
- **时效性**：快讯数据实时更新，适合当天使用；书籍排行变化较慢，可作为长期选题池。
- **网络限制**：当前服务器部分海外站点不可达，以上数据源均已验证可用。
- **播报不是创作**：趋势播报只做信息整理，不需要加入个人观点或人设语气。
