---
name: xhs-auto-publish
description: >
  小红书智能自动发帖 — 每日定时触发，素材收集→选题→行情校验→生图→发帖→数据驱动重试→低效清理。
  基于阅读数据反馈动态决策，每日至多 5 次自动发帖，有帖子阅读破 500 即停止，当日结束清理低效笔记。
---

# 小红书智能自动发帖（xhs-auto-publish）

> 每日定时触发，数据驱动的自动发帖闭环。装备即生效，触发时间由各 bot 自行配置。

---

## 总览

```
[每日 start_time 触发]
  → Step 1: 读取/初始化当日状态
  → Step 2: 素材收集
  → Step 3: 选题 + 行情校验
  → Step 4: 内容创作 + 生图
  → Step 4.5: 合规审核（compliance-mcp）
  → Step 5: 提交发布（走印务局）
  → Step 6: 记录 & 创建 2h 后 one-shot cron job
  ──── cron 触发（2h 后）────
  → Step 7: 数据回查 & 决策
    ├─ 有帖子 ≥ 500 阅读 → 当日完成 ✅
    ├─ 已发 5 次 → 当日完成（达上限）✅
    ├─ 最新帖 < 200 阅读 → 回到 Step 2 再发一条
    └─ 200 ≤ 阅读 < 500 → 再等 2h 后重新回查
  ──── cron 触发（23:00）────
  → Step 8: 清理低效笔记（仅删除本 skill 当日发的且阅读 < 200 的）
```

**铁律**：
1. 每日最多 5 次自动发帖
2. 有任一帖子阅读 ≥ 500 即停止发帖
3. 发布必走印务局（submit-to-publisher），不直接调用 publish
4. 行情相关内容必须先拿到实时数据，不凭记忆写数字
5. 当日 23:00 清理低效笔记，但无条件保留阅读最多的 2 条
6. **21:30 后不再发帖**——无论当日是否发过笔记、是否还有重试余额，21:30 之后只做回查/清理，不新发

---

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `start_time` | 每日首次触发时间（HH:MM），各 bot 在 HEARTBEAT.md 中配置 | `09:30` |

> 文档中 `<你的account_id>` 是占位符，执行时替换为自己的 bot ID（如 `bot11`）。每个 bot 从自己的 TOOLS.md 中获取。

---

## Step 1 — 读取/初始化当日状态

状态文件：`memory/auto-publish-state.json`

```bash
# 读取状态文件
cat memory/auto-publish-state.json 2>/dev/null || echo '{"date":"","posts_today":[],"total_posts":0,"has_hit_500":false,"completed":false}'
```

**状态字段**（详见 [state-schema.md](state-schema.md)）：
- `date` — 当前日期（YYYY-MM-DD）
- `posts_today[]` — 今日发帖记录 `{ note_id, title, published_at, reads }`
- `total_posts` — 今日已发帖数
- `has_hit_500` — 是否有帖子阅读破 500
- `completed` — 当日任务是否已结束

**决策**：
- `date` 不是今天 → 重置为空状态（新的一天）
- `completed == true` → 不执行，直接退出
- `total_posts >= 5` → 不执行，直接退出
- `has_hit_500 == true` → 不执行，直接退出
- **当前时间 ≥ 21:30** → 不发帖，直接退出（回查/清理不受此限制）

---

## Step 2 — 素材收集

**前置检查**：确认 `total_posts < 5` 且 `has_hit_500 == false`。

### 2.1 检查素材库存量

```bash
# 读取素材库，检查灵感池中未用素材数量
cat memory/topic-library.md
```

- 灵感池未用素材 ≥ 3 条 → **跳过收集**，直接进入 Step 3
- 未用素材 < 3 条 → 执行收集

### 2.2 执行素材收集

按 `xhs-topic-collector` skill 的流程执行：

1. 读 SOUL.md + MEMORY.md → 确定巡逻方向（3-5 个关键词）
2. **并行收集**：
   - 小红书首页 `list_feeds` + 关键词搜索 `search_feeds`
   - 评论区 `get_notification_comments` — 粉丝在问什么
   - 外部信息源（Web 搜索、垂直平台）
