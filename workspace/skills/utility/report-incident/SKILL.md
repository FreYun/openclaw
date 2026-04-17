---
name: report-incident
description: 异常上报技能 — 当发生运行时异常时，记录事件并通知魏忠贤（mag1）。适用于 MCP 超时、登录失败、发帖错误、skill 执行错误等。当你遇到需要上报的异常时调用此 skill。
---

# 安全异常上报

将异常记录写入 `/home/rooot/.openclaw/security/incidents.jsonl`。

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

**写入安全日志**

```bash
python3 -c "
import json, datetime  # ⚠️ message ≤50字；context 可选
r = {'ts': datetime.datetime.now().astimezone().isoformat(), 'reporter': '<bot_id>', 'session_id': '<session_id>', 'level': '<ERROR|WARNING>', 'type': '<类型>', 'message': '<≤50字描述>', 'context': {}}
open('/home/rooot/.openclaw/security/incidents.jsonl', 'a').write(json.dumps(r, ensure_ascii=False) + '\n')
"
```

> ERROR 和 WARNING 均只写文件，由 mag1 心跳巡检统一处理。

---

## 示例

**ERROR（MCP 超时）**：

```bash
python3 -c "
import json, datetime
r = {'ts': datetime.datetime.now().astimezone().isoformat(), 'reporter': 'bot7', 'session_id': 'abc12345', 'level': 'ERROR', 'type': 'MCP_TIMEOUT', 'message': 'get_feeds端口18067无响应，等待45秒后放弃', 'context': {'tool': 'get_feeds', 'port': 18067}}
open('/home/rooot/.openclaw/security/incidents.jsonl', 'a').write(json.dumps(r, ensure_ascii=False) + '\n')
"
```

---

## 上报后的行为

上报后继续工作；ERROR 致任务中断时，简短告知研究部。

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
