# /tmp/skill_bag Memory 技能深度调研报告

**调研时间**: 2026-03-18  
**调研人**: 工部侍郎 (coder)  
**版本**: 1.0

---

## 〇、核心发现（先说结论）

**OpenClaw 已内置完整的记忆搜索基础设施**（SQLite + FTS5 + 可选向量），但当前**全部 agent 均未启用索引**（Provider: none, Indexed: 0 chunks）。skill_bag 中的 6 个记忆技能**全部是纯文件/JSON 存储，无向量化实现**。

最高 ROI 的动作不是引入 skill_bag 技能，而是**直接激活 OpenClaw 内置的 memorySearch**——只需一行配置，即可为所有 agent 启用 FTS + 向量搜索。

---

## 一、各 Memory 技能实现方式详解

### 1.1 汇总矩阵

| 技能 | 存储方式 | 检索机制 | 向量化 | 代码量 | 成熟度 |
|------|---------|---------|--------|--------|--------|
| **memory-self-improving** 1.0.11 | Markdown 文件 (.learnings/) | LLM 上下文注入 (无检索) | ❌ 无 | ~650 行 SKILL.md + 3 脚本 | ⭐⭐⭐⭐⭐ |
| **memory-认知记忆** 1.0.8 | Markdown + JSON (decay-scores.json) | LLM 路由分类 + 架构图提到 Vector+BM25 但**未实现** | ⚠️ 设计有，实现无 | 1275 行架构文档 + 模板 | ⭐⭐⭐⭐ |
| **memory-ontology** 0.1.2 | JSONL 图谱 (graph.jsonl) | Python CLI 属性查询 + 图遍历 | ❌ 无 | ~400 行 Python | ⭐⭐⭐ |
| **memory-Agent 进化论** 1.14.0 | JSONL 事件日志 + JSON 基因/胶囊 | Node.js 信号匹配 + 哈希去重 | ❌ 无 | ~50 个 JS 文件 | ⭐⭐⭐ |
| **memory-thinking-model** | JSON 快照文件 (每个一个 .json) | 关键词重叠计数排序 | ❌ 无 | ~400 行 Python | ⭐⭐ |
| **memory-Idea 教练** 0.2.0 | JSON 文件 (ideas.json) | 线性遍历 + 状态/类型过滤 | ❌ 无 | ~300 行 Python | ⭐⭐ |

### 1.2 逐个深度分析

#### memory-self-improving-1.0.11

**存储**:
```
.learnings/
├── LEARNINGS.md      # 学习日志，Markdown 条目
├── ERRORS.md         # 错误日志
└── FEATURE_REQUESTS.md  # 功能请求
```
- 纯 Markdown 追加写入
- 每条记录有结构化元数据（ID/Priority/Status/Domain/Summary）
- 无数据库，无索引

**检索机制**: **无检索** — 依赖 LLM 在 context window 中直接读取全部 .learnings/ 文件。当文件超出 context 限制时会丢失早期记录。

**向量化**: 完全没有。

**提升机制**: 重要 learning 手动"提升"到 AGENTS.md/SOUL.md/TOOLS.md（由 LLM 判断）。

#### memory-认知记忆 1.0.8

**存储**:
```
memory/
├── episodes/        # Markdown 日志 (YYYY-MM-DD.md)
├── graph/
│   ├── index.md     # 实体注册表 + 边表（Markdown 表格）
│   ├── entities/    # 每个实体一个 .md 文件
│   └── relations.md # 关系类型定义
├── procedures/      # 工作流模板 (.md)
├── vault/           # 固定记忆
└── meta/
    ├── decay-scores.json  # 衰减分数
    ├── reflection-log.md  # 反思历史
    └── audit.log          # 审计日志
```
- 主存储全部是 Markdown + JSON
- 知识图谱以 Markdown 表格形式存储（非图数据库）
- 衰减分数以 JSON 存储

**检索机制**: 
- **设计层面**: 架构文档明确提到 "Vector Index + BM25 Search"（第 46-47 行），并引用 OpenClaw 的 `memorySearch` 配置（provider: voyage）
- **实现层面**: **完全未实现向量搜索**。所有检索依赖 LLM 读取 Markdown 文件 + LLM 路由分类（routing-prompt.md）
- 知识图谱检索靠 LLM 读取 graph/index.md 表格

