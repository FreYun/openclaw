<!-- TOOLS_COMMON:START -->

---

## Xiaohongshu (XHS) Operations

**Must `Read skills/xhs-op/mcp-tools.md` before any XHS operation. No SKILL.md = guaranteed failure.**

- Call via `npx mcporter call "xiaohongshu-mcp.tool_name(...)"` — never `curl` the port directly
- `account_id` rule: **no tool accepts `account_id`** — identity is determined by port. Passing it causes errors. Only exception: `publish_content` (optional)
- Publishing goes through the publisher (`skills/submit-to-publisher/SKILL.md`); compliance review is handled there
- On timeout: check login status first; if logged out, follow SKILL.md Step 0; if mcporter reports `offline`, report to HQ
- Never retry timed-out operations repeatedly; never start/compile/modify MCP source code

---

## ⛔ System Admin — Strictly Forbidden

**Only HQ (mag1) may execute these. All sub-bots are prohibited:**

- `openclaw gateway restart/stop/start`, `kill/pkill/killall`, `systemctl/service`
- `rm -rf`, `trash` on system directories or other bots' files

**Infrastructure issues (timeout, connection failure) → report to HQ, do not troubleshoot yourself.**

---

## Web Browsing

- **Must pass `profile: "your_account_id"`** — omitting it causes timeout
- On launch failure → `bash /home/rooot/.openclaw/scripts/ensure-browser.sh your_account_id`
- **`browser close` is mandatory after every task, success or failure** — no exceptions. Stale tabs accumulate across sessions and spike CPU. Any skill that opens a browser must close it before finishing.
- `ref` is only valid for the current snapshot; re-snapshot after page changes
- No Chrome extensions; don't retry timeouts repeatedly
- Before starting: run `browser tabs profile="your_account_id"` to check for stale tabs from previous sessions, close any you find
- **On browser timeout / "can't reach browser control service"**: do NOT fall back to web_fetch immediately. First run `bash /home/rooot/.openclaw/scripts/ensure-browser.sh your_account_id` to start Chrome, then retry the browser tool once. Only fall back if it still fails after that.

---

## Financial Data: Research MCP

直连 **research-mcp**，92 个金融数据工具，分 10 个类别。

调用：`npx mcporter call "research-mcp.tool_name(...)"`

**使用前必须 `Read skills/research-mcp/SKILL.md`**，根据意图路由表找到对应子模块（fund.md / stock.md / market.md / bond.md / macro.md / news.md），再 Read 子模块获取具体工具的参数和用法。

10 个工具箱：`market_ashares`(8) · `market_hk`(6) · `market_us`(5) · `stock`(29) · `fund`(22) · `fund_screen`(7) · `bond`(5) · `macro`(3) · `commodity`(2) · `news_report`(5)

---

## Inter-Agent Communication (Message Bus)

### Rules

1. **Only channel**: `send_message` / `reply_message` / `forward_message` — no CLI calls, legacy `message()`, or shell scripts
2. **Every message must include `trace`** (provenance chain); `reply_message` auto-routes based on trace
3. **⛔ Strict single-round**: request → process → `reply_message` → **done**. One request = one reply. Put all data in the reply — never split into multiple messages

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

### ⛔ Incoming `[MSG:xxx]` Messages

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
2. **research-mcp** → financial data (Read SKILL.md first)
3. **browser** → Xueqiu, EastMoney research reports, etc.
4. **MCP search** → supplementary search, overseas data
5. **xiaohongshu-mcp** → note management, interactions
6. **message bus** → inter-agent communication
<!-- TOOLS_COMMON:END -->



# TOOLS.md - 技能部工具配置

## 身份

- **Agent ID：** `skills`
- **职能：** Skill 与 MCP 插件目录管理

---

## 关键路径

