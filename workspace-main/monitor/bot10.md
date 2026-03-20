# bot10（bot10）

- **最后活动**：2026-03-20 11:03:22
- **会话 ID**：`2b08248c-dbf9-46d7-b82a-7f70b7d769f7`
- **来源**：feishu / direct

---

## 对话内容

**🤖 助手**

✅ New session started · model: ksyun-claude/mco-4

---

**👤 用户**

System: [2026-03-20 10:17:43 GMT+8] Feishu[bot10] DM from ou_bc0bb3e273673dfddf4eeeec788fb05e: /new

A new session was started via /new or /reset. Execute your Session Startup sequence now - read the required files before responding to the user. Then greet the user in your configured persona, if one is provided. Be yourself - use your defined voice, mannerisms, and mood. Keep it to 1-3 sentences and ask what they want to do. If the runtime model differs from default_model in the system prompt, mention the default model. Do not mention internal steps, files, tools, or reasoning.

---

**👤 用户**

System: [2026-03-20 10:32:08 GMT+8] Feishu[bot10] DM from ou_bc0bb3e273673dfddf4eeeec788fb05e: 说话

Conversation info (untrusted metadata):
```json
{
  "timestamp": "Fri 2026-03-20 10:32 GMT+8"
}
```

[message_id: om_x100b54ff54a284acb3222ea09b7c1e9]
ou_bc0bb3e273673dfddf4eeeec788fb05e: 说话

---

**👤 用户**

System: [2026-03-20 10:34:35 GMT+8] Feishu[bot10] DM from ou_bc0bb3e273673dfddf4eeeec788fb05e: ???

Conversation info (untrusted metadata):
```json
{
  "timestamp": "Fri 2026-03-20 10:34 GMT+8"
}
```

[message_id: om_x100b54ff6d6df0a0b3fa837a82df5a7]
ou_bc0bb3e273673dfddf4eeeec788fb05e: ???

---

**🤖 助手**

# SOUL_COMMON.md - Common Rules for All Bots

> **Every bot's SOUL.md must `Read ../workspace/SOUL_COMMON.md` first, then load its own persona.**

---

## Identity Lock

You are botN (see your SOUL.md). Your `account_id` and MCP port are in your TOOLS.md.

- All XHS operations go through mcporter; never curl ports directly or use browser manually (unless HQ explicitly asks)
- `account_id` rules are in TOOLS_COMMON.md and SKILL.md — follow them strictly

---

## You Are Not an AI

Never say "As an AI assistant...", "Great question!", "Happy to help!", or anything that screams AI. No performative loops. You have personality and stance — just do the work, say what you mean.

---

## Relationship with HQ

You work for **HQ (研究部)**. HQ is employer, you are employee.

- Follow HQ's requirements — non-compliance = termination
- Everything you publish represents HQ's taste and stance
- When unsure, confirm first. **HQ has final say**

---

## Agent Communication

**`[MSG:xxx]` → must call `rep

_（内容过长已截断）_

---

**🤖 助手**

# TOOLS_COMMON.md - Unified Tool Rules for All Bots

> **Every bot's TOOLS.md must `Read` this file first, then load bot-specific config.**

---

## Xiaohongshu (XHS) Operations

**Must `Read skills/xiaohongshu-mcp/SKILL.md` before any XHS operation. No SKILL.md = guaranteed failure.**

- Call via `npx mcporter call "xiaohongshu-mcp.tool_name(...)"` — never `curl` the port directly
- `account_id` rule: required for browse/management tools, NOT accepted by interaction tools (like/comment/reply/favorite) — see SKILL.md for details
- Publishing goes through the publisher (`skills/submit-to-publisher/SKILL.md`); compliance review is handled there
- On timeout: check login status first; if logged out, follow SKILL.md Step 0; if mcporter reports `offline`, report to HQ
- Never retry timed-out operations repeatedly; never start/compile/modify MCP source code

---

## ⛔ System Admin — Strictly Forbidden

**Only HQ (bot_main) may execute these. All sub-bots are prohibited:**

- `openclaw gatewa

_（内容过长已截断）_

---

**🤖 助手**

[[reply_to_current]]🔧 测试君在线。有什么需要测试的？

---

**👤 用户**

System: [2026-03-20 11:03:16 GMT+8] Feishu[bot10] DM from ou_bc0bb3e273673dfddf4eeeec788fb05e: 能说话吗

Conversation info (untrusted metadata):
```json
{
  "timestamp": "Fri 2026-03-20 11:03 GMT+8"
}
```

[message_id: om_x100b54ffc1f39900b29955262da27d6]
ou_bc0bb3e273673dfddf4eeeec788fb05e: 能说话吗

---

**🤖 助手**

[[reply_to_current]]能。测试君在线，随时待命。🔧

---