**向量化**: 
- 架构设计了 Vector Index 层（见架构图第 46 行）
- 引用了 `memorySearch.provider: "voyage"` 配置
- 但 **没有任何代码实现向量化**——既没有 embedding 生成脚本，也没有向量存储代码
- 本质上是"画了架构图但没写代码"

**衰减模型**: `relevance(t) = base × e^(-0.03 × days) × log2(access_count + 1) × type_weight`
- 这个模型在 decay-scores.json 中维护
- 由 LLM 在反思时手动计算和更新（不是自动化的后台进程）

#### memory-ontology 0.1.2

**存储**: JSONL 追加日志 (`memory/ontology/graph.jsonl`)
```jsonl
{"op":"create","entity":{"id":"p_001","type":"Person","properties":{"name":"Alice"}}}
{"op":"relate","from":"proj_001","rel":"has_task","to":"task_001"}
```

**检索机制**: Python CLI (`ontology.py`) 实现：
- `query --type Task --where '{"status":"open"}'` — 属性精确匹配
- `related --id proj_001 --rel has_task` — 一跳图遍历
- `validate` — Schema 约束校验
- **线性扫描全部 JSONL 重建内存图**，无索引

**向量化**: 完全没有。纯属性匹配 + 图遍历。

#### memory-Agent 进化论 1.14.0

**存储**: 
```
assets/gep/
├── genes.json       # 可复用基因定义
├── capsules.json    # 成功胶囊（避免重复推理）
└── events.jsonl     # 追加事件日志（树形结构，有 parent_id）
```
- Node.js 实现 (`src/gep/memoryGraph.js`)
- 内存图（`stableHash` 去重 + 信号匹配）
- 事件日志追加写入

**检索机制**: 
- `normalizeErrorSignature()` — 错误签名标准化后哈希匹配
- `normalizeSignalsForMatching()` — 信号关键词匹配
- 无搜索 API，靠遍历 events.jsonl

**向量化**: 完全没有。在 SKILL.md 中提到 "cosine similarity" 但仅作为概念引用，代码中没有任何 embedding 计算。

#### memory-thinking-model-enhancer

**存储**: 每个思维快照一个 JSON 文件 (`~/.claude/thinking_models/memory/*.json`)
- `model_index.json` — 全局索引（类型统计、成功率）
- `{snapshot_id}.json` — 每次思维过程的快照

**检索机制** (`thinking_memory.py`):
```python
def query_similar_problems(self, query, model_type=None, limit=5):
    # 关键词分词 → 集合交集 → overlap 计数排序
    query_keywords = set(re.findall(r'[\w]+', query.lower()))
    snapshot_keywords = set(re.findall(r'[\w]+', snapshot["problem_summary"].lower()))
    overlap = len(query_keywords & snapshot_keywords)
```
- **纯关键词重叠计数**，不是 TF-IDF，不是 BM25，更不是向量搜索
- 线性遍历所有 JSON 快照文件

**向量化**: 完全没有。

#### memory-Idea 教练 0.2.0

**存储**: 单个 JSON 文件 (`~/.openclaw/idea-coach/ideas.json`)
- 所有 idea 存在一个 JSON 数组中

**检索机制**: 线性遍历 + 状态/类型/到期日过滤
- 无搜索，纯属性过滤

**向量化**: 完全没有。

---

## 二、当前记忆基础设施状态

### 2.1 OpenClaw 内置记忆系统（关键发现）

OpenClaw **已经内置了完整的记忆搜索基础设施**：

```
~/.openclaw/memory/
├── bot_main.sqlite      # SQLite + FTS5，已创建
├── coder.sqlite
├── bot1.sqlite
├── bot2.sqlite
├── ...（每个 agent 一个）
├── bot11.sqlite
├── mcp_publisher.sqlite
└── skills.sqlite
```

**当前状态**（`openclaw memory status` 输出）:

| Agent | 文件数 | 已索引 | Provider | FTS | Vector | 状态 |
|-------|--------|--------|----------|-----|--------|------|
| bot_main | 11 | 0/11 | none | ready | unknown | ❌ 未索引 |
| bot1 | 10 | 0/10 | none | ready | unknown | ❌ 未索引 |
| bot2 | 6 | 0/6 | none | ready | unknown | ❌ 未索引 |
| bot3 | 3 | 0/3 | none | ready | unknown | ❌ 未索引 |
| bot4 | 16 | 0/16 | none | ready | unknown | ❌ 未索引 |
| bot5 | 24 | 0/24 | none | ready | unknown | ❌ 未索引 |
| bot6 | 8 | 0/8 | none | ready | unknown | ❌ 未索引 |
| bot7 | 11 | 0/11 | none | ready | unknown | ❌ 未索引 |
| bot11 | 31 | 0/31 | none | ready | unknown | ❌ 未索引 |
| **合计** | **~130** | **0** | — | — | — | **全部休眠** |

