---
name: space-tracker
description: >
  商业航天产业跟踪技能。监控发射计划、产业链动态、政策催化、概念股异动，
  输出发射提醒、产业周报、事件点评等内容，支持小红书和公众号两个渠道。
---

# 商业航天跟踪 skill

跟踪中国商业航天产业发展，包括：火箭发射计划、星座组网进度、可回收技术突破、政策催化、概念股异动。输出可用于小红书笔记、公众号文章、飞书提醒。

---

## 触发条件

### 定时触发（heartbeat）

| 时间 | 任务 | 说明 |
|------|------|------|
| 每日 8:30 | **发射日历检查** | 检查未来 7 天是否有计划发射，有则发飞书提醒 |
| 每日 20:00 | **产业动态巡逻** | 搜索当日商业航天新闻，更新到 `memory/space/daily-feed.md` |
| 每周日 10:00 | **周报生成** | 汇总本周发射、政策、公司动态，输出周报草稿 |

### 被动触发

- 研究部说 "查一下航天"、"发射提醒"、"航天周报"、"航天概念股"
- 知识星球/雪球出现航天相关热帖
- 概念股出现异动（单日涨幅 > 5% 的标的 ≥ 3 只）

---

## 信息源与工具

### 联网搜索（主力）

```bash
# 搜索当日商业航天新闻
web_search("商业航天 发射 2026")
web_search("千帆星座 GW星座 最新进展")
web_search("SpaceX Starship 最新")
```

关键词库（轮换使用，避免重复）：
- 发射类：`商业航天 发射`、`火箭首飞`、`朱雀三号`、`天龙三号`、`长征十二号`
- 星座类：`千帆星座 部署`、`GW星座 发射`、`卫星互联网 进展`
- 技术类：`可回收火箭 中国`、`液氧甲烷 火箭`、`一级回收`
- 政策类：`商业航天 政策`、`国家航天局 商业航天`
- 公司类：`蓝箭航天`、`天兵科技`、`星河动力`、`东方空间`、`中科宇航`
- 海外类：`SpaceX Starship`、`Starlink 卫星数量`

### 浏览器信息源（用 bot11 profile）

| 平台 | 用法 | 关注内容 |
|------|------|---------|
| **知识星球** | 通过 zsxq-reader skill 读取 | 黑马调研/土狗星球中航天相关讨论 |
| **雪球** | `openclaw browser navigate https://xueqiu.com/k?q=商业航天 --browser-profile bot11` | 热帖、大V观点、概念股讨论 |
| **小红书** | `xiaohongshu-mcp.search_feeds(keyword: '商业航天')` | 同行创作者内容、用户兴趣点 |

### 数据接口

```python
# 概念股行情（akshare）
import akshare as ak
# 商业航天概念板块
df = ak.stock_board_concept_name_em()  # 找到"商业航天"板块
df = ak.stock_board_concept_cons_em(symbol="商业航天")  # 成分股
# 卫星互联网概念板块
df = ak.stock_board_concept_cons_em(symbol="卫星互联网")
```

---

## Memory 路径规范

所有运行时数据存放在 `memory/space/` 下，与 skill 目录分离：

```
workspace-bot11/memory/space/
├── launch-calendar.md        # 发射日历（核心文件）
├── watchlist.md              # 概念股跟踪列表
├── industry-chain.md         # 产业链图谱笔记
├── daily-feed.md             # 每日资讯流水（滚动保留 7 天）
├── constellation-tracker.md  # 星座组网进度追踪
├── content-archive.md        # 已发布内容记录
├── weekly/                   # 周报存档
│   └── 2026-WXX.md
└── company-profiles/         # 重点公司档案
    ├── landspace.md          # 蓝箭航天
    ├── space-pioneer.md      # 天兵科技
    ├── galactic-energy.md    # 星河动力
    ├── ispace.md             # 星际荣耀
    ├── cas-space.md          # 中科宇航
    ├── orienspace.md         # 东方空间
    └── ...
```

### 维护规则

- `daily-feed.md`：每日追加，超过 7 天的内容移除（精华提炼到其他文件）
- `launch-calendar.md`：发射结果出来后 **立即更新**
- `watchlist.md`：每月复盘一次，剔除不再相关的标的，增加新标的
- `constellation-tracker.md`：每次有新批次发射后更新在轨数量
- `company-profiles/`：有重大事件时更新（首飞/IPO/融资/事故）

---

## 配套技能

| 技能 | 何时使用 |
|------|---------|
| `xhs-op/内容策划` | 将航天内容纳入小红书日常选题 |
| `mp-content-writer` | 输出公众号长文（周报、深度分析） |
| `zsxq-reader` | 从知识星球获取航天相关讨论 |
| `xhs-browser-publish` | 发布小红书笔记 |
| `xhs-op/素材积累` | 航天素材纳入日常素材巡逻 |
