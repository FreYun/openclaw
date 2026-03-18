# HEARTBEAT.md

## 定期任务

### 1. 预测验证检查（每次心跳）

读取 `memory/predictions/tracker.md`。
如果有"待验证"状态的预测，且已到或超过预期验证日期 → 执行验证并更新状态。

### 2. 自我复盘触发（每月一次）

读取 `memory/evolution/review-log.md` 最后一条复盘记录的日期。
如果距今超过 **30 天** → 触发 `/self-review`（完整复盘流程）。

如果距今 15-30 天 → 做轻量检查：
- 有无新积累的研究记录（`memory/research/` 下新文件）？
- 有无已到期但未核验的预测？
- 如有 → 写入 daily notes，下次主会话时处理。

### 3. 行业观点保鲜（每月）

读取 `memory/views/` 下所有文件的"最后更新"日期。
如果某个行业文件超过 **60 天** 未更新 → 在 daily notes 中标记，提醒在下次主会话中重新评估。

---

### 4. 小红书互动（每次心跳）

在搜索 feed 中执行互动动作，模拟真实用户行为：

**流程：**
1. 检查登录状态：`npx mcporter call xiaohongshu-mcp.check_login_status account_id=bot7`
   - 未登录 → 跳过互动，记录到 daily notes
2. 搜索与当前关注领域相关的 feed（关键词从当前研究主线中选取，如"AI算力"、"存储芯片"、"半导体"等）
3. 从搜索结果中选 3 篇与投研主题相关的优质帖子
4. **点赞 3 篇**：每篇之间间隔约 1 分钟（用 `sleep 60`）
   ```
   npx mcporter call xiaohongshu-mcp.like_feed account_id=bot7 feed_id={id} xsec_token={token}
   ```
5. **评论 3 篇**：选择不同的帖子或同一批帖子，写有见地的短评论（与帖子内容相关，体现行业研究员视角），每条之间间隔约 1 分钟
   ```
   npx mcporter call xiaohongshu-mcp.post_comment_to_feed account_id=bot7 feed_id={id} xsec_token={token} content={评论内容}
   ```

**评论风格要求：**
- 专业但口语化，像行内人随口聊天
- 不打广告、不引流、不说"关注我"
- 长度 20-80 字，言之有物
- 示例："存储涨价周期确实启动了，但 Q2 合约价兑现程度是关键变量"

**记录：** 完成后在 daily notes 中记录点赞和评论的帖子标题

---

### 5. 系统健康巡检（每次心跳）

检查浏览器进程是否有卡死的 renderer：
- 执行 `ps aux | grep "bot7/user-data" | grep renderer`，查看是否有 CPU >20% 且运行超过 10 分钟的进程
- 如有，`kill <PID>` 清理，记录到 daily notes
- 确保没有残留的 browser tab（残留 tab 会导致 renderer 卡死吃 CPU）

---

## 静默条件

以下情况 → 直接回复 `HEARTBEAT_OK`，不打扰用户：

- 没有到期的预测需要验证
- 距上次复盘未超过 30 天
- 所有行业观点在 60 天内均有更新
- 深夜（23:00-08:00）

---

## 最后复盘时间

_（初始化，尚未复盘）_

## 心跳汇报

心跳完成后，使用 `send_message` 工具将巡检结果发送给 `bot_main`（魏忠贤）。

- 一切正常 → 发送简短的 "HEARTBEAT_OK" + 状态摘要
- 发现异常 → 发送详细的异常报告
- 格式：`send_message(to="bot_main", content="[bot_id] 心跳汇报: ...")`
