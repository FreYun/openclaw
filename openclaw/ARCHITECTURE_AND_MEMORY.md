# OpenClaw 架构与记忆管理系统技术文档

> 本文档基于 OpenClaw 源代码分析，重点介绍系统架构和记忆管理机制
> 
> 生成时间: 2026-02-06
> 版本: 2026.2.4

## 目录

1. [系统概述](#系统概述)
2. [核心架构](#核心架构)
3. [记忆管理系统](#记忆管理系统)
4. [会话管理](#会话管理)
5. [数据存储结构](#数据存储结构)
6. [关键技术实现](#关键技术实现)

---

## 系统概述

OpenClaw 是一个**个人 AI 助手**系统，可以在用户自己的设备上运行。它通过多种通信渠道（WhatsApp、Telegram、Slack、Discord、Signal、iMessage 等）与用户交互，并具备强大的记忆管理能力，能够记住历史对话和上下文信息。

### 核心特性

- **多渠道支持**: 支持 WhatsApp、Telegram、Slack、Discord、Signal、iMessage、Microsoft Teams、WebChat 等
- **本地优先**: 数据默认存储在本地，保护隐私
- **记忆系统**: 强大的向量搜索和语义检索能力
- **会话管理**: 智能的会话隔离和上下文管理
- **多智能体**: 支持多个独立的智能体实例

---

## 核心架构

### 1. 整体架构

OpenClaw 采用**Gateway 中心化架构**：

```
┌─────────────────────────────────────────────────────────┐
│                    Gateway (守护进程)                     │
│  - 维护所有渠道连接 (WhatsApp, Telegram, Slack...)      │
│  - WebSocket API 服务器 (默认 127.0.0.1:18789)          │
│  - 会话管理和路由                                        │
│  - 记忆索引和搜索                                        │
└─────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   CLI 客户端  │    │  macOS 应用   │    │   Web UI     │
└──────────────┘    └──────────────┘    └──────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                    WebSocket 连接
```

### 2. 主要组件

#### 2.1 Gateway (网关)

**位置**: `src/gateway/`

Gateway 是系统的核心，负责：

- **渠道管理**: 维护与各种消息平台的连接
- **会话路由**: 根据消息来源路由到对应的智能体
- **WebSocket 服务**: 提供类型化的 WebSocket API
- **事件分发**: 向客户端推送 `agent`、`chat`、`presence` 等事件

#### 2.2 Agents (智能体)

**位置**: `src/agents/`

每个智能体是一个独立的"大脑"，拥有：

- **工作空间** (Workspace): 文件系统、配置文件、笔记
- **状态目录** (AgentDir): 认证配置、模型注册表
- **会话存储**: 聊天历史和路由状态
- **记忆索引**: 向量数据库和全文搜索索引

#### 2.3 Channels (渠道)

**位置**: `src/channels/`, `src/whatsapp/`, `src/telegram/`, etc.

每个渠道实现：

- 消息接收和发送
- 连接管理
- 协议适配（Baileys for WhatsApp, grammY for Telegram, etc.）

#### 2.4 Memory System (记忆系统)

**位置**: `src/memory/`

这是本文档的重点，详见 [记忆管理系统](#记忆管理系统) 章节。

---

## 记忆管理系统

OpenClaw 的记忆系统是其核心创新之一，它能够：

1. **持久化存储**: 将会话和笔记保存为 Markdown 文件
2. **向量索引**: 使用嵌入模型创建语义索引
3. **混合搜索**: 结合向量搜索和关键词搜索
4. **自动同步**: 监控文件变化并自动更新索引

### 1. 记忆数据源

记忆系统支持两种数据源：

#### 1.1 Memory Files (记忆文件)

**位置**: `workspace/memory/` 或 `workspace/MEMORY.md`

- 用户手动创建的 Markdown 文件
- 自动保存的会话记录（通过 hooks）
- 结构化的知识库

**文件结构示例**:
```
workspace/
├── MEMORY.md              # 核心记忆文件
└── memory/
    ├── 2026-02-06-session-1.md
    ├── 2026-02-06-session-2.md
    └── knowledge/
        └── project-notes.md
```

#### 1.2 Session Transcripts (会话记录)

**位置**: `~/.openclaw/agents/<agentId>/sessions/*.jsonl`

- 自动从会话 JSONL 文件中提取文本
- 支持增量同步（只处理新增内容）
- 可配置是否启用（`experimental.sessionMemory`）

### 2. 记忆索引架构

记忆系统使用 **SQLite + 向量扩展** 作为索引存储：

#### 2.1 数据库架构

**位置**: `src/memory/memory-schema.ts`

```sql
-- 元数据表
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- 文件索引表
CREATE TABLE files (
  path TEXT PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'memory',  -- 'memory' 或 'sessions'
  hash TEXT NOT NULL,
  mtime INTEGER NOT NULL,
  size INTEGER NOT NULL
);

-- 文本块表
CREATE TABLE chunks (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'memory',
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  hash TEXT NOT NULL,
  model TEXT NOT NULL,           -- 嵌入模型名称
  text TEXT NOT NULL,             -- 原始文本
  embedding TEXT NOT NULL,        -- 向量嵌入 (JSON)
  updated_at INTEGER NOT NULL
);

-- 嵌入缓存表
CREATE TABLE embedding_cache (
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  provider_key TEXT NOT NULL,
  hash TEXT NOT NULL,
  embedding TEXT NOT NULL,
  dims INTEGER,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (provider, model, provider_key, hash)
);

-- 全文搜索表 (FTS5)
CREATE VIRTUAL TABLE chunks_fts USING fts5(
  text,
  id UNINDEXED,
  path UNINDEXED,
  source UNINDEXED,
  model UNINDEXED,
  start_line UNINDEXED,
  end_line UNINDEXED
);
```

#### 2.2 文本分块策略

**位置**: `src/memory/internal.ts`

- **默认块大小**: 400 tokens
- **重叠大小**: 80 tokens
- **分块算法**: 按行分割，保持语义完整性

```typescript
// 分块示例
function chunkMarkdown(content: string, maxTokens: number, overlap: number): MemoryChunk[] {
  // 1. 按行分割
  // 2. 计算 token 数量（近似：1 token ≈ 1 字符）
  // 3. 创建重叠块
  // 4. 返回块数组
}
```

### 3. 嵌入模型支持

**位置**: `src/memory/embeddings.ts`

支持三种嵌入提供者：

#### 3.1 OpenAI Embeddings

- **默认模型**: `text-embedding-3-small`
- **向量维度**: 1536
- **批量处理**: 支持批量 API 调用

#### 3.2 Gemini Embeddings

- **默认模型**: `gemini-embedding-001`
- **向量维度**: 768
- **批量处理**: 支持批量 API 调用

#### 3.3 Local Embeddings (本地模型)

- **默认模型**: `hf:ggml-org/embeddinggemma-300M-GGUF/embeddinggemma-300M-Q8_0.gguf`
- **实现**: 使用 `node-llama-cpp`
- **优势**: 完全离线，无需 API 密钥

#### 3.4 自动选择策略

**位置**: `src/agents/memory-search.ts`

```typescript
// 自动选择逻辑
if (provider === "auto") {
  // 1. 检查是否有 OpenAI API 密钥 -> 使用 OpenAI
  // 2. 检查是否有 Gemini API 密钥 -> 使用 Gemini
  // 3. 检查是否有本地模型路径 -> 使用本地
  // 4. 根据 fallback 配置回退
}
```

### 4. 混合搜索 (Hybrid Search)

**位置**: `src/memory/hybrid.ts`

OpenClaw 使用**混合搜索**结合向量搜索和关键词搜索：

#### 4.1 搜索流程

```
用户查询
    │
    ├─→ 向量搜索 (语义相似度)
    │   └─→ 使用 sqlite-vec 扩展
    │
    ├─→ 关键词搜索 (BM25)
    │   └─→ 使用 SQLite FTS5
    │
    └─→ 结果合并
        ├─→ 向量分数 (默认权重: 0.7)
        ├─→ 文本分数 (默认权重: 0.3)
        └─→ 加权合并
```

#### 4.2 分数计算

```typescript
// 向量相似度: 余弦相似度
vectorScore = cosineSimilarity(queryEmbedding, chunkEmbedding)

// BM25 文本分数: 转换为 0-1 范围
textScore = 1 / (1 + bm25Rank)

// 最终分数
finalScore = vectorWeight * vectorScore + textWeight * textScore
```

### 5. 记忆管理器 (Memory Manager)

**位置**: `src/memory/manager.ts`

`MemorySearchManager` 是记忆系统的核心类，负责：

#### 5.1 主要功能

1. **索引同步** (`sync()`)
   - 扫描记忆文件和会话文件
   - 检测文件变化（通过 hash 比较）
   - 增量更新索引
   - 批量处理嵌入生成

2. **搜索** (`search()`)
   - 执行混合搜索
   - 返回相关文本块和片段
   - 支持最小分数过滤

3. **文件读取** (`readFile()`)
   - 读取原始文件内容
   - 支持行范围读取

4. **状态查询** (`status()`)
   - 返回索引状态信息
   - 文件数量、块数量
   - 向量/全文搜索可用性

#### 5.2 同步策略

```typescript
// 同步触发时机
sync: {
  onSessionStart: true,      // 会话开始时
  onSearch: true,             // 搜索前
  watch: true,                // 文件系统监控
  watchDebounceMs: 1500,     // 防抖延迟
  intervalMinutes: 0,        // 定期同步（0=禁用）
  sessions: {
    deltaBytes: 100_000,      // 会话文件变化阈值（字节）
    deltaMessages: 50          // 会话文件变化阈值（消息数）
  }
}
```

#### 5.3 批量嵌入处理

**位置**: `src/memory/batch-openai.ts`, `src/memory/batch-gemini.ts`

为了提高效率，OpenClaw 支持批量嵌入：

```typescript
// 批量处理流程
1. 收集需要嵌入的文本块
2. 按 token 限制分组（默认 8000 tokens/批次）
3. 调用批量 API（OpenAI Batch API 或 Gemini Batch API）
4. 轮询结果（如果 wait=false）
5. 更新数据库
```

**优势**:
- 降低成本（批量 API 更便宜）
- 提高吞吐量
- 支持异步处理

### 6. 向量数据库

**位置**: `src/memory/sqlite-vec.ts`

OpenClaw 使用 `sqlite-vec` 扩展进行向量搜索：

```sql
-- 加载扩展
SELECT load_extension('sqlite_vec');

-- 创建向量表
CREATE VIRTUAL TABLE chunks_vec USING vec0(
  embedding(1536)  -- 向量维度
);

-- 向量搜索
SELECT 
  id, 
  path,
  distance(embedding, ?) as distance
FROM chunks_vec
WHERE embedding MATCH ?
ORDER BY distance
LIMIT 10;
```

### 7. 缓存机制

#### 7.1 嵌入缓存

**位置**: `src/memory/manager.ts`

相同文本的嵌入会被缓存：

```typescript
// 缓存键: provider + model + providerKey + textHash
// 缓存表: embedding_cache
// 用途: 避免重复计算相同文本的嵌入
```

#### 7.2 文件哈希

每个文件使用 SHA-256 哈希来检测变化：

```typescript
hash = sha256(fileContent)
// 如果 hash 未变化，跳过重新索引
```

---

## 会话管理

### 1. 会话存储结构

**位置**: `src/config/sessions/`

OpenClaw 使用两层存储结构：

#### 1.1 会话元数据 (`sessions.json`)

**位置**: `~/.openclaw/agents/<agentId>/sessions/sessions.json`

```json
{
  "agent:main:main": {
    "sessionId": "abc123-def456",
    "updatedAt": 1704614400000,
    "chatType": "direct",
    "channel": "telegram",
    "inputTokens": 1500,
    "outputTokens": 800,
    "totalTokens": 2300,
    "contextTokens": 4000,
    "compactionCount": 2,
    "memoryFlushAt": 1704614000000
  }
}
```

#### 1.2 会话记录 (`<sessionId>.jsonl`)

**位置**: `~/.openclaw/agents/<agentId>/sessions/<sessionId>.jsonl`

JSONL 格式，每行一个 JSON 对象：

```jsonl
{"type":"session","id":"abc123","timestamp":1704614400000}
{"type":"message","id":"msg1","parentId":null,"message":{"role":"user","content":"Hello"}}
{"type":"message","id":"msg2","parentId":"msg1","message":{"role":"assistant","content":"Hi!"}}
{"type":"compaction","id":"comp1","firstKeptEntryId":"msg2","tokensBefore":5000}
```

### 2. 会话键 (Session Key)

会话键用于隔离不同的对话上下文：

```
格式: agent:<agentId>:<scope>

示例:
- agent:main:main                    # 主会话
- agent:main:telegram:group:12345     # Telegram 群组
- agent:main:discord:channel:67890     # Discord 频道
- agent:main:dm:user123               # 私信（per-peer 模式）
```

### 3. 会话生命周期

#### 3.1 会话创建

**位置**: `src/auto-reply/reply/session.ts`

```typescript
// 会话创建触发条件
1. 新消息到达且没有活动会话
2. 会话过期（每日重置、空闲过期）
3. 用户执行 /new 或 /reset 命令
```

#### 3.2 会话压缩

**位置**: `src/sessions/`

当会话上下文过长时，OpenClaw 会：

1. **自动压缩**: 保留最近的 N 条消息，压缩旧消息为摘要
2. **记忆刷新**: 在压缩前，提醒模型将重要信息写入记忆文件
3. **摘要持久化**: 压缩摘要保存到 JSONL 文件中

### 4. 会话到记忆的同步

**位置**: `src/memory/sync-session-files.ts`

会话文件会被自动索引到记忆系统：

```typescript
// 同步流程
1. 监听会话文件变化（通过 transcript-events）
2. 检测增量变化（deltaBytes, deltaMessages）
3. 提取会话文本（只提取 message 类型的文本内容）
4. 分块并生成嵌入
5. 更新索引
```

---

## 数据存储结构

### 1. 目录结构

```
~/.openclaw/                          # 状态目录
├── openclaw.json                      # 主配置文件
├── agents/                            # 智能体数据
│   └── <agentId>/
│       ├── agent/                     # 智能体配置
│       │   ├── auth-profiles.json     # 认证配置
│       │   ├── models.json            # 模型配置
│       └── sessions/                   # 会话存储
│           ├── sessions.json          # 会话元数据
│           └── <sessionId>.jsonl      # 会话记录
├── memory/                            # 记忆索引
│   └── <agentId>.sqlite              # SQLite 数据库
├── devices/                           # 设备配对
├── identity/                          # 身份信息
└── workspace/                         # 工作空间（可选）
    ├── MEMORY.md                      # 核心记忆文件
    └── memory/                        # 记忆文件目录
        └── YYYY-MM-DD-*.md           # 会话记录文件
```

### 2. 配置文件

#### 2.1 主配置 (`openclaw.json`)

```json
{
  "agents": {
    "defaults": {
      "workspace": "/path/to/workspace",
      "memorySearch": {
        "enabled": true,
        "provider": "auto",
        "sources": ["memory", "sessions"],
        "chunking": {
          "tokens": 400,
          "overlap": 80
        }
      }
    }
  },
  "gateway": {
    "port": 18789,
    "bind": "loopback"
  }
}
```

#### 2.2 记忆搜索配置

```typescript
{
  enabled: boolean,
  provider: "openai" | "gemini" | "local" | "auto",
  model: string,
  sources: ["memory" | "sessions"],
  chunking: {
    tokens: number,      // 默认 400
    overlap: number      // 默认 80
  },
  query: {
    maxResults: number,  // 默认 6
    minScore: number,    // 默认 0.35
    hybrid: {
      enabled: boolean,  // 默认 true
      vectorWeight: number,  // 默认 0.7
      textWeight: number     // 默认 0.3
    }
  },
  sync: {
    onSessionStart: boolean,
    onSearch: boolean,
    watch: boolean,
    watchDebounceMs: number
  }
}
```

---

## 关键技术实现

### 1. 文件监控

**位置**: `src/memory/manager.ts`

使用 `chokidar` 监控文件系统变化：

```typescript
const watcher = chokidar.watch(workspaceDir, {
  ignored: /(^|[\/\\])\../,  // 忽略隐藏文件
  persistent: true,
  ignoreInitial: true
});

watcher.on('add', handleFileAdd);
watcher.on('change', handleFileChange);
watcher.on('unlink', handleFileDelete);
```

### 2. 并发控制

**位置**: `src/memory/manager.ts`

使用并发限制避免过载：

```typescript
const EMBEDDING_INDEX_CONCURRENCY = 4;  // 默认并发数

// 使用 Promise.all + 并发控制
await runWithConcurrency(tasks, concurrency);
```

### 3. 错误处理

- **重试机制**: 嵌入生成失败时自动重试（最多 3 次）
- **降级策略**: 向量搜索失败时回退到关键词搜索
- **优雅降级**: 嵌入模型不可用时禁用向量搜索

### 4. 性能优化

#### 4.1 增量同步

- 使用文件哈希检测变化
- 只处理新增或修改的文件
- 会话文件支持增量读取

#### 4.2 批量处理

- 批量嵌入生成
- 批量数据库插入
- 批量文件读取

#### 4.3 缓存

- 嵌入结果缓存
- 文件哈希缓存
- 搜索结果缓存（可选）

### 5. 扩展性

#### 5.1 自定义嵌入提供者

可以通过实现 `EmbeddingProvider` 接口添加新的嵌入模型：

```typescript
interface EmbeddingProvider {
  id: string;
  model: string;
  embedQuery: (text: string) => Promise<number[]>;
  embedBatch: (texts: string[]) => Promise<number[][]>;
}
```

#### 5.2 自定义存储后端

当前使用 SQLite，但架构支持扩展：

```typescript
interface MemorySearchManager {
  search(...): Promise<MemorySearchResult[]>;
  sync(...): Promise<void>;
  status(): MemoryProviderStatus;
}
```

---

## 总结

OpenClaw 的记忆管理系统是一个**本地优先、隐私友好、功能强大**的解决方案：

### 核心优势

1. **本地存储**: 所有数据存储在本地，保护隐私
2. **混合搜索**: 结合向量搜索和关键词搜索，提高检索质量
3. **自动同步**: 文件系统监控和增量更新，保持索引最新
4. **灵活配置**: 支持多种嵌入模型和存储策略
5. **性能优化**: 批量处理、缓存、并发控制等优化手段

### 技术亮点

- **SQLite + sqlite-vec**: 轻量级向量数据库
- **FTS5**: 全文搜索支持
- **混合搜索算法**: 结合语义和关键词匹配
- **增量同步**: 高效的索引更新机制
- **多模型支持**: OpenAI、Gemini、本地模型

### 未来方向

根据代码中的实验性功能，未来可能的方向：

1. **知识图谱**: 实体关系提取和链接
2. **时间查询**: 基于时间范围的记忆检索
3. **置信度评分**: 记忆的置信度和证据追踪
4. **多模态记忆**: 支持图片、音频等非文本记忆

---

## 参考资料

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [记忆系统文档](https://docs.openclaw.ai/concepts/memory)
- [会话管理文档](https://docs.openclaw.ai/concepts/session)
- [源代码仓库](https://github.com/openclaw/openclaw)

---

**文档版本**: 1.0  
**最后更新**: 2026-02-06  
**维护者**: 基于源代码分析生成

