# Skill 树结构 + 投机预加载 设计方案

## Context

当前 skill 系统是扁平结构：所有 equipped skill 按 slot 分桶列在 EQUIPPED_SKILLS.md 里，bot 启动时全量扫描。执行时 Claude 串行调 MCP tool，每步等结果再发下一步，大量时间浪费在等待 IO 上。

目标：
1. **技能分类树** — skill 按领域分类组织，bot 按需导航展开
2. **投机预加载** — 执行 step N 时后台预拉 step N+1 的数据，到达时直接命中缓存，未选中分支剪枝

---

## Part 1: 技能分类树

### 1.1 skill.json 新增 `category` 字段

```json
{
  "name": "TMT全景",
  "category": "行业研究/TMT",
  "slot": "research",
  ...
}
```

- 用 `/` 分隔层级，支持任意深度
- 向后兼容：无 category 的 skill 按 slot 归类到默认分组
- category 纯分类用途，不影响 slot 装备逻辑

### 1.2 分类规划

```
研究技能/
├── 行业研究/
│   ├── TMT/        → tmt-landscape
│   ├── 光伏/       → solar-tracker
│   └── 通用/       → sector-pulse
├── 个股研究/       → research-stock, earnings-digest, technical-analyst
├── 宏观/           → market-environment-analysis
└── 资讯/           → news-factcheck, report-digest, report-critique

运营技能/
├── 小红书/         → xhs-op, xhs-nurture, xhs-topic-collector
├── 公众号/         → gzh-publish
└── 合规/           → compliance-review

风格/
├── 内容风格/       → laicaimeimei-writing-style, xuanma-style, ...
└── 画图风格/       → laicaimeimei-cover-style, default-cover-style, ...
```

### 1.3 EQUIPPED_SKILLS.md 改为树形渲染

修改 `dashboard/server.js` 的 `generateSkillsManifest()`：

```markdown
# 已装备技能

## 研究技能
### 行业研究
- TMT全景（tmt-landscape） — `skills/tmt-landscape/SKILL.md`
- 光伏跟踪（solar-tracker） — `skills/solar-tracker/SKILL.md`
### 个股研究
- 个股分析（research-stock） — `skills/research-stock/SKILL.md`

## 运营技能
### 小红书
- 小红书运营（xhs-op） — `skills/xhs-op/SKILL.md`
```

### 1.4 改动文件

| 文件 | 改动 |
|------|------|
| `workspace/skills/*/skill.json` | 各 skill 加 `category` 字段 |
| `dashboard/server.js` `generateSkillsManifest()` | 按 category 树分组渲染 |
| `dashboard/server.js` `scanAllSkills()` | 解析 category 字段到 registry |

---

## Part 2: Step DAG 声明

### 2.1 skill.json 新增 `pipeline` 字段

```json
{
  "name": "TMT全景",
  "category": "行业研究/TMT",
  "pipeline": {
    "steps": [
      {
        "id": "pricing-env",
        "name": "定价环境",
        "prefetch": [
          {"mcp": "tushare", "tool": "tushare_index_daily", "args": {"ts_code": "000998.CSI,000300.SH,399006.SZ", "limit": 60}},
          {"mcp": "research-mcp", "tool": "get_ashares_index_val"},
          {"mcp": "research-mcp", "tool": "get_cn_bond_yield"},
          {"mcp": "research-mcp", "tool": "market_overview"}
        ],
        "next": ["sector-scan"]
      },
      {
        "id": "sector-scan",
        "name": "四方向景气",
        "prefetch": [
          {"mcp": "research-mcp", "tool": "research_search", "args": {"query": "电子半导体研报", "top_k": 3}},
          {"mcp": "research-mcp", "tool": "research_search", "args": {"query": "计算机AI研报", "top_k": 3}},
          {"mcp": "research-mcp", "tool": "research_search", "args": {"query": "通信算力研报", "top_k": 3}},
          {"mcp": "research-mcp", "tool": "research_search", "args": {"query": "传媒游戏研报", "top_k": 3}}
        ],
        "next": ["earnings-verify"]
      },
      {
        "id": "earnings-verify",
        "name": "盈利验证",
        "prefetch": "dynamic",
        "next": ["fund-flow", "policy"]
      },
      {
        "id": "fund-flow",
        "name": "资金行为",
        "prefetch": "dynamic",
        "next": ["consistency-check"]
      },
      {
        "id": "policy",
        "name": "政策分析",
        "prefetch": [
          {"mcp": "research-mcp", "tool": "news_search", "args": {"query": "TMT科技政策", "top_k": 5}}
        ],
        "next": ["consistency-check"]
      },
      {
        "id": "consistency-check",
        "name": "逻辑自洽",
        "next": ["report"]
      },
      {
        "id": "report",
        "name": "输出报告"
      }
    ]
  }
}
```

