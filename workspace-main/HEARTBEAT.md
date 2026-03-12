# HEARTBEAT.md - 管理员巡检清单

## 核心任务：小红书登录状态巡检

每次心跳（每 3 小时）检查 bot1、bot4、bot5、bot7 的小红书登录状态，并将结果播报到飞书群。

### 执行步骤

1. **确认 MCP 服务在线**

```bash
curl -s http://localhost:18060/health
```

若服务离线，先尝试启动：
```bash
nohup /tmp/xhs-mcp -headless=true -port=:18060 > /tmp/xiaohongshu-mcp.log 2>&1 &
sleep 3 && curl -s http://localhost:18060/health
```

2. **逐个检查登录状态**

```bash
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'bot1')"
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'bot4')"
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'bot5')"
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'bot7')"
```

3. **生成播报消息**

根据检查结果生成简洁的状态报告，格式如下：

```
⚙️ 小红书登录状态巡检

bot1（来财妹妹）：✅ 主站已登录 / ✅ 创作者已登录
bot4（研报搬运工阿泽）：✅ 主站已登录 / ✅ 创作者已登录
bot5（宣妈慢慢变富）：✅ 主站已登录 / ❌ 创作者未登录
bot7（老K投资笔记）：✅ 主站已登录 / ✅ 创作者已登录

⏰ 检查时间：YYYY-MM-DD HH:MM
```

- ✅ 表示已登录
- ❌ 表示未登录或 cookie 失效，需要重新扫码

4. **发送到飞书群**

使用 `message(action="send", message="...")` 将状态报告发送到当前飞书群。

### 异常处理

- 如果 MCP 服务无法启动，播报服务离线状态
- 如果某个 bot 检查超时，标记为 ⚠️ 检查超时
- 如果所有 bot 都正常，仍然播报（确认正常也是重要信息）

## 频率控制

- **最短间隔 3 小时**：如果距离上次巡检播报不到 3 小时，直接回复 `HEARTBEAT_OK`，不执行巡检
- 判断方法：检查飞书群中最近一条巡检消息的时间戳，如果距现在 < 3 小时则跳过
- 非定时唤醒（exec 事件等触发的）不需要执行巡检，直接回复 `HEARTBEAT_OK`

## 静默条件

- **仅在 08:30–23:30 之间执行巡检**，其余时间直接回复 `HEARTBEAT_OK`
- 即：00:00–08:29 和 23:31–23:59 不执行，不打扰
