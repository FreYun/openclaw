# HEARTBEAT.md - 心跳巡检清单

## 每次心跳必做

### 小红书内容策划（xhs-content-planner）
- [ ] 每日 3 次定时触发：**9:00、13:00、18:00**
- [ ] 检查 `heartbeat-state.json` 中 `lastContentPlannerRuns`，判断当前时段是否已执行
- [ ] 到期则执行 `skills/xhs-content-planner/SKILL.md` 的完整流程（检查当天是否已发帖 → 收集素材 → 推荐选题）
- [ ] 执行后更新 `lastContentPlannerRuns` 记录

### 小红书素材巡逻（xhs-topic-collector）
- [ ] 每日 3 次定时触发：**10:00、15:00、21:00**
- [ ] 检查 `heartbeat-state.json` 中 `lastTopicCollectorRuns`，判断当前时段是否已执行
- [ ] 到期则执行 `skills/xhs-topic-collector/SKILL.md` 的完整流程（确定巡逻方向 → 多渠道巡逻 → 筛选记录 → 素材库维护）
- [ ] 执行后更新 `lastTopicCollectorRuns` 记录

> **节奏说明：** content-planner 和 topic-collector 的时间错开，形成"攒素材 → 选题 → 发布"的自然节奏。两个 skill 各 3 次/天，合计 6 次小红书相关任务。

### 知识星球话题巡检（zsxq-reader）
- [ ] 每日 3 次定时触发：**9:30、14:30、23:00**
- [ ] 检查 `heartbeat-state.json` 中 `lastZsxqReaderRuns`，判断当前时段是否已执行
- [ ] 到期则执行 `skills/zsxq-reader/SKILL.md` 的浏览流程：
  1. 启动浏览器 `openclaw browser start --browser-profile bot11`
  2. 依次打开每个已加入的星球（见 SKILL.md 中的星球列表）
  3. 滚动加载**自上次巡检以来的新话题**（按日期判断，遇到上次巡检时间之前的话题即停止滚动）
  4. 提取新话题的作者、日期、内容摘要、标签、附件列表
  5. **分星球汇总**：每个星球单独总结，包括新话题数量、重点话题摘要、附件列表
  6. 汇总结果发送给（飞书群聊 `feishu:direct:chat:oc_6fd813d4cebdcbc97ed622e2d47d8fac`）
- [ ] 执行后更新 `lastZsxqReaderRuns` 记录（记录本次巡检时间，供下次判断"新话题"截止点）

> **频率控制：** 每次滚动间隔 3-5 秒，单次最多加载 100 条（5 轮），两个星球之间间隔 2-3 分钟。

## 轮换执行（不必每次全做，但是每天至少做一次！）

### 跟踪任务
- [ ] 读取 `memory/tracking-tasks.json`，检查是否有 `status: "active"` 且到期需要执行的任务（按各任务的 `frequency` 和 `last_checked` 判断）
- [ ] 逐条执行检查，更新 `last_checked` 和 `last_result`
- [ ] 满足 `notify_condition` 的任务 → 发送到飞书群 `chat:oc_6fd813d4cebdcbc97ed622e2d47d8fac`
- [ ] 已过期或已完成的任务 → 标记为 `done`

### 记忆维护
- [ ] **确保当日日记存在：** 若今日 `memory/YYYY-MM-DD.md` 不存在，先创建该文件（内容可为标题 +「本日无记录」），保证每天都有当日日记文件
- [ ] 检查今天的 memory 日记是否需要更新：若今天有过对话/操作，但当日日记仍只有「本日无记录」，补写一小段当日小结（今天做了什么、有什么收获，或确认今天基本无事）
- [ ] 是否有值得写入 MEMORY.md 的长期经验
- [ ] 专题笔记是否需要补充

## 规则

- **更新 JSON 状态文件（`heartbeat-state.json`、`tracking-tasks.json` 等）时，必须用 Write（整体覆写）而非 Edit（局部替换）。** 因为 Edit 要求精确匹配旧内容，容易因并发修改或格式差异导致失败
- 深夜 24:00-08:00 不打扰，除非紧急
- 无事发生就 HEARTBEAT_OK
