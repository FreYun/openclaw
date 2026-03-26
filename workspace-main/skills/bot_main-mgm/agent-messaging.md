# Agent 通讯手册

> 印务局的核心职责之一：接收 agent 投稿、处理后将结果准确回报。

## 消息总线架构

```
Bot (投稿者)
  ↓ submit-to-publisher.sh
  ↓ Redis: agentmsg:inbox:sys1 (XADD)
  ↓ openclaw agent --agent sys1 --message "[MSG:xxx]..."
  ↓
印务局 (sys1)
  ├─ 解析 [MSG:xxx] → 提取 message_id
  ├─ ACK 确认
  ├─ 处理发布队列
  └─ reply_message(message_id: "xxx", content: "结果", deliver_to_user: true)
      ↓ 自动沿 trace 路由
  研究部飞书 ← 结果通知
```

## 收到消息后的标准流程

### 1. 解析触发消息

```
[MSG:wQApFy8_sBdNOa3mt_pn8] 📮 新帖投稿：《标题》| 账号：bot5 | ...
```

提取 `message_id` = `wQApFy8_sBdNOa3mt_pn8`。

### 2. ACK 确认

立即回复队列位置，让提交者知道已收到：

```
reply_message(
  message_id: "wQApFy8_sBdNOa3mt_pn8",
  content: "📮 收到投稿 | 《标题》| 队列序号：#1，前面还有 0 个任务"
)
```

### 3. 处理完成后回报

```
reply_message(
  message_id: "wQApFy8_sBdNOa3mt_pn8",
  content: "📮 已发布 ✅ | 《标题》| 账号：bot5 | 可见性：公开可见",
  deliver_to_user: true
)
```

`deliver_to_user: true` 确保结果送达研究部飞书。

## 回报消息模板

| 结果 | 模板 |
|------|------|
| 成功 | `📮 已发布 ✅ \| 《{title}》\| 账号：{account_id} \| 可见性：{visibility}` |
| 失败 | `📮 发布失败 ❌ \| 《{title}》\| 原因：{reason}` |
| 暂停 | `📮 发布暂停 \| 《{title}》\| {account_id} 需要重新登录` |
| 合规打回 | `📮 合规未通过 \| 《{title}》\| 违规项：{violations}` |

## 通讯工具速查

| 工具 | 用途 | 何时用 |
|------|------|--------|
| `reply_message` | 沿 trace 回复消息 | **99% 的场景**。处理完 [MSG:xxx] 后回报结果 |
| `send_message` | 主动发起新对话 | 极少用。仅在没有 [MSG:xxx] 上下文时（如 heartbeat 发现问题需通知某 bot） |
| `forward_message` | 转发给另一个 agent | 几乎不用。印务局是终端执行者，不转发 |
| `get_message` | 查询消息详情 | 调试时用，查看消息状态和 trace |
| `list_messages` | 列出收件箱 | 检查积压时用 |

## ⛔ 禁止的通讯方式

- ❌ `message()` — 旧接口，不走消息总线，trace 丢失
- ❌ `sessions_send` — 内部接口，不要直接调用
- ❌ `openclaw agent --message` — 会创建新会话，不是回复
- ❌ 纯文本输出 — 提交者收不到

**永远用 `reply_message`**。它自动根据 trace 把结果送到正确的地方。

## Trace 机制

每条消息携带 trace 数组，记录消息的来源链：

```json
[{
  "agent": "bot5",
  "session_id": "uuid-of-session",
  "reply_channel": "feishu",
  "reply_to": "ou_db93023b3f5d5492af130c8a8a7320c4",
  "reply_account": "bot5"
}]
```

- `reply_channel: "feishu"` + `reply_to: "ou_xxx"` → 结果自动发到研究部飞书
- 印务局不需要构造 trace，只需 `reply_message` 即可，trace 已在消息中

## 主动通知其他 Agent

极少场景需要主动联系 agent（如发现某 bot 的 MCP 离线）：

```
send_message(
  to: "bot5",
  content: "⚠️ 你的 MCP 服务（端口 18065）已离线，请检查",
  trace: [{
    agent: "sys1",
    reply_channel: "feishu",
    reply_to: "ou_db93023b3f5d5492af130c8a8a7320c4",
    reply_account: "sys1"
  }]
)
```

注意：主动通知会唤醒目标 agent 的会话，谨慎使用。

## 印务局特殊关怀面板

当需要对某个 bot 的下一次投稿做特殊处理（如跳过合规、优先发布、特别审核等），直接编辑印务局的 MEMORY.md：

```
文件：/home/rooot/.openclaw/workspace-mcp-publisher/MEMORY.md
位置：## 特殊关怀面板 section 内
```

格式：
```markdown
### {botN} — {简要说明}
- **生效时间**：YYYY-MM-DD HH:MM
- **圣上旨意**：{具体指令}
- **有效期**：一次性 / 永久 / 至 YYYY-MM-DD
```

示例：
```markdown
### bot1 — 下次投稿免审直发
- **生效时间**：2026-03-26 15:00
- **圣上旨意**：bot1 下一次投稿跳过合规审核，直接发布
- **有效期**：一次性
```

印务局在处理每篇投稿前会检查此面板，匹配 `account_id` 后执行指令。一次性指令用后自动删除。
