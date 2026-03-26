---
name: report-incident
description: 异常上报技能 — 当发生运行时异常时，记录事件并通知魏忠贤（mag1）。适用于 MCP 超时、登录失败、发帖错误、skill 执行错误等。当你遇到需要上报的异常时调用此 skill。
---

# 安全异常上报

将异常记录写入 `/home/rooot/.openclaw/security/incidents.jsonl`，ERROR 级别通过消息插件通知魏忠贤（mag1）。

---

## 何时上报

以下情况**必须上报**：

| 类型 | 触发场景 |
|------|---------|
| `MCP_TIMEOUT` | mcporter 调用 xiaohongshu-mcp 工具超时（>30秒）|
| `MCP_ERROR` | MCP 工具返回错误（连接失败、服务不可达）|
| `LOGIN_REQUIRED` | 检测到 cookie 失效、需要重新扫码登录 |
| `PUBLISH_FAILED` | 发帖操作失败（技术性失败，非内容审核）|
| `SKILL_ERROR` | skill 执行中遭遇未预期的严重错误 |
| `BROWSER_CRASH` | 浏览器崩溃、页面无响应、Rod 操作超时 |
| `RATE_LIMITED` | 被小红书限流或封禁 |
| `COMPLIANCE_BLOCK` | 内容合规审核拦截（记录规律，供安全部分析）|
| `OTHER` | 其他严重异常 |

以下情况**不需要上报**：
- 搜索无结果
- 用户主动取消操作
- 轻微网络抖动（已自动恢复）
- 内容写作过程中的普通重试

---

## 上报方法

**第一步：写入安全日志**

```bash
python3 -c "
import json, datetime, subprocess, sys

# ⚠️ message 字段不超过 50 字
record = {
    'ts': datetime.datetime.now().astimezone().isoformat(),
    'reporter': '【你的 account_id，如 bot7】',
    'session_id': '【必填！当前会话 ID，从系统上下文中获取】',
    'level': '【ERROR 或 WARNING】',
    'type': '【类型，如 MCP_TIMEOUT】',
    'message': '【一句话描述，≤50字】',
    'context': {
        # 可选：出错工具名、端口、账号等关键信息
    }
}

with open('/home/rooot/.openclaw/security/incidents.jsonl', 'a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')

print('已写入安全日志')
"
```

**第二步：通知魏忠贤（ERROR 级别必须执行）**

使用系统消息插件：

```
send_message(
  to: "mag1",
  content: "【异常上报】reporter=<你的bot_id> session=<session_id> type=<类型> level=ERROR msg=<问题描述≤50字>",
  trace: [{ agent: "<你的bot_id>" }]
)
```

> WARNING 级别可只写文件，不必通知；ERROR 级别必须两步都执行。

---

## 完整示例

### 示例 1：MCP 超时（ERROR）

```bash
python3 -c "
import json, datetime
record = {
    'ts': datetime.datetime.now().astimezone().isoformat(),
    'reporter': 'bot7',
    'session_id': 'abc12345',
    'level': 'ERROR',
    'type': 'MCP_TIMEOUT',
    'message': 'get_feeds 端口18067无响应，等待45秒后放弃',
    'context': {'tool': 'get_feeds', 'port': 18067}
}
with open('/home/rooot/.openclaw/security/incidents.jsonl', 'a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')
print('已写入安全日志')
"

# 然后用消息插件通知魏忠贤
send_message(
  to: "mag1",
  content: "【异常上报】reporter=bot7 type=MCP_TIMEOUT level=ERROR msg=get_feeds端口18067无响应，等待45秒后放弃",
  trace: [{ agent: "bot7" }]
)
```

### 示例 2：登录失效（ERROR）

```bash
python3 -c "
import json, datetime
record = {
    'ts': datetime.datetime.now().astimezone().isoformat(),
    'reporter': 'bot5',
    'session_id': 'xyz98765',
    'level': 'ERROR',
    'type': 'LOGIN_REQUIRED',
    'message': 'bot5小红书cookie已失效，get_user_profile返回登录页',
    'context': {'account_id': 'bot5', 'port': 18065}
}
with open('/home/rooot/.openclaw/security/incidents.jsonl', 'a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')
print('已写入安全日志')
"

# 然后用消息插件通知魏忠贤
send_message(
  to: "mag1",
  content: "【异常上报】reporter=bot5 type=LOGIN_REQUIRED level=ERROR msg=bot5小红书cookie已失效",
  trace: [{ agent: "bot5" }]
)
```

### 示例 3：合规拦截（WARNING，只写文件）

```bash
python3 -c "
import json, datetime
record = {
    'ts': datetime.datetime.now().astimezone().isoformat(),
    'reporter': 'bot1',
    'session_id': 'sess-001',
    'level': 'WARNING',
    'type': 'COMPLIANCE_BLOCK',
    'message': '发帖含「涨停」被合规拦截，草稿已放弃',
    'context': {'blocked_keyword': '涨停'}
}
with open('/home/rooot/.openclaw/security/incidents.jsonl', 'a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')
print('已写入安全日志')
"
```

---

## 上报后的行为

- **上报完成后继续工作**，不要等待回复
- ERROR 级别如导致当前任务中断，飞书群简短告知研究部
- 魏忠贤（mag1）会收到通知并决定是否升级处理

---

## 字段规范

| 字段 | 要求 |
|------|------|
| `reporter` | 你的 account_id（如 bot7） |
| `session_id` | 当前会话 ID；不确定时填 `unknown` |
| `level` | 只能是 `ERROR` 或 `WARNING` |
| `type` | 用上方表格中的类型 |
| `message` | **中文，≤50字**，一句话说清楚发生了什么 |
| `context` | 关键上下文，不要粘贴超长错误堆栈 |

不要重复上报同一异常（同一次失败只报一次）。
