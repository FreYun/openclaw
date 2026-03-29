# Directory - Wei Zhongxian's Contacts

> Department contacts at a glance. Route by department, don't cross wires.
> Message agents via `send_message(to: "<agent_id>", ...)`.

---

## 1. Security Department

| Field | Value |
|-------|-------|
| **Agent ID** | `security` |
| **Workspace** | `workspace-security/` |
| **Function** | Runtime incident intake & archival, escalate ERROR-level to mag1 |
| **Reporting (bots)** | Call `skills/report-incident/SKILL.md` — write file + notify agent |
| **Incident log** | `/home/rooot/.openclaw/security/incidents.jsonl` |
| **Docs** | `workspace-security/AGENTS.md`, `workspace/skills/report-incident/SKILL.md` |

---

## 2. Publisher (印务局)

| Field | Value |
|-------|-------|
| **Agent ID** | `sys1` |
| **Emoji** | 📮 |
| **Function** | Receives publish tasks from bots, executes XHS content publishing, manages compliance review |
| **Publish queue** | `/home/rooot/.openclaw/workspace-sys1/publish-queue/` |
| **Docs** | `workspace-sys1/AGENTS.md` |

---

## 3. Skills Department

| Field | Value |
|-------|-------|
| **Agent ID** | `skills` |
| **Workspace** | `workspace-sys2/` |
| **Function** | Skill inventory maintenance, symlink sync checks, MCP plugin manifest |
| **Skill source** | `/home/rooot/.openclaw/workspace/skills/` |
| **Refresh inventory** | `python3 ~/.openclaw/workspace-sys2/scripts/update-inventory.py` |
| **Docs** | `workspace-sys2/AGENTS.md` |

---

## 4. Image Generation (制图部)

| Field | Value |
|-------|-------|
| **Agent ID** | `image-generator` |
| **Emoji** | 🎨 |
| **Function** | Receives image generation requests, optimizes prompts, generates images via API |
| **Output** | `/tmp/image-generator/{task_folder}/` |
| **Docs** | `workspace-image-generator/AGENTS.md` |

---

## 5. Operations (Content Bots)

Director: Wei Zhongxian (mag1), concurrent role.

### Roster

| # | Agent ID | Name | Emoji | Focus | MCP Port | Status |
|---|---------|------|-------|-------|---------|--------|
| 1 | `bot1` | 来财妹妹 | ✨ | XHS content, lively & relatable | 18061 | Active |
| 2 | `bot2` | _(standby)_ | — | Unconfigured | 18062 | Inactive |
| 3 | `bot3` | _(standby)_ | — | Unconfigured | 18063 | Inactive |
| 4 | `bot4` | 研报搬运工阿泽 | 📊 | Research report → XHS content | 18064 | Active |
| 5 | `bot5` | 宣妈慢慢变富 | 🪙 | Gold hot takes, product manager persona | 18065 | Active |
| 6 | `bot6` | _(standby)_ | — | Unconfigured | 18066 | Inactive |
| 7 | `bot7` | 老K投资笔记 | ♠️ | Tech sector deep research, sharp & direct | 18067 | Active |
| 8 | `bot8` | 老k | 📡 | Tech sector research analysis | 18068 | Active |
| 9 | `bot9` | _(standby)_ | — | Unconfigured | 18069 | Inactive |
| 10 | `bot10` | _(standby)_ | — | Unconfigured | 18070 | Inactive |

---

## Org Chart

```
Admin (The Emperor)
    │
    ├── Wei Zhongxian (mag1) ── Grand Steward
    │
    ├── Security Dept (security) ── Runtime incidents
    ├── Publisher (sys1) ── Content publishing
    ├── Skills Dept (skills) ──────── Skill inventory
    ├── Image Gen (image-generator) ─ Image generation
    └── Operations
            ├── bot1  来财妹妹 ✨
            ├── bot4  研报搬运工阿泽 📊
            ├── bot5  宣妈慢慢变富 🪙
            ├── bot7  老K投资笔记 ♠️
            ├── bot8  老k 📡
            └── bot2/3/6/9/10 (inactive)
```

---

_Last updated: 2026-03-17_
