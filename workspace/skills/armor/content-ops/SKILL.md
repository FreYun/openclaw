---
name: content-ops
description: >
  内容运营 Agent — 选题排期、审稿、人感诊断、爆款拆解。xhs-op 负责"怎么发"，content-ops 负责"发什么、写成什么样、哪篇该毙"。
---

# 内容运营 Agent（content-ops）

> 装备即生效。xhs-op 管"怎么发"，content-ops 管"发什么、写成什么样、哪篇该毙"。

## 定位

| 层级 | 负责人 | 管什么 |
|------|-------|--------|
| 合规层 | compliance-review | 法律红线、平台规则、敏感词 |
| 写作层 | 各 bot 自带的内容风格 skill | 标题、结构、排版、SEO |
| **主编层** | **本技能** | 选题排期、人感诊断、战略契合度、爆款模式学习 |
| 发布层 | `xhs-op` | 登录、浏览、互动、投稿发布 |

## 子文档索引

按需读取，不必一次全读。

| 文档 | 何时读取 |
|------|----------|
| [content-calendar.md](content-calendar.md) | 每日排期运行流程、queue/botN.md 格式、排期规则、参考知识 |
| [draft-review.md](draft-review.md) | 草稿需要主编层审稿（战略契合度、人感、节奏、差异化） |
| [hit-breakdown.md](hit-breakdown.md) | 有新爬虫数据需要分析、需要沉淀新的爆款模式、需要查阅 `patterns/` 速查表 |
| [human-feel-audit.md](human-feel-audit.md) | 定期体检（每 2 周）、数据下滑、新号上线前 2 周、审稿发现"人感"问题时 |

### 数据目录（不是文档，是沉淀产出）

```
workspace-{自己}/queue/         ← 各 bot 的排期队列（content-calendar 维护）
└── botN.md                     ← 落在装备本 skill 的 agent 自己的 workspace 下

content-ops/（skill 源目录，符号链接只读）
├── patterns/                   ← 爆款模式库（hit-breakdown 维护，全局共享）
│   ├── INDEX.md                速查表（优先只读这个）
│   └── titles/openings/structures/emotions/interactions/visuals/failures.md
└── summaries/                  ← hit-breakdown 每批次分析摘要
    └── YYYY-MM-DD.md
```

> **为什么 queue 在 agent workspace 而不在 skill 目录**：skill 通过 symlink 装备，sandbox 禁止向 symlink 外写入；且排期是 agent 自身状态，不该跨 agent 共享。patterns/summaries 仍在 skill 目录是因为它们是全局知识库，由 hit-breakdown 专门维护。

---

## 铁律

1. **派题必回审**。无论 cron 排期还是手动派题，给 bot 的指令里**必须包含"写完后用 `send_message(to="sys4")` 送审，等运营部回复再走合规→交稿"**。禁止让 bot 跳过回审直接走合规→印务局。（教训：2026-04-16 sys4 手动派题 bot6，即兴编写指令时删掉了回审步骤，bot6 写完直接合规→交稿，主编审核被跳过。）
2. **审稿是主编视角，不是找茬**。审的不是"这篇对不对"，而是"发出去对这个账号长期价值是正还是负"。让 bot 觉得"原来还能这样写"，而不是"又被打回来了"。
2. **patterns/INDEX.md 优先**。审稿和写稿时先查速查表，按需展开对应维度文件；不要一次把 `patterns/*.md` 全读进来。
3. **渐进式加载上下文**。draft-review 分三 phase，每 phase 只读当前需要的文件，读完立刻用，有 checkpoint 不跳步。
4. **爆款拆解不搬运正文**。`patterns/` 里的案例只保留关键摘录，记录结构和手法，不复制内容。
5. **人感诊断有触发条件**。不是每次都跑，按 human-feel-audit.md 里的触发条件列表执行。
6. **爬虫批次识别靠 `last_seen_at`**。hit-breakdown 分析时只看"最近一批"——用 `find_latest_batch()`，不要用 `xhs_updated_at`（那是小红书侧的笔记更新时间，不是 Spider 抓取时间）。

---

## 典型工作流

### 每日排期（content-calendar.md）

```
1. 读 workspace-{self}/queue/botN.md 当前排期 + 上周数据
2. 读各 bot 的 memory/topic-library.md（选题的第一输入源，绝不凭记忆编选题）
3. 扫热点环境 + bot 的内容支柱权重
4. 更新 workspace-{self}/queue/botN.md，推送当日任务给 bot
```

### 审稿（draft-review.md）

```
Phase 0: 接活（不读文件，确认输入）
Phase 1: 人感快检 — 读 bot 的 SOUL.md + 内容风格 skill
Phase 2: 战略契合度 — 读 workspace-{self}/queue/botN.md 当前排期
Phase 3: 标题/结构打磨 — 读 patterns/INDEX.md 速查表
```

### 分析爬虫新数据（hit-breakdown.md）

```
1. find_latest_batch() 算出最近一批的时间边界
2. 阶段一 鸟瞰 SQL 聚合（keyword × fans_tier × 互动分布）
3. 阶段二 深读 25-40 篇候选，按 6 维度框架分析
4. 阶段三 更新 patterns/*.md（强化/细化/挑战/新增/老化）
5. 写 summaries/YYYY-MM-DD.md 含 batch frontmatter
```

### 人感体检（human-feel-audit.md）

```
1. 采集 bot 近 14 天发帖（memory/posts/ + list_my_notes）
2. 按 AI 味七宗罪逐项检查
3. 输出诊断报告 + 针对性处方
4. 审稿发现问题时可以顺手跑
```

---

## 与其他 skill 的集成

- **xhs-op** — 发布层，本 skill 审完/选完/排完，交给 xhs-op 发
- **bot 自带的内容风格 skill**（如 `laicaimeimei-writing-style`、`laok-style` 等）— 写作层归 bot 自己管，content-ops 审稿不代笔，只看战略契合度和人感
- **xhs-topic-collector** — 素材积累，给 content-calendar 提供选题池
- **compliance-review** — 合规层，审完内容归 compliance 过一遍才能走 xhs-op 发布

_通用内容运营能力，所有 bot 共享。_
