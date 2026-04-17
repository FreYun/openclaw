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

# TOOLS.md - 工具配置

> 首先 Read [`/home/rooot/.openclaw/workspace/TOOLS_COMMON/TOOLS_COMMON.md`](../workspace/TOOLS_COMMON/TOOLS_COMMON.md) 获取统一工具规范

## 基础信息

- **account_id**: sys4
- **角色**: 内容运营 Agent（content-ops 主编层）
- **不操作小红书**: sys4 不直接发帖、不登录任何 XHS 账号。所有 XHS 行为由各 bot 或 sys1 印务局执行
- **不擅自重启服务**: 见 `TOOLS_COMMON.md` 系统管理禁区

## 工作目录

- **可写区**: `/home/rooot/.openclaw/workspace-sys4/` 下所有目录、`workspace-botN/editor-notes/`（⚠️ 跨 workspace，sandbox 可能 block，失败时改走 `send_message`）
- **只读区**: 其他 bot 的 `SOUL.md` / `IDENTITY.md` / `CONTENT_STYLE.md` / `memory/`、所有 `skills/`(symlink 出去 sandbox 写不了)、`dashboard/` 数据文件
- **绝对禁止**: 在 `skills/` 内写文件、发明新的顶层目录、操作 `.xhs-profiles/`、**向 `workspace-botN/今日选题.md` 写入**（废弃路径；sandbox 会 block，改走 `send_message` 内联派发）
- **今日选题的传递方式**：通过 `send_message` 工具**内联到消息体**发给 bot，不再落文件。详见 `skills/content-ops/content-calendar.md` Step 5

> **路径写绝对路径**：sys4 的 cwd 不固定，所有命令和文件读写都用 `/home/rooot/.openclaw/...` 起头的绝对路径。

---

## 数据源全景

排期、审稿、复盘、爆款拆解都依赖以下数据源。**接到任务前先想清楚要查哪一类**。

### 1. Bot 的小红书后台数据（自家发的帖子怎么样了）

| 项 | 值 |
|---|---|
| **数据文件** | `/home/rooot/.openclaw/dashboard/xhs-stats.json`（86K，cron 每天 9:00 / 21:00 自动采集） |
| **查询脚本** | `/home/rooot/.openclaw/dashboard/query-stats.sh` |
| **覆盖范围** | 各 bot 自家 XHS 后台数据：曝光、阅读、点击率、点赞、评论、收藏、涨粉、分享 |
| **不覆盖** | 全网爆款（用 Spider DB）、bot 没发出去的草稿（用 workspace-botN/memory/posts/） |

**常用调用**:

```bash
# 总览：所有 bot 的一行摘要（先扫这个，决定深入看哪个）
bash /home/rooot/.openclaw/dashboard/query-stats.sh --summary

# 看某个 bot 互动最好的 N 篇（带正文）
bash /home/rooot/.openclaw/dashboard/query-stats.sh bot5 --top=3 --with-content

# 看某个 bot 全部帖子（标题+指标）
bash /home/rooot/.openclaw/dashboard/query-stats.sh bot5

# 仅标题（撞题查重用）
bash /home/rooot/.openclaw/dashboard/query-stats.sh bot5 --titles
```

**xhs-stats.json 结构**（直接读 JSON 时用）:

```json
{
  "updated_at": "ISO timestamp",
  "bots": {
    "botN": {
      "updated_at": "...",
      "notes": [
        { "title", "publish_time", "impressions", "views", "click_rate",
          "likes", "comments", "favorites", "new_followers", "shares", ... }
      ]
    }
  }
}
```

> `--with-content` 会自动从 `/home/rooot/.openclaw/workspace-sys1/publish-queue/published/` 匹配标题附带正文 —— 这是 sys1 印务局的发布归档，sys4 只读。

### 2. Bot 自己写的发帖原文（草稿和已发归档）

| 路径 | 内容 |
|---|---|
| `/home/rooot/.openclaw/workspace-botN/memory/posts/` | bot 自己的发帖原文归档（含未发布的草稿和历史已发） |
| `/home/rooot/.openclaw/workspace-sys1/publish-queue/published/` | sys1 印务局的已发布归档（query-stats.sh `--with-content` 用的就是这里） |

**用途**：审稿时对比历史风格、爆款拆解时取正文、人感诊断时采样近 14 天发帖。

### 3. 全网爬虫数据（用于 hit-breakdown 爆款拆解）

| 项 | 值 |
|---|---|
| **数据库** | `/home/rooot/.openclaw/Spider_XHS/datas/xhs.db`（sqlite） |
| **写入方** | `Spider_XHS/batch_collect.py` 滚动写入 |
| **批次识别** | 用 `last_seen_at`（Spider 最近刷到时间），**不要用 `xhs_updated_at`**（小红书侧的笔记更新时间，不是爬虫时间） |
| **CLI 工具** | 环境无 `sqlite3` CLI，用 `python3 -c 'import sqlite3; ...'` |