### 2.2 prefetch 类型

| 类型 | 含义 | 例子 |
|------|------|------|
| `prefetch: [...]` | 静态调用列表，参数已知，可立即预拉 | Step 1 的指数数据 |
| `prefetch: "dynamic"` | 参数依赖前序步骤输出，不可静态预拉 | Step 3 的个股数据（依赖 step 2 选出的龙头） |
| 无 prefetch | 纯分析步骤，不需要数据拉取 | Step 6 自洽检验 |

---

## Part 3: Prefetch Engine（新 MCP 服务）

### 3.1 架构

```
                    ┌─────────────────┐
                    │  prefetch-mcp   │  ← 新服务，端口 :18095
                    │  (Node.js)      │
                    ├─────────────────┤
                    │ HTTP API:       │
                    │  POST /prefetch │  ← 提交预加载任务
                    │  GET  /cache    │  ← 查询缓存
                    │  POST /prune    │  ← 剪枝
                    │  POST /start    │  ← 启动 pipeline
                    ├─────────────────┤
                    │ 内部:           │
                    │  - 任务队列     │
                    │  - MCP 转发层   │  → 调 research-mcp / tushare 等
                    │  - 结果缓存     │  TTL 30min, LRU 淘汰
                    │  - DAG 解析器   │  读 skill.json pipeline
                    └─────────────────┘
```

### 3.2 工作流程

```
1. Bot 开始执行 skill
   → Claude 调 prefetch-mcp.start_pipeline(skill_id="tmt-landscape")
   → Engine 读 skill.json，解析 DAG
   → 立即预拉 step 1 (pricing-env) 的 4 个 MCP calls（并行）
   → 同时预拉 step 2 (sector-scan) 的 4 个 research_search（因为 step 1→2 是静态链）

2. Claude 执行 Step 1
   → 调 prefetch-mcp.fetch(pipeline_id, step="pricing-env", tool="tushare_index_daily", args={...})
   → Engine 查缓存：命中 → 直接返回（~0ms）
   → 未命中 → 实时调用，返回结果

3. Step 1 完成，Claude 进入 Step 2
   → Step 2 的数据已在后台拉完 → 全部缓存命中
   → 同时 Engine 看到 step 2 的 next 是 earnings-verify（dynamic）
   → dynamic 步骤无法预拉，等待

4. Step 2 完成，Claude 决定聚焦哪些方向
   → Claude 调 prefetch-mcp.prefetch_dynamic(pipeline_id, step="earnings-verify", calls=[...])
   → Engine 后台开始拉个股数据
   → 同时预拉 step 5 (policy) 的静态 news_search

5. 分支剪枝
   → Claude 走完 step 3，选择了 fund-flow 而非 policy 先执行
   → 无需显式剪枝，policy 的预拉数据留在缓存（30min TTL 自然过期）
   → 如果最终也走到 policy，缓存还在 → 命中
```

### 3.3 MCP Tools 暴露

```
start_pipeline(skill_id, bot_id)
  → 读 skill.json，创建 pipeline 实例，预拉第一波静态 calls
  → 返回 pipeline_id

fetch(pipeline_id, step_id, mcp, tool, args)
  → 查缓存，命中直接返回；未命中则实时调用
  → 触发下一步静态 prefetch

prefetch_dynamic(pipeline_id, step_id, calls[])
  → 手动提交动态预拉任务（参数来自前序步骤输出）

prune(pipeline_id, pruned_steps[])
  → 删除指定步骤的缓存（可选，不调也会 TTL 过期）

pipeline_status(pipeline_id)
  → 返回各步骤缓存命中率、预拉状态
```

### 3.4 MCP 转发层

Prefetch engine 不直接实现数据拉取，而是转发到已有 MCP：

