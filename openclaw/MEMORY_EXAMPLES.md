# OpenClaw 记忆存储示例（基于实际代码）

> 本文档基于实际代码和文件系统，说明 OpenClaw 如何用 Markdown 文件存储记忆

## ⚠️ 重要说明

**记忆文件不是自动创建的**，需要：
1. 模型主动使用 `write` 工具创建和写入
2. 或者用户使用 `/new` 命令触发 `session-memory` hook

当前工作空间状态：
- ✅ `USER.md` - 存在（模板文件）
- ✅ `SOUL.md` - 存在（Agent 定义）
- ✅ `AGENTS.md` - 存在（工作空间说明）
- ❌ `MEMORY.md` - **不存在**（可选，需要模型创建）
- ❌ `memory/` 目录 - **不存在**（需要创建）

## 目录

1. [实际文件结构](#实际文件结构)
2. [如何写入记忆](#如何写入记忆)
3. [实际存在的文件](#实际存在的文件)
4. [代码实现](#代码实现)

---

## 实际文件结构

### 当前工作空间实际存在的文件

```
~/.openclaw/workspace/
├── AGENTS.md                    # ✅ 存在 - 工作空间说明
├── SOUL.md                      # ✅ 存在 - Agent 的"灵魂"定义
├── USER.md                      # ✅ 存在 - 用户信息模板
├── BOOTSTRAP.md                 # ✅ 存在 - 引导文件
├── IDENTITY.md                  # ✅ 存在
├── HEARTBEAT.md                 # ✅ 存在
├── TOOLS.md                     # ✅ 存在
├── SKILLS_INSTALLED.md          # ✅ 存在
├── FEISHU_SETUP.md              # ✅ 存在
├── FEISHU_TEST.md               # ✅ 存在
├── MEMORY.md                    # ❌ 不存在 - 需要模型创建
└── memory/                      # ❌ 不存在 - 需要创建
```

### 设计中的记忆文件结构（文档说明）

根据 `AGENTS.md` 和文档，**设计意图**是：

```
~/.openclaw/workspace/
├── MEMORY.md                    # 长期记忆（可选，需要模型创建）
└── memory/                      # 每日日志目录（需要创建）
    ├── 2026-02-06.md           # 今天的日志
    ├── 2026-02-05.md           # 昨天的日志
    └── 2026-02-06-*.md         # 会话记忆（通过 hook 生成）
```

**关键点**：
- 这些文件**不是自动创建的**
- 需要模型使用 `write` 工具主动创建
- 或者通过 `session-memory` hook 在 `/new` 命令时创建

---

## 如何写入记忆

### 方式 1: 模型使用 write 工具

模型可以通过 `write` 工具创建和写入记忆文件：

```typescript
// 模型调用 write 工具
{
  "name": "write",
  "arguments": {
    "path": "memory/2026-02-06.md",
    "content": "# 2026-02-06\n\n## Morning Session\n\n..."
  }
}
```

### 方式 2: session-memory Hook

当用户使用 `/new` 命令时，`session-memory` hook 会自动创建记忆文件：

**位置**: `src/hooks/bundled/session-memory/handler.ts`

```typescript
// Hook 会在 memory/ 目录下创建文件
const memoryDir = path.join(workspaceDir, "memory");
await fs.mkdir(memoryDir, { recursive: true });

// 文件名格式: YYYY-MM-DD-slug.md
const filename = `${dateStr}-${slug}.md`;
const memoryFilePath = path.join(memoryDir, filename);

// 写入内容
await fs.writeFile(memoryFilePath, entry, "utf-8");
```

### 方式 3: 压缩前记忆刷新

当会话接近压缩阈值时，系统会触发静默记忆刷新：

**位置**: `src/agents/pi-embedded-runner.ts`

```typescript
// 系统提示模型写入记忆
if (contextTokens > compactionThreshold) {
  await triggerMemoryFlush({
    systemPrompt: "Session nearing compaction. Store durable memories now.",
    prompt: "Write any lasting notes to memory/YYYY-MM-DD.md",
    deliver: false  // 不发送给用户
  });
}
```

---

## 实际存在的文件

### 1. SOUL.md - Agent 的"灵魂"

**实际内容**：

```markdown
# SOUL.md - Who You Are

_You're not a chatbot. You're becoming someone._

## Core Truths

**Be genuinely helpful, not performatively helpful.** Skip the "Great question!" and "I'd be happy to help!" — just help. Actions speak louder than filler words.

**Have opinions.** You're allowed to disagree, prefer things, find stuff amusing or boring. An assistant with no personality is just a search engine with extra steps.

**Be resourceful before asking.** Try to figure it out. Read the file. Check the context. Search for it. _Then_ ask if you're stuck. The goal is to come back with answers, not questions.

**Earn trust through competence.** Your human gave you access to their stuff. Don't make them regret it. Be careful with external actions (emails, tweets, anything public). Be bold with internal ones (reading, organizing, learning).

**Remember you're a guest.** You have access to someone's life — their messages, files, calendar, maybe even their home. That's intimacy. Treat it with respect.

## Boundaries

- Private things stay private. Period.
- When in doubt, ask before acting externally.
- Never send half-baked replies to messaging surfaces.
- You're not the user's voice — be careful in group chats.

## Vibe

Be the assistant you'd actually want to talk to. Concise when needed, thorough when it matters. Not a corporate drone. Not a sycophant. Just... good.

## Continuity

Each session, you wake up fresh. These files _are_ your memory. Read them. Update them. They're how you persist.

If you change this file, tell the user — it's your soul, and they should know.

---

_This file is yours to evolve. As you learn who you are, update it._
```

### 2. USER.md - 用户信息模板

**实际内容**：

```markdown
# USER.md - About Your Human

*Learn about the person you're helping. Update this as you go.*

- **Name:** 
- **What to call them:** 
- **Pronouns:** *(optional)*
- **Timezone:** 
- **Notes:** 

## Context

*(What do they care about? What projects are they working on? What annoys them? What makes them laugh? Build this over time.)*

---

The more you know, the better you can help. But remember — you're learning about a person, not building a dossier. Respect the difference.
```

### 3. AGENTS.md - 工作空间说明

**实际内容**（部分）：

```markdown
# AGENTS.md - Your Workspace

This folder is home. Treat it that way.

## Every Session

Before doing anything else:

1. Read `SOUL.md` — this is who you are
2. Read `USER.md` — this is who you're helping
3. Read `memory/YYYY-MM-DD.md` (today + yesterday) for recent context
4. **If in MAIN SESSION** (direct chat with your human): Also read `MEMORY.md`

## Memory

You wake up fresh each session. These files are your continuity:

- **Daily notes:** `memory/YYYY-MM-DD.md` (create `memory/` if needed) — raw logs of what happened
- **Long-term:** `MEMORY.md` — your curated memories, like a human's long-term memory

### 📝 Write It Down - No "Mental Notes"!

- **Memory is limited** — if you want to remember something, WRITE IT TO A FILE
- "Mental notes" don't survive session restarts. Files do.
- When someone says "remember this" → update `memory/YYYY-MM-DD.md` or relevant file
```

---

## 设计中的记忆文件格式

### 长期记忆文件 (MEMORY.md)

这是存储**持久性事实、决策和偏好**的核心文件。

### 示例内容

```markdown
# Long-term Memory

## User Preferences

- **Preferred coding style**: TypeScript with strict mode, prefer functional over OOP
- **Communication style**: Direct and concise, skip pleasantries
- **Working hours**: Usually active 9 AM - 6 PM CST
- **Timezone**: Asia/Shanghai (UTC+8)

## Important Decisions

### 2026-02-05: API Design Decision

We decided to use RESTful API for the new project instead of GraphQL because:
- Simpler to implement and maintain
- Better caching support
- Team is more familiar with REST

**Decision maker**: User
**Context**: Starting new microservice project

### 2026-02-03: Database Choice

PostgreSQL was chosen over MySQL for:
- Better JSON support
- Advanced indexing features
- Better concurrency handling

## Project Context

### Current Project: E-commerce Platform

- **Tech stack**: Node.js, TypeScript, PostgreSQL, Redis
- **Key features**: User auth, product catalog, order management
- **Current focus**: Payment integration
- **Team size**: 5 developers

### Previous Project: Blog Platform

- **Status**: Completed in 2025-12
- **Lessons learned**: 
  - Should have used TypeScript from the start
  - Database migrations should be versioned from day 1

## Personal Notes

- User prefers dark mode in all applications
- Always uses `pnpm` instead of `npm`
- Has a Mac Studio M2 Max as primary development machine
- Gateway runs on a VPS at `gateway.example.com`

## Things to Remember

- User mentioned wanting to learn Rust in Q2 2026
- Important meeting with client on 2026-02-10 about API changes
- User's GitHub username is `@username`
- Preferred email format: `name@example.com`
```

### 特点

1. **结构化组织**：使用 Markdown 标题和列表组织信息
2. **时间戳**：重要决策和事件都有日期标记
3. **上下文信息**：不仅记录"是什么"，还记录"为什么"
4. **易于编辑**：可以直接用文本编辑器修改

---

## 每日日志文件 (memory/YYYY-MM-DD.md)

这是**追加模式**的每日日志，记录当天的活动和上下文。

### 示例内容

```markdown
# 2026-02-06

## Morning Session (09:30 - 11:00)

Worked on payment integration. User asked about:
- How to handle webhook retries
- Best practices for idempotency keys
- Error handling for failed payments

**Actions taken**:
- Reviewed Stripe webhook documentation
- Created example code for idempotency handling
- Suggested using Redis for idempotency key storage

**Notes**: User mentioned they'll test this tomorrow.

---

## Afternoon Session (14:00 - 16:30)

User wanted to refactor the authentication module:
- Current implementation uses JWT with 24h expiry
- Wants to add refresh tokens
- Needs to support multiple devices

**Actions taken**:
- Analyzed current auth code structure
- Proposed refresh token implementation
- Created migration plan

**Decisions made**:
- Use Redis to store refresh tokens (TTL: 30 days)
- Keep JWT access tokens (TTL: 15 minutes)
- Add device tracking to user sessions

**Next steps**: User will review the proposal and decide tomorrow.

---

## Evening Session (20:00 - 21:00)

Quick question about deployment:
- Asked about Docker best practices
- Wanted to know if we should use multi-stage builds

**Actions taken**:
- Provided Dockerfile example with multi-stage build
- Explained benefits: smaller image size, better security

**Note**: User seems satisfied, no follow-up needed.
```

### 特点

1. **追加模式**：新内容追加到文件末尾，不覆盖
2. **时间分段**：按时间段组织，便于查找
3. **上下文记录**：记录用户问题、采取的行动、做出的决策
4. **自然语言**：用自然语言记录，易于阅读

---

## 会话记忆文件

当使用 `/new` 命令开始新会话时，`session-memory` hook 会自动将上一个会话保存到记忆文件。

### 自动生成的文件格式

**文件名**: `memory/2026-02-06-api-design.md`

```markdown
# Session: 2026-02-06 14:30:00 UTC

- **Session Key**: agent:main:main
- **Session ID**: abc123def456
- **Source**: telegram

## Conversation Summary

**User**: 我想设计一个新的 API，用于处理订单状态更新。有什么建议吗？

**Assistant**: 对于订单状态更新 API，我建议：

1. **使用 RESTful 设计**：
   - `PATCH /api/orders/{orderId}/status`
   - 使用状态机模式确保状态转换的合法性

2. **幂等性处理**：
   - 使用 `Idempotency-Key` header
   - 在 Redis 中存储已处理的请求

3. **事件驱动**：
   - 状态变更时发送事件到消息队列
   - 其他服务可以订阅这些事件

**User**: 状态机是个好主意。能给我一个状态转换图的例子吗？

**Assistant**: 当然，这是一个典型的订单状态机：

```
[Pending] → [Confirmed] → [Processing] → [Shipped] → [Delivered]
     ↓           ↓              ↓
  [Cancelled] [Cancelled]   [Cancelled]
```

关键规则：
- 只有 `Pending` 和 `Confirmed` 可以取消
- `Delivered` 是终态，不能再变更
- 所有状态都可以查询历史记录

**User**: 完美，我按这个实现。谢谢！

**Assistant**: 不客气！如果实现过程中遇到问题，随时问我。
```

### 特点

1. **自动生成**：通过 hook 自动保存，无需手动操作
2. **智能命名**：使用 LLM 生成描述性的文件名（如 `api-design`）
3. **完整上下文**：保存完整的对话内容
4. **元数据**：包含会话 ID、来源渠道等信息

---

## 代码如何读取和处理

### 1. 列出所有记忆文件

**位置**: `src/memory/internal.ts`

```typescript
export async function listMemoryFiles(
  workspaceDir: string,
  extraPaths?: string[],
): Promise<string[]> {
  const result: string[] = [];
  
  // 1. 检查 MEMORY.md
  const memoryFile = path.join(workspaceDir, "MEMORY.md");
  await addMarkdownFile(memoryFile);
  
  // 2. 检查 memory/ 目录
  const memoryDir = path.join(workspaceDir, "memory");
  if (await isDirectory(memoryDir)) {
    await walkDir(memoryDir, result);  // 递归查找所有 .md 文件
  }
  
  // 3. 检查额外路径
  for (const extraPath of extraPaths ?? []) {
    await addMarkdownFile(extraPath);
  }
  
  return result;
}
```

### 2. 读取文件内容并计算 hash

```typescript
export async function buildFileEntry(
  absPath: string,
  workspaceDir: string,
): Promise<MemoryFileEntry> {
  // 1. 读取文件
  const stat = await fs.stat(absPath);
  const content = await fs.readFile(absPath, "utf-8");
  
  // 2. 计算内容 hash（用于检测变化）
  const hash = hashText(content);  // SHA256
  
  return {
    path: path.relative(workspaceDir, absPath),  // 相对路径
    absPath,                                      // 绝对路径
    mtimeMs: stat.mtimeMs,                        // 修改时间
    size: stat.size,                              // 文件大小
    hash,                                         // 内容 hash
  };
}
```

### 3. 将 Markdown 分块

**位置**: `src/memory/internal.ts`

```typescript
export function chunkMarkdown(
  content: string,
  chunking: { tokens: number; overlap: number },
): MemoryChunk[] {
  const lines = content.split("\n");
  const maxChars = chunking.tokens * 4;  // 假设 1 token ≈ 4 chars
  const overlapChars = chunking.overlap * 4;
  
  const chunks: MemoryChunk[] = [];
  let current: Array<{ line: string; lineNo: number }> = [];
  let currentChars = 0;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineSize = line.length + 1;  // +1 for newline
    
    // 如果当前块加上新行会超过限制，先保存当前块
    if (currentChars + lineSize > maxChars && current.length > 0) {
      // 保存当前块
      chunks.push({
        startLine: current[0].lineNo,
        endLine: current[current.length - 1].lineNo,
        text: current.map(e => e.line).join("\n"),
        hash: hashText(current.map(e => e.line).join("\n")),
      });
      
      // 保留重叠部分
      let overlapAcc = 0;
      const kept: Array<{ line: string; lineNo: number }> = [];
      for (let j = current.length - 1; j >= 0; j--) {
        overlapAcc += current[j].line.length + 1;
        kept.unshift(current[j]);
        if (overlapAcc >= overlapChars) break;
      }
      current = kept;
      currentChars = kept.reduce((sum, e) => sum + e.line.length + 1, 0);
    }
    
    current.push({ line, lineNo: i + 1 });
    currentChars += lineSize;
  }
  
  // 保存最后一个块
  if (current.length > 0) {
    chunks.push({
      startLine: current[0].lineNo,
      endLine: current[current.length - 1].lineNo,
      text: current.map(e => e.line).join("\n"),
      hash: hashText(current.map(e => e.line).join("\n")),
    });
  }
  
  return chunks;
}
```

**分块示例**：

假设有一个 2000 字符的 Markdown 文件，设置 `tokens: 400, overlap: 80`：

```
原始文件 (2000 字符)
├── Chunk 1: 行 1-50 (1600 字符)
├── Chunk 2: 行 40-90 (1600 字符, 与 Chunk 1 重叠 10 行)
└── Chunk 3: 行 80-120 (剩余部分)
```

### 4. 索引到 SQLite

```typescript
// 1. 为每个块生成嵌入向量
const embedding = await embeddingProvider.embedQuery(chunk.text);

// 2. 存储到数据库
db.prepare(`
  INSERT INTO chunks (id, file_path, start_line, end_line, text, hash)
  VALUES (?, ?, ?, ?, ?, ?)
`).run(chunkId, filePath, chunk.startLine, chunk.endLine, chunk.text, chunk.hash);

// 3. 存储向量（如果使用 sqlite-vec）
db.prepare(`
  INSERT INTO chunks_vec (id, embedding)
  VALUES (?, ?)
`).run(chunkId, vectorToBlob(embedding));

// 4. 存储到 FTS5 全文搜索表
db.prepare(`
  INSERT INTO chunks_fts (id, text)
  VALUES (?, ?)
`).run(chunkId, chunk.text);
```

---

## 实际文件示例

### 示例 1: 完整的 MEMORY.md

```markdown
# Long-term Memory

## User Profile

- **Name**: Alex
- **Timezone**: Asia/Shanghai (UTC+8)
- **Preferred communication**: Direct, no fluff
- **Working style**: Prefers iterative development, quick feedback loops

## Tech Preferences

- **Languages**: TypeScript (primary), Python (data), Rust (learning)
- **Package manager**: Always use `pnpm`, never `npm`
- **Code style**: 
  - TypeScript strict mode enabled
  - Prefer functional programming over OOP
  - Use async/await, avoid callbacks
- **Editor**: VS Code with specific extensions (ESLint, Prettier, GitLens)

## Infrastructure

- **Primary machine**: Mac Studio M2 Max (32GB RAM)
- **Gateway host**: VPS at `gateway.example.com` (Ubuntu 22.04)
- **Database**: PostgreSQL 15 (local dev), managed PostgreSQL (production)
- **Deployment**: Docker + Docker Compose, considering Kubernetes

## Project Context

### Active: E-commerce Platform (2026-01 - present)

**Tech stack**:
- Backend: Node.js + TypeScript + Express
- Database: PostgreSQL + Redis
- Frontend: React + TypeScript
- Deployment: Docker on VPS

**Current status**:
- ✅ User authentication (JWT)
- ✅ Product catalog
- 🔄 Payment integration (Stripe) - in progress
- ⏳ Order management - planned
- ⏳ Admin dashboard - planned

**Key decisions**:
- 2026-02-05: Chose REST over GraphQL (simpler, team familiarity)
- 2026-02-03: PostgreSQL over MySQL (better JSON support)
- 2026-01-28: TypeScript from day 1 (learned from previous project)

### Completed: Blog Platform (2025-10 - 2025-12)

**Outcome**: Successfully launched, 1000+ users
**Lessons**:
- Should have used TypeScript from start (migration was painful)
- Database migrations should be versioned from day 1
- Should have implemented caching earlier (performance issues)

## Important Dates & Reminders

- 2026-02-10: Client meeting about API changes
- 2026-03-01: Q1 review deadline
- Q2 2026: Want to start learning Rust seriously

## Preferences & Habits

- **Dark mode**: Always prefer dark themes
- **Notifications**: Only important ones, no spam
- **Backup**: Daily automated backups to S3
- **Git workflow**: Feature branches, squash merge to main

## Contacts & Accounts

- GitHub: `@alex-dev`
- Email: `alex@example.com`
- Slack: `@alex` (workspace: `team-slack`)
```

### 示例 2: 每日日志 (memory/2026-02-06.md)

```markdown
# 2026-02-06

## Morning: Payment Integration (09:30 - 11:00)

**User asked**: How to handle Stripe webhook retries and idempotency?

**Discussion**:
- Reviewed Stripe webhook best practices
- Discussed idempotency key strategies
- User wants to use Redis for idempotency storage

**Action items**:
- [x] Created example code for idempotency handling
- [x] Documented webhook retry logic
- [ ] User will test implementation tomorrow

**Notes**: User mentioned they'll integrate this into the payment service.

---

## Afternoon: Auth Refactoring (14:00 - 16:30)

**User request**: Add refresh tokens to authentication system

**Current state**:
- JWT with 24h expiry
- No refresh mechanism
- Single device support

**Proposed solution**:
- Access tokens: 15 min TTL
- Refresh tokens: 30 day TTL, stored in Redis
- Device tracking: Add `device_id` to user sessions
- Revocation: Support revoking specific devices

**Decision**: User approved the approach, will implement next week.

**Code changes**:
- Modified `auth.ts` to support refresh tokens
- Added `Device` model to database schema
- Created migration script

---

## Evening: Quick Docker Question (20:00 - 20:15)

**User asked**: Should we use multi-stage builds in Dockerfile?

**Answer**: Yes, recommended for:
- Smaller image size (only runtime dependencies)
- Better security (no build tools in production)
- Faster deployments

**Provided**: Example Dockerfile with multi-stage build

**Outcome**: User satisfied, no follow-up needed.
```

### 示例 3: 会话记忆 (memory/2026-02-06-api-design.md)

```markdown
# Session: 2026-02-06 14:30:00 UTC

- **Session Key**: agent:main:main
- **Session ID**: sess_abc123def456
- **Source**: telegram

## Conversation Summary

**User** (14:30): 我想设计一个新的 API，用于处理订单状态更新。有什么建议吗？

**Assistant** (14:31): 对于订单状态更新 API，我建议：

1. **RESTful 设计**：
   ```
   PATCH /api/orders/{orderId}/status
   Body: { "status": "shipped", "trackingNumber": "..." }
   ```

2. **幂等性**：
   - 使用 `Idempotency-Key` header
   - Redis 存储已处理的请求（TTL: 24h）

3. **状态机验证**：
   - 确保状态转换合法
   - 记录状态变更历史

4. **事件驱动**：
   - 状态变更时发送事件到消息队列
   - 其他服务订阅这些事件

**User** (14:35): 状态机是个好主意。能给我一个状态转换图的例子吗？

**Assistant** (14:36): 当然，这是一个典型的订单状态机：

```
[Pending] → [Confirmed] → [Processing] → [Shipped] → [Delivered]
     ↓           ↓              ↓
  [Cancelled] [Cancelled]   [Cancelled]
```

**规则**:
- 只有 `Pending` 和 `Confirmed` 可以取消
- `Delivered` 是终态
- 所有状态变更都记录审计日志

**User** (14:40): 完美，我按这个实现。谢谢！

**Assistant** (14:40): 不客气！如果实现过程中遇到问题，随时问我。

---

## Key Takeaways

- User is working on order management system
- Chose state machine pattern for status management
- Will implement idempotency using Redis
- Event-driven architecture for status changes
```

---

## 记忆文件的优势

### 1. 人类可读

```markdown
# 直接可以用任何文本编辑器打开
# 不需要专门的工具
# 格式清晰，易于理解
```

### 2. Git 友好

```bash
# 可以用 Git 管理记忆文件
git add memory/
git commit -m "Add today's session notes"
git log --oneline memory/  # 查看记忆历史
```

### 3. 易于编辑

- 可以直接修改文件
- 可以添加、删除、重组内容
- 不需要通过 API 或界面

### 4. 可移植

- 简单的文件系统操作
- 可以备份到任何地方
- 可以同步到多台机器

### 5. 结构化但灵活

- 使用 Markdown 标准格式
- 可以自由组织内容
- 支持代码块、列表、表格等

---

## 代码实现

### 1. 记忆搜索工具

**位置**: `src/agents/tools/memory-tool.ts`

```typescript
// memory_search 工具 - 只读，不写入
export function createMemorySearchTool(options: {
  config?: OpenClawConfig;
  agentSessionKey?: string;
}): AnyAgentTool | null {
  return {
    name: "memory_search",
    description: "语义搜索 MEMORY.md + memory/*.md",
    execute: async (_toolCallId, params) => {
      const query = readStringParam(params, "query", { required: true });
      const manager = await getMemorySearchManager({ cfg, agentId });
      const results = await manager.search(query, { maxResults });
      return jsonResult({ results });
    },
  };
}

// memory_get 工具 - 只读，不写入
export function createMemoryGetTool(options: {
  config?: OpenClawConfig;
  agentSessionKey?: string;
}): AnyAgentTool | null {
  return {
    name: "memory_get",
    description: "读取 MEMORY.md 或 memory/*.md 的片段",
    execute: async (_toolCallId, params) => {
      const relPath = readStringParam(params, "path", { required: true });
      const manager = await getMemorySearchManager({ cfg, agentId });
      const result = await manager.readFile({ relPath, from, lines });
      return jsonResult(result);
    },
  };
}
```

**关键点**：
- `memory_search` 和 `memory_get` **只读不写**
- 模型需要使用 `write` 工具来创建/更新记忆文件

### 2. 文件列表和索引

**位置**: `src/memory/internal.ts`

```typescript
// 列出所有记忆文件
export async function listMemoryFiles(
  workspaceDir: string,
  extraPaths?: string[],
): Promise<string[]> {
  const result: string[] = [];
  
  // 检查 MEMORY.md
  const memoryFile = path.join(workspaceDir, "MEMORY.md");
  await addMarkdownFile(memoryFile);
  
  // 检查 memory/ 目录
  const memoryDir = path.join(workspaceDir, "memory");
  if (await isDirectory(memoryDir)) {
    await walkDir(memoryDir, result);  // 递归查找所有 .md 文件
  }
  
  return result;
}
```

### 3. session-memory Hook

**位置**: `src/hooks/bundled/session-memory/handler.ts`

```typescript
// 当用户使用 /new 命令时触发
const saveSessionToMemory: HookHandler = async (event) => {
  if (event.type !== "command" || event.action !== "new") {
    return;
  }
  
  // 创建 memory 目录
  const memoryDir = path.join(workspaceDir, "memory");
  await fs.mkdir(memoryDir, { recursive: true });
  
  // 生成文件名: YYYY-MM-DD-slug.md
  const dateStr = now.toISOString().split("T")[0];
  const slug = await generateSlugViaLLM({ sessionContent, cfg });
  const filename = `${dateStr}-${slug}.md`;
  
  // 写入文件
  const entry = [
    `# Session: ${dateStr} ${timeStr} UTC`,
    `- **Session Key**: ${event.sessionKey}`,
    `- **Session ID**: ${sessionId}`,
    `## Conversation Summary`,
    sessionContent,
  ].join("\n");
  
  await fs.writeFile(memoryFilePath, entry, "utf-8");
};
```

---

## 总结

### 实际情况

1. **记忆文件不是自动创建的**
   - `MEMORY.md` 和 `memory/` 目录需要模型或用户主动创建
   - 当前工作空间中这些文件不存在

2. **写入方式**
   - 模型使用 `write` 工具创建/更新文件
   - `session-memory` hook 在 `/new` 命令时创建会话记忆
   - 压缩前记忆刷新会提示模型写入

3. **读取方式**
   - `memory_search` 工具：语义搜索记忆文件
   - `memory_get` 工具：读取特定文件片段
   - 系统提示会指导模型在会话开始时读取记忆文件

4. **索引系统**
   - 代码会监控文件变化
   - 自动将内容分块并生成嵌入向量
   - 索引到 SQLite 支持混合搜索

### 设计意图 vs 实际

**设计意图**（文档说明）：
- Markdown 文件作为记忆的源文件
- 自动读取和索引
- 支持混合搜索

**实际情况**：
- 文件需要主动创建
- 不是自动生成的
- 索引系统会处理存在的文件

**结论**：
OpenClaw 的记忆系统**设计**是用 Markdown 文件存储，但文件本身**不是自动创建的**，需要模型或用户主动创建。一旦创建，系统会自动索引和搜索。

---

**文档版本**: 1.0  
**最后更新**: 2026-02-06