3. 筛选 → 写入 `memory/topic-library.md` 灵感池

> 详细流程见 xhs-topic-collector/SKILL.md，此处不重复。

---

## Step 3 — 选题 + 行情校验

### 3.1 选题

从 `memory/topic-library.md` 灵感池中选 1 个选题：

**优先级**：
1. 🔥 时效性素材（即将过期的优先）
2. 🌲 常青素材（按人设契合度选）

**去重**：读 `memory/发帖记录.md`，确保与近 7 天发布内容不重复（标题/角度不撞车）。

### 3.2 行情校验（条件触发）

**判断规则**：如果选题涉及以下任一关键词 → 必须获取实时行情：
- 行情、大盘、指数、涨跌、A股、港股、美股
- 具体股票名/代码、基金、ETF
- 金价、油价、汇率、利率
- 板块、概念、热点轮动

**获取实时数据**：

```bash
# 大盘概览
npx mcporter call "research-mcp.market_overview()"

# 如涉及具体指数/个股，按需调用
npx mcporter call "research-mcp.get_index_daily(ts_code: '000001.SH', limit: 1)"
npx mcporter call "research-mcp.get_stock_daily_quote(ts_code: 'XXXXXX.SZ', limit: 1)"

# 如涉及商品（金、油等）
npx mcporter call "research-mcp.get_commodity_price(symbol: 'AU')"
```

**输出**：将实时数据整理为「行情速写」，作为 Step 4 内容创作的**硬约束输入**：

```
【行情速写 YYYY-MM-DD HH:MM】
- 上证：XXXX.XX（+X.XX%）
- 深证：XXXX.XX（+X.XX%）
- 创业板：XXXX.XX（+X.XX%）
- [其他相关数据]
```

> ⚠️ 内容中出现的任何具体数字（点位、涨跌幅、价格）必须来自行情速写，不可凭记忆编造。

---

## Step 4 — 内容创作 + 生图

### 4.1 准备

读以下文件确保风格一致：
- `CONTENT_STYLE.md`（如有）— 内容风格定义
- `SOUL.md` — 人设 & 说话风格
- `memory/写稿经验.md` （如有）— 踩坑教训
- `memory/发帖记录.md` （如有）— 最近发帖内容，保持连续性

### 4.2 创作

基于选题和行情速写（如有），创作图文笔记：

- **标题**：≤ 20 个中文字，有吸引力，符合人设
- **正文**：200-500 字，有实质信息量，不水
- **排版**：适当分段、用 emoji 点缀（但不过度）
- **标签**：3-5 个相关标签
- **行情内容**：数字必须与行情速写一致

### 4.3 生图

生成 1-3 张配图，**风格必须与 bot 自身人设一致**：

1. 检查 bot 是否有专属封面/生图 skill（如 `nailong-cover`、`mp-cover-art` 等） → 有则按该 skill 流程生图
2. 无专属 skill → 读 `CONTENT_STYLE.md` / `SOUL.md` 中的视觉风格定义，作为 `style` 参数传入 `image-gen-mcp`
3. 确认图片生成成功后进入下一步

---

## Step 4.5 — 合规审核

内容创作完成后、提交印务局前，**必须调用 compliance-mcp 审核**：

```bash
npx mcporter call "compliance-mcp.review_content(title: '标题', content: '正文内容', tags: '标签1,标签2')"
```

**决策**：
- `passed: true` → 进入 Step 5 提交
- `passed: false` → 根据 `violations` 修改内容，重新审核直到通过
  - 如多次审核不过 → 换选题，回到 Step 3
  - 在日记中记录审核不过的原因，更新 `memory/写稿经验.md`

---

## Step 5 — 提交发布（走印务局）

**必须通过 submit-to-publisher.sh 提交**，不直接调用 MCP publish。

**前提**：Step 4.3 必须已生成图片，Step 4.5 合规审核必须通过。