```javascript
// 转发配置
const MCP_ENDPOINTS = {
  "research-mcp": "http://localhost:18080/mcp/${bot_id}",
  "tushare": "http://localhost:18080/mcp/${bot_id}",  // tushare 集成在 research-mcp 里
};

async function forwardMcpCall(mcp, tool, args, botId) {
  // 建立 MCP session → tools/call → 返回结果
}
```

### 3.5 缓存设计

```
/tmp/prefetch-cache/
├── {pipeline_id}/
│   ├── pricing-env/
│   │   ├── tushare_index_daily_{hash}.json    ← 结果 + 元数据
│   │   ├── get_ashares_index_val_{hash}.json
│   │   └── ...
│   ├── sector-scan/
│   │   └── ...
│   └── _meta.json    ← pipeline 元数据（创建时间、DAG、状态）
```

- TTL: 30 分钟（研究数据时效性）
- 缓存 key: `${tool}_${sha256(JSON.stringify(args))}`
- LRU: 最多保留 50 个 pipeline 实例
- 剪枝: 显式 prune 或 TTL 自然过期

---

## Part 4: SKILL.md 改写约定

### 4.1 新增 prefetch 指令块

在每个 Step 开头加 prefetch 提示：

```markdown
## Step 1 — 定价环境

> **Prefetch**: 本步数据已由 pipeline 预加载，用 `fetch()` 获取。

调用 `prefetch-mcp.fetch(pipeline_id, "pricing-env", "tushare_index_daily", {...})` 获取数据...
```

### 4.2 动态预拉指令

```markdown
## Step 2 → Step 3 过渡

> 根据 Step 2 确定的龙头标的，提交动态预拉：
> `prefetch-mcp.prefetch_dynamic(pipeline_id, "earnings-verify", [
>   {mcp: "tushare", tool: "tushare_daily_basic", args: {ts_code: "..."}},
>   ...
> ])`
```

### 4.3 Pipeline 启动/结束

```markdown
# TMT 全景研究

**执行前**：`prefetch-mcp.start_pipeline("tmt-landscape")` → 获取 pipeline_id

...（各步骤）...

**执行后**：pipeline 自动过期，无需手动清理
```

---

## Part 5: 实施步骤

### Phase 1: 技能树（1-2天）
1. 设计 category 分类方案，给所有 ~45 个 skill 的 skill.json 加 category
2. 修改 `dashboard/server.js` 的 `generateSkillsManifest()` 按树渲染
3. 修改 `scanAllSkills()` 解析 category
4. 重新 SYNC 所有 bot，验证 EQUIPPED_SKILLS.md 渲染正确

### Phase 2: Prefetch MCP 服务（3-5天）
1. 创建 `/home/rooot/MCP/prefetch-mcp/` Node.js 项目
2. 实现核心：DAG 解析 + MCP 转发 + 文件缓存 + TTL/LRU
3. 暴露 4 个 MCP tools（start_pipeline / fetch / prefetch_dynamic / prune）
4. 注册到 gem-registry.json

### Phase 3: TMT-landscape 试点（1-2天）
1. 给 tmt-landscape 的 skill.json 加 pipeline 定义
2. 改写 SKILL.md 使用 prefetch-mcp 调用
3. 让 sys3 或 bot7 实测，对比有/无 prefetch 的执行时间
4. 验证缓存命中率和数据正确性

### Phase 4: 推广（按需）
1. 给其他多步 research skill 加 pipeline（sector-pulse, solar-tracker, earnings-digest）
2. 总结 pipeline 声明的最佳实践
3. 更新 skill-generate 模板，新 skill 自带 pipeline 声明

---

## 验证方案

1. **树结构验证**: SYNC 后检查各 bot 的 EQUIPPED_SKILLS.md 是否按树渲染
2. **Prefetch 功能验证**:
   - `curl` 调 prefetch-mcp 的 start_pipeline → 检查缓存目录是否生成
   - 调 fetch → 检查缓存命中（对比直接调 MCP 的延迟）
   - TTL 过期后再调 → 确认重新拉取
3. **端到端验证**: bot7 跑 tmt-landscape，对比日志中各步骤耗时
4. **回归验证**: 无 pipeline 的 skill 不受影响，正常执行
