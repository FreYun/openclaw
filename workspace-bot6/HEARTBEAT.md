# HEARTBEAT.md - 心跳巡检清单

本 workspace 以小红书基金配置/理财内容为主。巡检侧重内容与记忆。

## 巡检任务（轮换执行，不必每次全做）

### 记忆维护
- [ ] **确保当日日记存在：** 若今日 `memory/YYYY-MM-DD.md` 不存在，先创建（标题 +「本日无记录」）
- [ ] 若今天有过对话/操作但当日日记仍只有「本日无记录」，补一小段当日小结
- [ ] 是否有值得写入 MEMORY.md 的长期经验（研究部偏好、内容规律、踩坑教训）

### 素材巡逻（定时：10:00、20:00）
- [ ] 执行 `skills/xhs-topic-collector/SKILL.md` — 巡逻小红书和外部信息源，收集选题灵感写入 `topic-library.md`
- [ ] 重点关注：基金配置、指数走势、商品动态、固收+市场变化
- [ ] 巡逻完成后简短汇报新增素材数量

### 内容策划与发布（定时：9:00、13:00、18:00）
- [ ] 执行 `skills/xhs-content-planner/SKILL.md` — 从素材库推荐 3 个选题，用户选定后生成内容并发布
- [ ] 注意智能跳过：当天已发帖则跳过本次推荐（用户主动要求除外）

### 市场数据巡检（每天 1-2 次，按 `memory/数据工具手册.md` 执行）

**每日快速巡检：**
- [ ] `market_overview` → 大盘涨跌 + 成交额
- [ ] `fund_basicinfo`（14只基金）→ 组合净值变动
- [ ] 有异动品种 → `news_search` 查原因
- [ ] 关注黄金、有色、固收+等核心品种的异动

**每周补充（周一或周五 1 次）：**
- [ ] `get_ashares_index_val` → 更新估值百分位
- [ ] `get_southbound_hkd_turnover` → 南向资金方向
- [ ] `get_cn_macro_data("pmi,cpi,m2,afre")` → 有无新宏观数据
- [ ] `commodity_data("黄金9999")` + `get_cn_bond_yield(maturity="10Y")` → 黄金和利率走势

**找不到数据时的兜底：** 先 `news_search` → 再用 browser 工具（`profile: "bot6"`）访问金十/东方财富/Mysteel/中国债券信息网，具体页面见 `memory/数据工具手册.md` 第六节

### 笔记数据更新（每天 1 次即可）
- [ ] 查询账号和笔记数据，**原地覆盖更新** `memory/笔记统计数据.md`（不要新建带日期后缀的文件）

### 小红书互动（研究部要求：每次心跳必做）
- [ ] **点赞 3 个帖子**：搜索基金/理财相关内容，选 3 个优质帖子点赞，每个操作间隔 1 分钟
- [ ] **评论 3 个帖子**：对上述或其他优质帖子发表有价值的评论（程序员视角 + 基金配置），每个操作间隔 1 分钟
- [ ] 查看通知、回复粉丝评论（使用 MCP `get_notification_comments` / `reply_notification_comment`）
- **互动要求**：点赞和评论各 3 个，每个动作间隔 ≥1 分钟，评论内容符合"爱理财的James"人设

### 系统健康巡检
- [ ] **检查浏览器进程**：执行 `ps aux | grep "bot6/user-data" | grep renderer` 查看是否有 CPU 占用 >20% 且运行超过 10 分钟的 renderer 进程。如有，`kill <PID>` 清理，并记录到当日日记
- [ ] **检查 tab 残留**：如果当前没有在用 browser 工具，确保没有残留的浏览器 tab

## 规则

- 深夜 24:00–08:00 不主动打扰，除非研究部有安排
- 发布前按 AGENTS.md「发布权限与确认」执行，不擅自发敏感或首次某类内容；按研究部要求办事，否则会被开除
- 无事发生就 HEARTBEAT_OK

## 心跳汇报

**⚠️ 不要用 `send_message` 汇报心跳结果！** 发消息会唤醒对方 agent，对方回复又会唤醒你，造成无限循环。

心跳结果写入文件即可：
```bash
echo "$(date '+%Y-%m-%d %H:%M') HEARTBEAT_OK - 状态摘要" >> /home/rooot/.openclaw/workspace-bot6/HEARTBEAT_LOG.md
```

- 一切正常 → 写一行 HEARTBEAT_OK + 状态摘要
- 发现严重异常（如进程崩溃）→ 才用 `send_message` 通知 `bot_main`，且消息末尾加 `[NO_REPLY_NEEDED]`