```bash
# 提交到印务局（必须用 image 模式，附带实际图片）
folder=$(bash ~/.openclaw/workspace/skills/xhs-op/submit-to-publisher.sh \
  -a <你的account_id> \
  -t "标题" \
  -b /tmp/post_body_$$.txt \
  -m image \
  -r "agent:<你的account_id>" \
  -T "标签1,标签2,标签3" \
  -c "正文内容" \
  -V "公开可见")
echo "FOLDER: $folder"
```

> ⚠️ **禁止使用 `text_to_image` 模式**。必须先通过生图工具生成真实图片，以 `-m image` 模式附带图片发布。

---

## Step 6 — 记录 & 设置回查

### 6.1 更新状态文件

发帖成功后，更新 `memory/auto-publish-state.json`：

```json
{
  "date": "YYYY-MM-DD",
  "posts_today": [
    { "note_id": "pending", "title": "帖子标题", "published_at": "HH:MM", "reads": 0 }
  ],
  "total_posts": 1,
  "has_hit_500": false,
  "completed": false
}
```

> `note_id` 初始为 `"pending"`，在 Step 7 回查时通过 `list_notes()` 匹配标题获取真实 ID。

### 6.2 更新发帖记录

按 xhs-op 规范更新 `memory/发帖记录.md` 和当日日记 `memory/YYYY-MM-DD.md`。

### 6.3 创建 2h 回查 cron job

每次发帖后，**显式创建一个 one-shot cron 任务**，确保 2h 后一定触发回查：

```bash
# 创建 1h 后触发的一次性任务，执行后自动删除
openclaw cron add \
  --name "auto-publish-check-<你的account_id>" \
  --at "+2h" \
  --message "执行 xhs-auto-publish Step 7：数据回查。读取 memory/auto-publish-state.json，调用 list_notes() 检查阅读数据，按规则决策是否继续发帖。" \
  --session isolated \
  --delete-after-run
```

> 使用 `--at "+2h"` 创建一次性 cron job（`schedule.kind: "at"`），执行后自动从 `cron/jobs.json` 中删除，不留垃圾。

### 6.4 创建 23:00 清理 cron job（仅当日首次发帖时）

如果是当日第一次发帖（`total_posts == 1`），同时创建当日 23:00 的清理任务：

```bash
# 仅首次发帖时创建，避免重复
openclaw cron add \
  --name "auto-publish-cleanup-<你的account_id>" \
  --at "$(date -d 'today 23:00' --iso-8601=seconds)" \
  --message "执行 xhs-auto-publish Step 8：当日清理。读取 memory/auto-publish-state.json，删除本 skill 当日发布的阅读 < 200 的笔记。" \
  --session isolated \
  --delete-after-run
```

---

## Step 7 — 数据回查 & 决策

### 7.1 获取阅读数据

```bash
npx mcporter call "xiaohongshu-mcp.list_notes()"
```

从返回结果中，按标题匹配找到今日通过本 skill 发布的笔记，提取：
- `feed_id` — 笔记 ID（更新到状态文件的 `note_id`）
- 阅读数（👁浏览）
- 点赞、收藏等互动数据

### 7.2 更新状态

将每条笔记的实际阅读数写回 `memory/auto-publish-state.json`。

### 7.3 决策

```
if 任一帖子 reads >= 500:
  → has_hit_500 = true
  → completed = true
  → 🎉 当日任务完成，在日记中记录成功帖子

elif total_posts >= 5:
  → completed = true
  → 📊 当日任务完成（已达 5 次上限），在日记中记录各帖数据

elif 最新帖子 reads < 200 且距发帖已过 2h:
  → 如果当前时间 ≥ 21:30 → 不再发帖，标记 completed = true
  → 否则 → 回到 Step 2，发一条新帖（循环继续）

elif 最新帖子 200 ≤ reads < 500:
  → 有潜力但还没破 500
  → 再创建一个 2h 后的 one-shot cron job 重新回查：
    openclaw cron add --name "auto-publish-check-<你的account_id>" --at "+2h" \
      --message "执行 xhs-auto-publish Step 7：数据回查" --session isolated --delete-after-run

else:
  → 发帖不足 2h，继续等待
```