**关键**:
- SQLite 存储已创建 ✅
- FTS5 全文搜索引擎已就绪 ✅  
- 但 Provider = none，所有文件都是 Dirty（未索引）❌
- Embedding 缓存已启用但为空 ❌
- 向量搜索状态 unknown ❌

### 2.2 激活只需一行配置

根据 OpenClaw 配置文档，激活 memorySearch 只需要：

```json5
{
  agents: {
    defaults: {
      memorySearch: {
        provider: "gemini",                    // 或 "voyage"
        model: "gemini-embedding-001",         // embedding 模型
        remote: {
          apiKey: "${GEMINI_API_KEY}"           // 已有的 Gemini key
        }
      }
    }
  }
}
```

然后执行：
```bash
openclaw memory index          # 批量索引所有 agent 的记忆文件
openclaw memory search "xxx"   # 语义搜索
```

---

## 三、批量向量化记忆的成本与收获评估

### 3.1 方案对比

| 方案 | 做法 | 开发成本 | 运行成本 | 收获 |
|------|------|---------|---------|------|
| **A: 激活 OpenClaw 内置 memorySearch** | 配置 provider + 执行 index | **10 分钟** | Embedding API 调用费 | FTS + 向量搜索全部 agent |
| **B: 仅启用 FTS (无向量)** | 配置 provider=auto，不配 embedding | **5 分钟** | **零** | 全文关键词搜索 |
| **C: 引入 skill_bag 记忆技能** | 安装+配置+改造 | 1-3 天 | 极低 | 结构化记忆管理 |
| **D: A + C 组合** | 先激活内置搜索，再叠加 skill 的结构化管理 | 1-3 天 | Embedding API 费 | 最强 |

### 3.2 方案 A 详细成本

#### 开发成本
- 配置修改: 1 行 JSON
- 初始索引: `openclaw memory index`（~130 个文件，几分钟）
- 验证测试: `openclaw memory search "某个主题"`
- **总计: 10-15 分钟**

#### 运行成本（Embedding API）

以 Gemini embedding 为例：

| 指标 | 估算 |
|------|------|
| 当前记忆文件总数 | ~130 个 |
| 平均每文件 chunk 数 | ~5-10 |
| 初始索引总 chunk | ~1,000 |
| Gemini embedding 价格 | 免费额度内 / 极低 |
| 每日新增文件 | ~5-10 个 |
| 每日增量索引成本 | **几乎为零** |

以 Voyage AI 为例：
| 指标 | 估算 |
|------|------|
| Voyage-3 价格 | $0.06 / 1M tokens |
| 初始索引 ~1000 chunks × ~500 tokens | ~500K tokens ≈ $0.03 |
| 每月增量 | < $0.10 |

**结论**: 成本可忽略不计。

#### 资源消耗
- SQLite 已存在，无额外存储
- Embedding cache 在 SQLite 中，几 MB 级别
- 无需额外服务进程

### 3.3 收获评估

#### 直接收获

| 能力 | 当前 | 激活后 |
|------|------|--------|
| "上次关于 X 的讨论" | ❌ 需手动翻日记 | ✅ 语义搜索秒出 |
| "bot5 知道什么关于 Y" | ❌ 只能读 MEMORY.md | ✅ 搜索全部记忆文件 |
| 跨日记主题关联 | ❌ 不可能 | ✅ 向量相似度自动关联 |
| 心跳时检索历史 | ❌ 只读当天+昨天日记 | ✅ 搜索所有相关记忆 |
| Agent 自主回忆 | ❌ 受 context window 限制 | ✅ 按需检索，不占 context |

#### 间接收获
- **一致性改善**: Agent 不再"忘记"之前的决策和经验
- **减少重复错误**: 同类问题的历史处理方案可被检索到
- **提升用户体验**: "你之前不是说过 X 吗？" → Agent 可以准确回忆

---

## 四、skill_bag 技能是否可复用

### 4.1 与 OpenClaw 内置系统的关系

