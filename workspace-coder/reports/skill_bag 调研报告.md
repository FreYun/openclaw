# /tmp/skill_bag 目录调研报告

**调研时间**: 2026-03-18  
**调研人**: 工部侍郎 (coder)  
**报告版本**: 1.0

---

## 一、目录概览

### 1.1 基本统计

| 指标 | 数值 |
|------|------|
| 总文件数 | 642 |
| 总目录数 | 180 |
| 技能包数量 | 46 个 |
| 总占用空间 | 6.7MB |
| Markdown 文档 | 207 个 |
| Python 脚本 | ~50+ 个 |
| Shell 脚本 | ~15 个 |

### 1.2 目录结构

```
/tmp/skill_bag/
├── README.md                    # 总体说明文档
├── sync-config.json             # 同步到 openclaw-public 的配置
├── .gitignore                   # Git 忽略规则
│
├── capture-*/                   # 数据抓取类 (8 个)
├── code-*/                      # 代码工具类 (1 个)
├── data-*/                      # 数据分析类 (3 个)
├── deep-*/                      # 深度研究类 (3 个)
├── memory-*/                    # 记忆与认知类 (7 个)
├── news-*/                      # 新闻聚合类 (6 个)
├── stock-*/                     # 股票工具类 (15 个)
├── swarm-*/                     # 多智能体协作类 (2 个)
└── tool-*/                      # 工具类 (1 个)
```

---

## 二、技能分类详解

### 2.1 Capture — 数据抓取类 (8 个)

| 技能名 | 功能描述 | 技术栈 |
|--------|----------|--------|
| `capture-30 天热点` | 30 天热点趋势追踪 | - |
| `capture-arxiv 论文热点跟踪` | ArXiv 论文监控 | Shell 脚本 |
| `capture-blogwatcher` | 博客/RSS 监控 | - |
| `capture-gangtise` | 港股通知识库采集 | - |
| `capture-reddit-search` | Reddit 搜索 | - |
| `capture-search-x` | X (Twitter) 搜索 | - |
| `capture-youtube` | YouTube 视频内容抓取 | Shell 脚本 |
| `capture-韭菜公社` | 韭菜公社数据采集 | Python + Playwright + Gemini AI |

**亮点**: `capture-韭菜公社` 是最复杂的数据抓取技能，包含完整的数据库存储 (SQLite)、AI 结构化解析、多源数据分类 (产业链/异动板块/段子)。

### 2.2 Data — 数据分析类 (3 个)

| 技能名 | 功能描述 | 核心能力 |
|--------|----------|----------|
| `data-回测框架` | 交易策略回测 | 8 种内置策略、参数优化、Sharpe/Sortino 等指标 |
| `data-时间序列分析` | 金融时间序列分析 | ADF/KPSS 检验、STL 分解、Hurst 指数、变点检测 |
| `data-数据可视化` | 数据可视化 | - |

**亮点**: `data-时间序列分析` 包含 8 个方法论文档，覆盖从平稳性检验到网络分析的全流程。

### 2.3 Deep — 深度研究类 (3 个)

| 技能名 | 功能描述 |
|--------|----------|
| `deep-gemini 深度研究` | Gemini 深度研究代理 |
| `deep-事实检测` | 事实核查 |
| `deep-公司快速研究` | 公司深度研究 (含 PDF 报告生成) |

### 2.4 Memory — 记忆与认知类 (7 个)

| 技能名 | 版本 | 功能描述 |
|--------|------|----------|
| `memory-Agent 进化论` | 1.14.0 | 技能进化器 |
| `memory-Idea 教练` | - | 创意教练 |
| `memory-ontology-0.1.2` | 0.1.2 | 本体知识图谱 |
| `memory-self-improving-1.0.11` | 1.0.11 | 自我改进记忆 (最成熟) |
| `memory-thinking-model-enhancer` | - | 思维模型增强 |
| `memory-认知记忆` | 1.0.8 | 认知记忆系统 (多存储架构) |
| `memory-框架学习技能` | - | 框架学习与迁移 |

**亮点**: 
- `memory-self-improving-1.0.11` 是最成熟的技能，有完整的 learnings 日志系统、错误检测、技能提取流程
- `memory-认知记忆` 实现了人类般的多存储记忆架构 (情景/语义/程序/核心记忆)，支持衰减遗忘和反思巩固

### 2.5 News — 新闻聚合类 (6 个)