---

## Step 8 — 当日清理（23:00 触发）

每日 23:00 执行，**仅清理当日通过本 skill 发布的低效笔记**。不动其他渠道（手动发帖、其他 skill、研究部发布等）产生的笔记。

### 8.1 获取最新数据

```bash
npx mcporter call "xiaohongshu-mcp.list_notes()"
```

用返回结果更新 `posts_today` 中各帖的最新 reads。

### 8.2 筛选 & 删除

**只遍历** `memory/auto-publish-state.json` 中 `posts_today` 列表里的帖子，不扫描全部笔记。

**保留规则**：按阅读量降序排序，**无条件保留阅读最多的 2 条笔记**（即使阅读 < 200），其余阅读 < 200 的才删除。

```
# 1. 按 reads 降序排列 posts_today（排除 note_id 为 "pending"/"lost" 的）
sorted_posts = sort posts_today by reads DESC (exclude pending/lost)

# 2. 前 2 名无条件保留
top2 = sorted_posts[:2]

# 3. 剩余帖子中，阅读 < 200 的删除
for each post in sorted_posts[2:]:
  if post.reads < 200:
    → 删除该笔记
    npx mcporter call "xiaohongshu-mcp.manage_note(feed_id: '<note_id>', action: 'delete')"
    → 标记 post.deleted = true
    → 在日记中记录删除原因
  else:
    → 保留（阅读 ≥ 200）
```

> ⚠️ **绝不删除不在 posts_today 中的笔记**。本 skill 只管自己发的帖子。
> ⚠️ **当日发帖 ≤ 2 条时不会删除任何笔记**（全部属于 top 2）。

### 8.3 收尾

- 更新状态文件：`completed = true`
- 在当日日记中写入清理报告：

```
🧹 每日清理报告（YYYY-MM-DD 23:00）
- 今日共发 X 条笔记
- 保留 Y 条（top 2 保底 + 阅读 ≥ 200）
- 删除 Z 条（排名 3+ 且阅读 < 200）
- 最佳帖子：「标题」— 阅读 XXXX
```

- 将使用过的选题从 `memory/topic-library.md` 灵感池移动到已用归档区

---

## 异常处理

| 场景 | 处理 |
|------|------|
| 素材库为空且收集失败 | 跳过本次，在日记中记录，下次 heartbeat 再尝试 |
| 行情数据获取失败 | 如选题依赖行情 → 换一个不依赖行情的选题；如全部依赖行情 → 跳过本次 |
| 合规审核不过 | 根据 `violations` 修改内容重新审核，多次不过则换选题，不额外计入发帖次数 |
| list_notes 无法匹配到帖子 | 可能发布延迟或被平台删除，在状态中标记为 `note_id: "lost"`，不影响后续流程 |
| 23:00 清理时某帖删除失败 | 记录到日记，下次 heartbeat 重试 |

---

## 日记记录模板

每次执行 skill 后，在当日日记 `memory/YYYY-MM-DD.md` 中追加：

```
## 🚀 智能发帖（第 N 次）HH:MM
- 选题：「标题」
- 来源：灵感池 / 实时热点
- 行情校验：✅ 已校验 / ⏭️ 无需校验
- 发布状态：✅ 已提交印务局 / ❌ 被打回（原因）
- 配图：X 张（生图工具/专属封面）
```

---

## 与其他 skill 的协作

| Skill | 关系 |
|-------|------|
| `xhs-topic-collector` | Step 2 素材收集时调用其完整流程 |
| `xhs-op` | 发帖流程复用其 submit-to-publisher、合规速查 |
| `research-mcp` | Step 3 行情校验时调用 |
| `image-gen-mcp` | Step 4 生图 |
| bot 专属封面 skill | Step 4 优先使用（如 nailong-cover） |

---

_通用智能发帖能力，各 bot 通过 symlink 引用，触发时间自行配置。_