| 路径 | 说明 |
|------|------|
| `/home/rooot/.openclaw/workspace/skills/` | 共有 skill 源目录 |
| `/home/rooot/.openclaw/workspace-botN/skills/` | 各 bot 的 skill 目录（含 symlink）|
| `memory/shared-skills.md` | 共有 skill 目录（自动生成）|
| `memory/private-skills.md` | 私有 skill 目录（自动生成）|
| `memory/plugins.md` | MCP 插件配置清单（自动生成）|
| `memory/sync-status.md` | symlink 同步状态（自动生成）|

---

## 刷新目录

```bash
python3 ~/.openclaw/workspace-skills/scripts/update-inventory.py
```

---

## 常用查询命令

```bash
# 列出所有共有 skill
ls /home/rooot/.openclaw/workspace/skills/

# 检查 symlink 完整性（哪些 bot 缺少哪些 skill）
python3 -c "
import os
src = '/home/rooot/.openclaw/workspace/skills'
skills = [s for s in os.listdir(src) if os.path.isdir(os.path.join(src, s))]
for skill in sorted(skills):
    missing = [f'bot{i}' for i in range(1,11)
               if not os.path.exists(f'/home/rooot/.openclaw/workspace-bot{i}/skills/{skill}')]
    if missing: print(f'[缺失] {skill}: {missing}')
"

# 新增共有 skill 的 symlink（所有 bot）
SKILL=新skill名
for i in 1 2 3 4 5 6 7 8 9 10; do
  ln -s ../../workspace/skills/$SKILL /home/rooot/.openclaw/workspace-bot${i}/skills/$SKILL
done
```

---

## MCP 插件查询

```bash
# 查看某 bot 的 MCP 插件配置
cat /home/rooot/.openclaw/workspace-botN/config/mcporter.json
```

---

## Skill 网关（主网关）

技能部拥有并维护一个 MCP 聚合网关，所有 bot 通过它访问研究数据等共享工具。

| 项目 | 值 |
|------|------|
| 代码目录 | `/home/rooot/.openclaw/research-mcp/` |
| 端口 | `18080` |
| 权限配置 | `/home/rooot/.openclaw/research-mcp/permissions.yaml` |
| 日志 | `/tmp/research-mcp.log` |
| PID | `/tmp/research-mcp.pid` |

### 网关管理

```bash
# 启动/停止/重启/状态/日志
bash /home/rooot/.openclaw/research-mcp/run.sh start
bash /home/rooot/.openclaw/research-mcp/run.sh stop
bash /home/rooot/.openclaw/research-mcp/run.sh restart
bash /home/rooot/.openclaw/research-mcp/run.sh status
bash /home/rooot/.openclaw/research-mcp/run.sh log

# 健康检查
curl -s http://localhost:18080/health | python3 -m json.tool

# 查看所有 bot 路由
curl -s http://localhost:18080/
```

### 权限管理

编辑 `permissions.yaml`，修改角色定义或 bot→角色映射。配置变更在**下一次网关重启时生效**（无需立即重启）：

```bash
vim /home/rooot/.openclaw/research-mcp/permissions.yaml
# 配置保存后，下次网关重启自动加载
# 如需立即生效：bash /home/rooot/.openclaw/research-mcp/run.sh restart
```

各 bot 连接方式（已自动配置到 mcporter.json）：
```
http://localhost:18080/mcp/{bot_id}
```

### 当前角色

| 角色 | 工具数 | bot |
|------|--------|-----|
| full_access | 10 | bot7, bot8 |
| content_creator | 4 | bot1-4, bot6, bot9-10 |
| fund_advisor | 8 | bot5 |
| admin | 11 | mag1, skills |

### 权限申请处理

```bash
# 查看 bot 当前权限信息
bash ~/.openclaw/workspace-skills/scripts/handle-permission-request.sh <bot_id> <tool1,tool2>

# 修改权限后重启网关
vim /home/rooot/.openclaw/research-mcp/permissions.yaml
bash /home/rooot/.openclaw/research-mcp/run.sh restart
```

### 变更记录

变更日志：`memory/changelog.md`
权限申请记录：`memory/permission-requests.md`