| 技能名 | 数据源 |
|--------|--------|
| `news-aggregator-skill` | HN/GitHub/PH/36Kr/腾讯/华尔街见闻/V2EX/微博 (8 源) |
| `news-bbc-news` | BBC RSS |
| `news-cctv-news-fetcher` | CCTV |
| `news-daily-ai-news-skill` | AI 新闻 |
| `news-newsapi-search` | NewsAPI |
| `news-summary` | 新闻摘要 |

**亮点**: `news-aggregator-skill` 支持深度抓取 (--deep) 和语义过滤，输出格式为杂志/通讯风格。

### 2.6 Stock — 股票工具类 (15 个)

| 技能名 | 功能 |
|--------|------|
| `stock-a 股技术分析数据准备` | A 股技术面数据 |
| `stock-a 股股票基础研究` | A 股基础研究 |
| `stock-a 股自选股监控` | 自选股监控 |
| `stock-a 股量化监控系统` | A 股量化监控 |
| `stock-tushare 数据 mcp` | Tushare Pro MCP (158+ 接口) |
| `stock-yahoo-finance` | Yahoo Finance |
| `stock-买卖信号追踪` | 买卖信号 (全球 37,565+ 标的) |
| `stock-交易记录工具` | 交易日志 (Markdown + SQLite) |
| `stock-信息交叉验证` | 多源信息交叉验证 |
| `stock-持仓组合监控` | 持仓组合监控 |
| `stock-美股分析组合` | 美股分析 |
| `stock-美股基础数据` | 美股基础数据 |
| `stock-美股股价查询` | 美股股价查询 |
| `stock-股票分析工具` | 股票综合分析 |
| `stock-调研纪要总结` | 调研纪要总结 |

**亮点**: `stock-tushare 数据 mcp` 是最新的 MCP 集成方案，替代旧版 Python 脚本，通过 MCP tool 直接调用 158+ 接口。

### 2.7 Swarm — 多智能体协作类 (2 个)

| 技能名 | 版本 | 功能 |
|--------|------|------|
| `swarm-personas` | 1.2.1 | 角色扮演/多人格代理 |
| `swarm-war-room` | 1.1.0 | 多代理作战室 (头脑风暴/系统设计) |

**亮点**: `swarm-war-room` 是最复杂的多智能体协作框架，包含：
- 19 个 DNA 操作协议 (Socratic/Hermetic/Antifragile/Execution)
- 波浪式执行协议 (Wave Protocol)
- CHAOS 魔鬼代言人机制
- INTERCEPTOR 自主控制器
- 逆向作战室 (Reverse War Room)

### 2.8 Tool — 工具类 (1 个)

| 技能名 | 功能 |
|--------|------|
| `tool-serper 检索` | Serper Google 搜索引擎集成 |

---

## 三、核心技能深度分析

### 3.1 memory-self-improving-1.0.11 (自我改进)

**架构**:
```
.learnings/
├── LEARNINGS.md        # 学习日志 (correction/knowledge_gap/best_practice)
├── ERRORS.md           # 错误日志
└── FEATURE_REQUESTS.md # 功能请求

hooks/
└── openclaw/
    ├── HOOK.md
    ├── handler.js
    └── handler.ts
```

**核心机制**:
1. **触发检测**: 用户纠正/命令失败/API 错误/知识过时
2. **日志格式**: 标准化条目 (ID/优先级/状态/领域/摘要/详情/建议行动)
3. **提升机制**: 将通用学习提升到 CLAUDE.md/AGENTS.md/SOUL.md/TOOLS.md
4. **技能提取**: 满足条件 (重复/已验证/非显而易见) 时自动提取为新技能
5. **Hook 集成**: UserPromptSubmit / PostToolUse 自动触发

**评价**: ⭐⭐⭐⭐⭐ 最成熟的技能之一，有完整的版本历史和生态系统。

### 3.2 swarm-war-room (作战室)

**核心协议**:

| 支柱 | 协议数 | 示例 |
|------|--------|------|
| Socratic (苏格拉底) | 4 | 相反测试/五问法/无知声明/辩证义务 |
| Hermetic (赫尔墨斯) | 6 | 镜像测试/涟漪分析/张力映射 |
| Antifragile (反脆弱) | 5 | 减法指令/B 计划价格标签/90/10 规则 |
| Execution (执行) | 4 | 现实交付/保护声誉/减少混乱/技术卓越 |

