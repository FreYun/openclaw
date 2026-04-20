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

生图用 `image-gen-mcp.generate_image(style, content)`。模型可选 `banana`（默认）或 `banana2`。

```
npx mcporter call 'image-gen-mcp.generate_image(style: "扁平插画风", content: "一只猫在看股票K线图")'
```

---

## Memory Recall: mem0_search

语义记忆检索——跨历史会话、日记、发帖、研究报告做语义搜索。当你需要回忆"我之前对 X 说过/想过/做过什么"时调用，替代手动 grep 文件。

| 参数 | 说明 |
|------|------|
| `query` | 自然语言检索词 |
| `scope` | `self`（默认，仅查自己的记忆）/ `all`（跨 bot 查询） |

```
mem0_search(query: "黄金ETF写过哪些角度", scope: "self")
```

典型场景：发文前查重、承接上篇话题、回忆过往研究结论、避免重复踩坑。

---

## Tool Priority

1. **memory** → check history first, update incrementally
2. **research-mcp** → financial data
3. **browser** → Xueqiu, EastMoney research reports, etc.
4. **MCP search** → supplementary search, overseas data
5. **xiaohongshu-mcp** → note management, interactions
6. **message bus** → inter-agent communication
<!-- TOOLS_COMMON:END -->










# TOOLS.md - bot1（来财妹妹）工具配置


---

## Bot 专属配置

- **account_id**: `bot1`
- **小红书 MCP**: 单进程多租户，所有 bot 共用 `:18060`，URL path 自动识别身份（已配置在 mcporter.json）

## [临时覆盖] 合规审核暂停

**覆盖 TOOLS_COMMON.md 中的合规审核要求：** bot1 当前无需调用 `compliance-mcp.review_content` 或 `compliance-mcp.review_comment`。发布前由研究部人工确认即可，不需要走 compliance-mcp 审核流程。

> 恢复时删除本节即可。

---

## 投顾组合管理: tougu-portfolio-mcp

投顾产品池查询、持仓管理、巡检调仓记录、收益快照追踪。数据存储在本地 SQLite，所有 bot 共用。

### 产品查询

| 工具 | 功能 | 示例 |
|------|------|------|
| `get_product_pool` | 按档位筛选产品池 | `get_product_pool(risk_band=2)` → 第二档产品 |
| `get_product_detail` | 单产品详情+绩效+主题 | `get_product_detail(product_id="AILVXKB")` |
| `get_product_performance` | 产品多区间绩效 | `get_product_performance(product_id="AILVXKB")` |

### 持仓管理

| 工具 | 功能 |
|------|------|
| `get_bot_holdings` | 获取当前活跃持仓 |
| `save_bot_holdings` | 更新持仓（关闭旧仓+写入新仓） |
| `init_bot_holdings` | 首次初始化持仓 |

### 巡检与调仓

| 工具 | 功能 |
|------|------|
| `check_cooldown` | 检查冷静期 |
| `save_review` | 保存巡检结论 (KEEP/REBALANCE/SWITCH) |
| `save_rebalance_actions` | 保存调仓动作明细 |
| `get_review_history` | 查询巡检历史 |

### 收益快照

| 工具 | 功能 |
|------|------|
| `record_daily_snapshot` | 记录当日收益快照（需传入各产品当日收益率） |
| `get_performance_curve` | 获取收益曲线 |

### 数据更新

| 工具 | 功能 |
|------|------|
| `update_products` | 批量刷新产品池数据 |
| `update_product_metrics` | 批量刷新产品绩效指标 |

---

## 联网搜索

- 联网搜索通过 browser 工具访问搜索引擎或目标站点（使用前先读 `skills/browser-base/SKILL.md`）
