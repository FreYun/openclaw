<!-- TOOLS_COMMON:START -->

---

## System Admin — Strictly Forbidden

**Only HQ (mag1) may execute these. All sub-bots are prohibited:**

- `openclaw gateway restart/stop/start`, `kill/pkill/killall`, `systemctl/service`
- `rm -rf`, `trash` on system directories or other bots' files

**Infrastructure issues (timeout, connection failure) → report to HQ, do not troubleshoot yourself.**

---

## Inter-Agent Communication (Message Bus)

### Rules

1. **Only channel**: `send_message` / `reply_message` / `forward_message` — no CLI calls, legacy `message()`, or shell scripts
2. **Every message must include `trace`** (provenance chain); `reply_message` auto-routes based on trace
3. **Strict single-round**: request → process → `reply_message` → **done**. One request = one reply. Put all data in the reply — never split into multiple messages

### Tools

| Tool | Purpose |
|------|---------|
| `send_message` | Start a new conversation/request |
| `reply_message` | Return results (defaults to Feishu user; add `also_notify_agent: true` to also wake upstream agent) |
| `forward_message` | Forward to another agent (trace auto-appended) |
| `get_message` / `list_messages` | Query message details / inbox |

### Trace Construction

```
send_message(to: "target_agent", content: "...", trace: [{
  agent: "your_account_id", session_id: "current_session_id",
  reply_channel: "feishu", reply_to: "ou_xxx", reply_account: "your_account_id"
}])
```

`reply_channel/reply_to/reply_account`: only set at the origin hop. Intermediate forwards auto-append trace.

### Incoming `[MSG:xxx]` Messages

`xxx` is the message_id → process → call `reply_message(message_id: "xxx", content: "all results here")` → done.

**Never use `[[reply_to_current]]` or plain text replies** — the sender won't receive them. Always `reply_message`, whether success or failure.

---

## Image Generation: image-gen-mcp

生图用 `image-gen-mcp.generate_image(style, content)`。模型可选 `banana`（默认）或 `banana2`。图片保存到 `/tmp/image-gen/` 下。

```
npx mcporter call 'image-gen-mcp.generate_image(style: "扁平插画风", content: "一只猫在看股票K线图")'
```

---

## Tool Priority

1. **memory** → check history first, update incrementally
2. **research-mcp** → financial data
3. **browser** → Xueqiu, EastMoney research reports, etc.
4. **MCP search** → supplementary search, overseas data
5. **xiaohongshu-mcp** → note management, interactions
6. **message bus** → inter-agent communication
<!-- TOOLS_COMMON:END -->






# TOOLS.md - 测试君工具配置


---

## Bot 专属配置

- **account_id：** bot10
- **小红书 MCP 端口：** 18070
- **MCP 服务名：** xiaohongshu-mcp

## 调用示例

```bash
# 检查登录状态
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'bot10')"

# 搜索
npx mcporter call "xiaohongshu-mcp.search_feeds(account_id: 'bot10', keyword: '测试关键词')"

# 获取笔记详情
npx mcporter call "xiaohongshu-mcp.get_feed_detail(account_id: 'bot10', feed_id: 'xxx', xsec_token: 'xxx')"

# 获取用户主页
npx mcporter call "xiaohongshu-mcp.get_user_profile(account_id: 'bot10', user_url: 'https://www.xiaohongshu.com/user/profile/xxx')"

# 创作者后台
npx mcporter call "xiaohongshu-mcp.get_creator_home(account_id: 'bot10')"

# 查看通知评论
npx mcporter call "xiaohongshu-mcp.get_notification_comments(account_id: 'bot10')"
```

## 测试发帖（必须仅自己可见）

发帖走 `skills/submit-to-publisher/SKILL.md` 流程，**visibility 必须填 `仅自己可见`**。

## 联网搜索

- 联网搜索通过 browser 工具访问搜索引擎或目标站点（使用前先读 `skills/browser-base/SKILL.md`）

## 合规服务

```bash
npx mcporter call "compliance-mcp.review_content(title: '标题', content: '内容', tags: '标签')"
```