**执行流程**:
```
Wave 0: Prove It (验证风险假设) → 
Wave 1-N: Specialist Execution (专家执行) → 
CHAOS Shadow (魔鬼代言人挑战) → 
Pivot Gate (转向检查点) → 
Consolidation (合并蓝图) → 
Post-Mortem (事后复盘)
```

**评价**: ⭐⭐⭐⭐⭐ 企业级多智能体协作框架，适合复杂系统设计和战略规划。

### 3.3 memory-认知记忆 (Cognitive Memory)

**四存储架构**:
```
CONTEXT WINDOW (always loaded)
├── Core Memory / MEMORY.md (~3K tokens)
└── Conversation + Tools

MEMORY STORES (retrieved on demand)
├── Episodic   —  chronological event logs
├── Semantic   — knowledge graph (entities + relationships)
├── Procedural — learned workflows
└── Vault      — user-pinned, never decayed
```

**衰减模型**:
```
relevance(t) = base × e^(-0.03 × days) × log2(access_count + 1) × type_weight
```

**反思流程**:
1. 确认触发 → 2. 请求 Token → 3. 用户批准 → 4. 内部独白反思 → 5. 记录归档

**评价**: ⭐⭐⭐⭐⭐ 最接近人类记忆机制的 AI 记忆系统，支持多 Agent 共享读取。

### 3.4 capture-韭菜公社 (A 股主题跟踪)

**数据流程**:
```
网站抓取 (Playwright) → AI 结构化解析 (Gemini) → SQLite 存储 → 查询脚本输出
```

**数据库结构**:
```sql
articles (文章主表)
stocks (股票实体)
themes (主题实体)
article_stocks (文章↔股票关联)
article_themes (文章↔主题关联)
```

**场景路由**:
| 场景 | 触发词 | 操作 |
|------|--------|------|
| 市场热点 | "产业链""热门板块" | fetch industry_chain → query_industry_chain.py |
| 异动板块 | "有什么异动""涨停分析" | fetch action → query_action.py |
| 最新段子 | "最新段子""看看韭菜" | fetch study_hot (5-15 分钟) → query_latest.py |
| 查询股票 | "XX 股票怎么样" | query_stock.py (直接查库) |

**评价**: ⭐⭐⭐⭐ 完整的 A 股舆情监控系统，但抓取耗时较长。

### 3.5 stock-tushare 数据 mcp (Tushare MCP)

**核心优势**:
- 158+ MCP tool 接口
- 无需写 Python 脚本
- 覆盖 A 股/港股/美股/基金/期货/债券/宏观

**使用流程**:
```
1. 确认需求 → 2. 查 tool 索引 → 3. ToolSearch 加载 → 4. 调用 tool → 5. 存储/展示
```

**常用 Tool**:
| 需求 | Tool | 参数 |
|------|------|------|
| 股票行情 | tushare_daily | ts_code, start_date, end_date |
| 财务三表 | tushare_income/balancesheet/cashflow | ts_code, period |
| 指数走势 | tushare_index_daily | ts_code, start_date, end_date |
| 宏观 GDP | tushare_cn_gdp | q (季度) |

**评价**: ⭐⭐⭐⭐ 最新 MCP 集成方案，替代旧版脚本，但需要 ToolSearch 预加载。

---

## 四、sync-config.json 分析

### 4.1 同步配置

```json
{
  "source_dir": "../openclaw-skills",
  "public_skills": [46 个技能名称]
}
```

**同步策略**: 46 个技能全部列入 `public_skills`，准备发布到 openclaw-public。

### 4.2 排除模式

```
.env, *.key, *.pem, secrets/         # 敏感信息
__pycache__/, *.pyc, node_modules/   # 构建产物
*.db, *.sqlite, data/, output/       # 数据文件
*.log, tmp/, cache/                  # 临时文件
*.csv, *.xlsx, *.mp4, *.mp3          # 大文件
```

**评价**: 排除规则完善，保护敏感信息和大型数据文件。

---

## 五、潜在问题与建议

### 5.1 发现的问题