| 层次 | OpenClaw 内置 | skill_bag 技能 | 关系 |
|------|-------------|---------------|------|
| **存储层** | SQLite + FTS5 + 向量 | Markdown + JSON | 内置更强 |
| **检索层** | BM25 + 向量搜索 | 无/LLM 读取 | 内置完胜 |
| **结构层** | 无（原始 chunk） | 四存储/知识图谱/衰减 | skill 更丰富 |
| **管理层** | 无（只存不管） | 触发/路由/反思/衰减/审计 | skill 更丰富 |

**结论**: **互补关系，不是替代关系。**

- OpenClaw 内置解决了 **存储和检索** 问题（最底层）
- skill_bag 技能解决了 **结构化管理** 问题（上层）
- 最佳方案是两者结合

### 4.2 各技能复用评估

| 技能 | 可复用性 | 建议 |
|------|---------|------|
| **memory-self-improving** | ⭐⭐⭐⭐⭐ 直接可用 | 立即安装，零改造 |
| **memory-认知记忆** | ⭐⭐⭐ 需大幅改造 | 取其结构设计（四存储+衰减），丢其实现（Markdown 表格图谱），底层接入 OpenClaw memorySearch |
| **memory-ontology** | ⭐⭐⭐ 可选用 | JSONL 图谱适合小规模结构化知识，大规模时换 SQLite |
| **memory-Agent 进化论** | ⭐ 不推荐 | 过于复杂、风险高、与体系不兼容 |
| **memory-thinking-model** | ⭐⭐ 有参考价值 | 快照思路好，但关键词匹配检索太弱，接入向量搜索后可大幅提升 |
| **memory-Idea 教练** | ⭐⭐ 场景单一 | 需要时再用，与记忆框架无关 |

---

## 五、落地建议与优先级

### Phase 0: 激活内置 memorySearch（今天就能做，10 分钟）

```bash
# 1. 配置 memorySearch（使用已有的 Gemini API Key）
openclaw config set memorySearch.provider "gemini"
openclaw config set memorySearch.model "gemini-embedding-001"

# 2. 重启 gateway
openclaw gateway restart

# 3. 执行全量索引
openclaw memory index --verbose

# 4. 验证
openclaw memory status --deep
openclaw memory search "小红书内容创作"
```

**预期效果**: 所有 agent 立即获得语义搜索能力，~130 个记忆文件全部可检索。

### Phase 1: 安装 self-improving 技能（0.5 天）

为活跃 bot 安装 self-improving，开始积累结构化学习日志。

```bash
clawhub install self-improving-agent
```

### Phase 2: 改造认知记忆的结构设计（3-5 天）

取 memory-认知记忆的**设计精华**，丢弃其 Markdown 实现，在 OpenClaw memorySearch 之上构建：

**保留**:
- 四存储概念（episodic/semantic/procedural/vault）
- 衰减模型
- LLM 路由分类 (routing-prompt.md)
- 审计追踪

**改造**:
- 底层存储 → OpenClaw SQLite + 向量索引
- 检索 → `openclaw memory search` API
- 去掉反思独白/Token 请求等重流程
- 多 bot 独立运行

### Phase 3: 评估 ontology 图谱需求（视需求）

当跨 bot 结构化知识共享成为刚需时，引入 ontology 图谱或考虑 OpenClaw memorySearch 的 `extraPaths` 共享目录。

---

## 六、总结

| 发现 | 结论 |
|------|------|
| skill_bag 有向量化实现吗？ | **没有。6 个技能全部是纯文件/JSON 存储，无向量化代码。** memory-认知记忆设计了向量层但未实现。 |
| 需要引入批量向量化吗？ | **不需要额外引入，OpenClaw 已内置。** 只需激活配置。 |
| 激活向量化的成本？ | **10 分钟配置 + 几乎零运行成本（Gemini 免费额度足够）** |
| 激活后的收获？ | **所有 agent 获得语义记忆搜索能力，130+ 文件可检索** |
| skill_bag 技能还有用吗？ | **有用，但定位不同。** self-improving 直接可用；认知记忆的结构设计值得借鉴；其余参考价值有限。 |

**一句话建议**: 先花 10 分钟激活 OpenClaw 内置的 memorySearch，**立竿见影**。然后再考虑是否需要 skill_bag 技能的结构化管理能力。

---

**报告完成时间**: 2026-03-18 20:00  
**下一步**: 请 Admin 确认是否立即激活 memorySearch