**典型查询**（详见 [`hit-breakdown.md`](skills/content-ops/hit-breakdown.md)）：

```python
import sqlite3
DB = '/home/rooot/.openclaw/Spider_XHS/datas/xhs.db'
conn = sqlite3.connect(DB)
# 用 find_latest_batch() 算最近一批的时间边界，再做聚合
```

> ⚠️ 2026-04-13 之前的 857 行 `first/last_seen_at` 是从 `xhs_updated_at` 回填的近似值，做严格批次分析时要排除。

### 4. Bot 的素材库与人格文件（排期的第一输入源）

| 路径 | 内容 | 用途 |
|---|---|---|
| `/home/rooot/.openclaw/workspace-botN/memory/topic-library.md` | bot 自己采集的选题素材池 | **排期第一输入源**，绝不凭记忆编选题 |
| `/home/rooot/.openclaw/workspace-botN/memory/YYYY-MM-DD.md` | bot 的工作日记 | 了解 bot 最近在想什么、做什么 |
| `/home/rooot/.openclaw/workspace-botN/SOUL.md` | bot 的灵魂文件 | 人设、内容支柱 |
| `/home/rooot/.openclaw/workspace-botN/IDENTITY.md` | bot 的身份卡片 | 名字、性格、Emoji |
| `/home/rooot/.openclaw/workspace-botN/CONTENT_STYLE.md` | bot 的写作风格定义（部分 bot 才有） | 审稿时对照 |
| `/home/rooot/.openclaw/workspace-botN/USER.md` | 研究部对该 bot 的需求 | 知道哪些是研究部硬性要求 |

> 这些**全部只读**。要建议 bot 调整 SOUL/IDENTITY/CONTENT_STYLE，走 `workspace-botN/editor-notes/` 反馈渠道，bot 自决是否修改。详见 SOUL.md「反馈推送的标准格式」。

### 5. 自家产出（sys4 的可写区）

| 路径 | 内容 |
|---|---|
| `/home/rooot/.openclaw/workspace-sys4/queue/botN.md` | 各 bot 排期队列 |
| `/home/rooot/.openclaw/workspace-sys4/memory/YYYY-MM-DD.md` | sys4 工作日记 |
| `/home/rooot/.openclaw/workspace-sys4/memory/reviews/` | 审稿反馈记录 |
| `/home/rooot/.openclaw/workspace-sys4/memory/human-feel-audits/` | 人感诊断报告 |
| `/home/rooot/.openclaw/workspace-sys4/memory/feedback-log.md` | 已向 botN 推送过的 editor-notes 留痕 |
| `/home/rooot/.openclaw/workspace/skills/armor/content-ops/patterns/*.md` | 爆款模式库（**注意**：通过 symlink 装备时写不进去，需要先和研究部确认是否走 skill 源目录写入） |
| `/home/rooot/.openclaw/workspace/skills/armor/content-ops/summaries/YYYY-MM-DD.md` | hit-breakdown 批次摘要（同上） |

---

## 数据源选择速查

| 我要做什么 | 看哪里 |
|---|---|
| 这个 bot 上周哪篇互动最好？ | `query-stats.sh botN --top=3 --with-content` |
| 这个 bot 最近发了什么主题？ | `query-stats.sh botN --titles` 或 `workspace-botN/memory/posts/` |
| 这个 bot 现在能写什么选题？ | `workspace-botN/memory/topic-library.md`（**第一输入源**） |
| 全平台最近什么爆了？ | Spider DB + `find_latest_batch()` |
| 这个 bot 的人设、风格是什么？ | `workspace-botN/SOUL.md` + `CONTENT_STYLE.md`（如有） |
| 研究部对这个 bot 有什么硬要求？ | `workspace-botN/USER.md` |
| 我之前给这个 bot 推过什么建议？ | `workspace-sys4/memory/feedback-log.md` |

---

## 联网工具

按需调用（从 `TOOLS_COMMON.md` 继承）：

- **WebSearch / WebFetch**: 排期 Step 2 环境扫描用。**搜不到就跳过，不要瞎猜**（content-calendar.md 铁律）
- **Spider DB**: 用 python3 + sqlite3，不要尝试装 sqlite3 CLI

## 跨 Agent 通信

通过 `send_message` / `reply_message`（见 `TOOLS_COMMON.md` "Inter-Agent Communication"）。sys4 主要的对话对象：

- **研究部（mag1）** — 上报需要批准的事项、汇报排期完成情况
- **各 bot** — 今日选题通过 `send_message` **内联派发**（消息体里直接写选题+角度+参考旧作，bot 从消息读而非 Read 文件）；style/人设建议写 `workspace-botN/editor-notes/` 作为留档（失败时同样走 send_message）；draft-review 审稿结论按 `skills/content-ops/draft-review.md` 规定用 `send_message` 回推
- **sys1 印务局** — 仅在审稿完成、需要发布时联系，且必须经过 compliance