| 问题 | 严重程度 | 描述 |
|------|----------|------|
| 中文目录名编码问题 | 中 | 部分目录名含中文，在某些环境下可能访问失败 (如 `stock-tushare 数据 mcp`) |
| 技能版本不一致 | 低 | 部分技能有详细版本历史 (如 memory-Agent 进化论 1.14.0)，部分无版本号 |
| 文档质量参差 | 中 | 部分技能只有基础 SKILL.md，缺少 reference/examples 等补充文档 |
| 依赖管理不统一 | 低 | 部分用 uv，部分用 pip，部分用 requirements.txt |
| 测试覆盖率未知 | 中 | 仅 `stock-tushare 数据 mcp` 有 tests 目录 (且被.gitignore 排除) |
| API Key 管理 | 中 | 部分技能用 `.env`，部分用 MCP 服务器鉴权，缺少统一规范 |

### 5.2 改进建议

#### 短期 (1-2 周)

1. **统一中文目录名为英文**
   - 例如：`stock-tushare 数据 mcp` → `stock-tushare-mcp`
   - 避免跨平台编码问题

2. **补充缺失的文档**
   - 为每个技能添加 `examples.md` 或 `usage-examples.md`
   - 为复杂技能添加 `architecture.md` 或 `design.md`

3. **建立技能质量检查清单**
   ```markdown
   - [ ] SKILL.md 包含完整的使用示例
   - [ ] 有 .env.example 模板
   - [ ] 有 install/uninstall 脚本
   - [ ] 有测试用例或验证脚本
   - [ ] 有版本号 (_meta.json)
   ```

#### 中期 (1-2 月)

4. **统一依赖管理**
   - 推荐使用 `uv` (更现代、更快)
   - 或统一用 `requirements.txt` + `pip`

5. **建立技能测试框架**
   - 为每个技能添加 `tests/` 目录
   - 编写基本功能测试
   - CI/CD 集成

6. **API Key 管理规范化**
   - 统一使用 `.env.example` 模板
   - 添加密钥验证脚本
   - 文档中明确标注需要的 API Key

#### 长期 (3-6 月)

7. **技能依赖图谱**
   - 分析技能间的依赖关系
   - 建立技能加载顺序
   - 避免循环依赖

8. **技能性能基准**
   - 测量每个技能的执行时间
   - 测量 Token 消耗
   - 建立性能回归测试

9. **技能市场集成**
   - 将 46 个技能发布到 clawhub.com
   - 建立技能评分和评论系统
   - 支持技能一键安装/更新

---

## 六、技能生态分析

### 6.1 技能来源

| 来源 | 数量 | 占比 |
|------|------|------|
| kirkluokun (Admin?) | ~10+ | ~22% |
| openclaw/skills | ~5 | ~11% |
| clawdbot/skills | ~15 | ~33% |
| 其他贡献者 | ~16 | ~34% |

### 6.2 技能成熟度

| 成熟度 | 技能数 | 特征 |
|--------|--------|------|
| 生产就绪 | ~15 | 完整文档、测试、版本历史、Hook 支持 |
| 可用 | ~20 | 基本文档、可运行 |
| 实验性 | ~11 | 文档不全、缺少测试 |

### 6.3 技能依赖的外部服务

| 服务 | 使用技能数 |
|------|------------|
| Tushare Pro | 5+ |
| Gemini AI | 3+ |
| Serper API | 1 |
| NewsAPI | 1 |
| Yahoo Finance | 2 |
| Playwright | 5+ |

---

## 七、总结

### 7.1 整体评价

`/tmp/skill_bag` 是一个**高质量、覆盖面广的 OpenClaw 技能集合**，专注于 A 股投资研究与分析，同时涵盖记忆系统、多智能体协作、新闻聚合等通用能力。

**优势**:
- ✅ 技能分类清晰 (8 大类 46 个技能)
- ✅ 核心技能成熟度高 (self-improving/war-room/cognitive-memory)
- ✅ 文档质量整体较好
- ✅ 有完整的同步配置和.gitignore
- ✅ 部分技能有版本历史和生态系统

**不足**:
- ❌ 中文目录名可能导致编码问题
- ❌ 技能质量参差，部分缺少测试
- ❌ 依赖管理不统一
- ❌ API Key 管理缺少规范

### 7.2 推荐行动

1. **立即**: 修复中文目录名编码问题
2. **本周**: 为缺失文档的技能补充 examples.md
3. **本月**: 建立技能质量检查清单和测试框架
4. **下季度**: 发布到 clawhub.com，建立技能市场

---

**报告完成时间**: 2026-03-18 16:30  
**下一步**: 等待 Admin 审阅，确认是否需要执行改进建议
