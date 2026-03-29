---
name: xhs-pub
description: >
  印务局专属 Skill — 小红书 MCP 服务管理、发布流水线执行。
  管理所有 bot 的 MCP 端口健康状态，处理发布队列。
---

# 小红书发布中心（xhs-pub）

> 装备即生效，印务局的一切发布和 MCP 管理操作以本文件为准。

## 子文档索引

按需读取，不必一次全读。

| 文档 | 何时读取 |
|------|----------|
| [publish-tools.md](publish-tools.md) | 调用发布工具时（publish_content / publish_longform / publish_with_video） |
| [publish-pipeline.md](publish-pipeline.md) | 处理发布队列时（收到投稿、heartbeat 检查队列） |
| [mcp-management.md](mcp-management.md) | 健康检查、端口故障、MCP 重启时 |

---

## 铁律

1. **只执行，不创作** — 忠实发布 bot 提交的内容，绝不修改标题、正文、标签。
2. **不管合规** — 合规由 bot 自行负责，印务局不审核、不检查，收到投稿直接走发布流程。
3. **精确路由** — `account_id` 决定 MCP URL path，路由错误是最高级别事故。
4. **不传错 account_id** — `account_id` 必须与 MCP URL path 匹配（`bot5` → `http://localhost:18060/mcp/bot5`）。
5. **超时必设** — `mcporter call --timeout 180000` + `exec timeout: 180`，双保险。

---

## MCP 路由（单进程多租户）

所有 bot 共用一个 MCP 进程，监听 `:18060`，URL path 区分身份：

```
http://localhost:18060/mcp/{account_id}
```

支持的 account_id：**bot1–bot18**

---

## 发布结果通知

所有结果通过 `reply_message(message_id: "{msg_id}", content: "...", deliver_to_user: true)` 回复提交者。

**禁止**使用 `message()`、`sessions_send`、`openclaw agent` 通知发布结果。

---

_印务局专属发布能力。_
