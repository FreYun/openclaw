# AGENTS.md — Publisher Runbook

## On Wake

Read in order before any work:
1. `../workspace/SOUL_COMMON.md` → `SOUL.md` → `../workspace/TOOLS_COMMON.md` → `TOOLS.md`
2. `memory/status.md` — bot/MCP health
3. `memory/YYYY-MM-DD.md` (today)
4. `../workspace/skills/xiaohongshu-mcp/SKILL_publish.md` — publish API ref

## Wake Triggers

| Trigger | Action |
|---------|--------|
| `[MSG:xxx]` submission | Extract msg_id → ACK queue position → process queue |
| Heartbeat | Run HEARTBEAT.md |
| Admin command | Execute as instructed |

ACK on receipt:
```
reply_message(message_id: "{msg_id}", content: "📮 收到投稿 | 《{title}》| 队列序号：#{N}，前面还有 {M} 个任务")
```

---

## Publish Pipeline

`pending/ → parse → validate → lock → compliance → login check → publish → archive → log`

Process all entries serially, oldest first, no limit.

### 1. Parse

Folder format (new): read `post.md` + scan media files. `.md` file (legacy): read directly.
Parse YAML frontmatter + body (everything after `---`).

Field mapping:
- `text_to_image`: `content` param = frontmatter `content` (fallback: body); `text_content` = body
- Other modes (`image`/`longform`/`video`): `content` param = body

### 2. Validate

- `account_id` must be bot1–bot10
- `title` non-empty, ≤20 Chinese chars
- body non-empty
- `text_to_image`: card count (`\n\n` separated) ≤ 3
- **Rate limit** (bot10 exempt): same account cannot publish within 15min — check `memory/发帖记录.md`

Fail → `rm -rf` entry → notify submitter → log.

### 2.5. Tag Normalization (auto-fix)

Before publishing, normalize the `tags` array:

1. **Split comma-stuffed tags**: if any single tag string contains `，` (Chinese comma) or `,` (English comma), split it into separate tags and trim whitespace
   - e.g. `["英伟达", "AI 算力，光模块，商业航天"]` → `["英伟达", "AI 算力", "光模块", "商业航天"]`
2. **Strip leading `#`**: remove `#` prefix if present
3. **Deduplicate**: remove exact duplicates, preserve order
4. **Cap at 5 tags**: XHS allows max 5 topic tags; keep first 5, drop the rest
5. **Log if modified**: if tags were changed, log the before/after in daily journal

This step is silent — no need to notify the submitter. Just fix and continue.

### 3. Lock

```bash
mv pending/${entry} publishing/${entry}
```
mv fails (entry gone) → another session handling it, skip silently.

### 4. Compliance

```bash
npx mcporter call "compliance-mcp.review_content(title: '...', content: '...', tags: '...')"
```
- Pass → continue
- Fail → delete entry → notify with violations + fix suggestions
- Service down → delete entry → notify "compliance offline, resubmit later"

### 5. Login Check

```bash
ss -tlnH "sport = :{port}" | grep -q "{port}" && curl -s --connect-timeout 3 --max-time 5 http://localhost:{port}/health
npx mcporter call "xhs-{account_id}.check_login_status(account_id: '{account_id}')"
```
- Offline → attempt restart → still down: delete entry, notify submitter only (NO Feishu group)
- **Only `isCreatorLoggedIn` matters** — ignore main site login status
- Not logged in → `mv` back to `pending/` → notify submitter to handle login

### 6. Publish

> **Timeout rule**: ALWAYS set both layers:
> - `mcporter call --timeout 180000`
> - `exec` timeout: 180, yieldMs: 170000

**text_to_image:**
```bash
npx mcporter call --timeout 180000 "xhs-{aid}.publish_content(account_id:'{aid}', title:'{t}', content:'{c}', text_content:'{body}', text_to_image:true, image_style:'{style}', tags:[...], visibility:'{v}', is_original:{bool}, schedule_at:'{sa}')"
```

**image:**
```bash
npx mcporter call --timeout 180000 "xhs-{aid}.publish_content(account_id:'{aid}', title:'{t}', content:'{body}', text_to_image:false, images:['/abs/path/1.jpg',...], tags:[...], visibility:'{v}', is_original:{bool}, schedule_at:'{sa}')"
```

**longform:**
```bash
npx mcporter call --timeout 180000 "xhs-{aid}.publish_longform(account_id:'{aid}', title:'{t}', content:'{body}', tags:[...], visibility:'{v}')"
```

### 7. Archive

- Success → `mv publishing/${entry} published/${entry}`, append `published_at` timestamp
- Failure:
  - SIGTERM / timeout → **NO retry** (server may still be executing)
  - Clear MCP error → wait 60s, retry once (check_login_status first)
  - "Another operation in progress" → **NO retry**
  - Still fails → `rm -rf` → notify submitter

### 8. Log

Every submission (success or failure):
```bash
python3 ~/.openclaw/scripts/log-publish.py --bot {account_id} --title "{title}" --opinion "{opinion}" --status "{status}"
```
Status values: `✅ 已发布` / `❌ 失败` / `⏸️ 暂停`

Also update `memory/YYYY-MM-DD.md` daily journal.

---

## Notification Rules

All publish results **must** use `reply_message`:
```
reply_message(message_id: "{msg_id}", content: "📮 {result}", deliver_to_user: true)
```

Templates:
- `📮 已发布 ✅ | 《{title}》| 账号：{account_id} | 可见性：{visibility}`
- `📮 发布失败 ❌ | 《{title}》| 原因：{reason}`
- `📮 发布暂停 | 《{title}》| {account_id} 需要重新登录`

**NEVER** use `message()`, `sessions_send`, or `openclaw agent` for publish results. Use `send_message` if no `[MSG:xxx]` prefix.

**Feishu group alerts**: heartbeat infra issues ONLY. Publish errors → notify submitter bot only.

## schedule_at

Empty/expired → publish immediately. Future time → pass to MCP (XHS range: 1h–14d).

## Memory

- `memory/YYYY-MM-DD.md` — daily journal
- `memory/发帖记录.md` — all submissions table (via log-publish.py)
- `MEMORY.md` — long-term lessons

## Safety

- Never modify post content
- Never mix up account_id routing
- Never use `公开可见` for testing
- MCP calls via `npx mcporter call` only
- See SOUL.md
