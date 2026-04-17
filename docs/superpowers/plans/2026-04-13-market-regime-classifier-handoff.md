# Market Regime Classifier — 交接执行指南

**创建日期**：2026-04-13
**目标读者**：下一个 session（可能是另一个 Claude 实例或人类开发者）
**当前阶段**：spec 已定稿，准备进入 implementation
**spec 路径**：`docs/superpowers/specs/2026-04-13-market-regime-classifier-design.md`（commits `5741d66` → `824802f` → `f681942`）

---

## 0. 一分钟摘要

要构建一个通用 skill `market-regime-classifier`：读取 daily_review 的复盘 MD + akshare 指数数据 → 六维打分 → 映射到 5 档 regime（强牛/强势震荡/中性震荡/弱势震荡/熊）→ 输出战法推荐和仓位上限（MD + JSON + log）。

这是 **strategy 系新 slot 的第一个 skill**，也是未来 `short-term-sector-momentum`（超短策略）的上游依赖。本 skill 只做判断和推荐，**不做执行，不做回测**。

上手第一步：完整读 spec（14 节，约 420 行），理解六维打分、3 日确认、逃生门、Regime 映射。spec 里的每一条规则都是对话里反复确认过的，**不要轻易改规则**，有疑问先问用户。

---

## 1. 已做决策（不要再折腾）

这些决策来自长时间的用户对话和讨论，改动前必须确认：

### 1.1 架构决策

- **归类**：`workspace/skills/strategy/market-regime-classifier/`，**strategy 是新分类**，workspace/skills 目前没有这个 slot，需要新建。CATALOG.md 需加 "📊 策略 (Strategy)" 章节。
- **作用范围**：通用 skill，不绑定任何 bot。未来由策略型 bot（bot7/bot8）通过 symlink 引用。
- **只做大盘 regime，不做板块/盘中/跨市场**（spec §12 已列出 non-goals）。
- **不做回测**。回测留给下游 strategy skill。

### 1.2 六维打分（最终版，不再改）

spec §4 的表格是最终版。特别注意：**第 4 维是"情绪评分"（0-100 复合指标），不是"炸板率"**。这是用户在 spec 写完后主动替换的（commit `f681942`），原因是炸板率在 daily_review 的复盘 MD 里查不到，而情绪评分直接写在"情绪温度计"章节。

| # | 维度 | 数据字段来源 |
|---|---|---|
| 1 | 指数 vs 均线 | akshare 直接取 HS300（000300）+ CSI1000（000852）的日线，两个指数分别打分后**算术平均 → 四舍五入到最近的整数** |
| 2 | 涨跌家数比 | 复盘 MD "市场全景" 章节 |
| 3 | 情绪（涨停-跌停） | 复盘 MD "情绪温度计" 章节，字段名含 `涨停:跌停 N:M` |
| 4 | 情绪评分 | 复盘 MD "情绪温度计" 章节，`情绪评分 N / 100` |
| 5 | 最高连板高度 | 复盘 MD "连板 & 题材前瞻" 章节，`最高连板 N 板` |
| 6 | 成交量趋势 | 5 日均量 / 20 日均量，可能在 MD 里，也可能需要 akshare 补 |

**每维 -2 ~ +2，总分范围 -12 ~ +12**，等权重。

### 1.3 Regime 映射（spec §5）

- `≥+7` 强牛 / `+2~+6` 强势震荡 / `-1~+1` 中性震荡 / `-5~-2` 弱势震荡 / `≤-6` 熊
- 每档对应战法推荐 / 禁止战法 / 总仓位上限 / 单票上限（spec §5 的表，原样实现）
- 8 个战法 S1–S8，名字和 ID 不要改

### 1.4 稳定性机制（spec §6，重点中的重点）

**3 日确认 + 缓冲区**（上下行不对称，用户明确要求）：

- **向更乐观档切换**：最近 3 日总分均 ≥ 新档位下限
- **向更悲观档切换**：最近 3 日总分均 ≤ 新档位上限 − 1（多 1 分缓冲，避免错过反弹）
- **允许一次跨档**：只在 3 日同时满足两档的悲观条件时

**单日剧变逃生门**（覆盖 3 日确认）：

- **下行逃生门（OR 逻辑，宽松）**：任一触发即降 1 档
  1. 总分相比上一日下降 ≥ 5
  2. HS300 **或** CSI1000 单日跌幅 ≥ 3% **且** 涨跌家数比 ≤ 0.25
  3. 情绪评分 ≤ 20 **或** 涨停差 ≤ −40
- **上行逃生门（AND 逻辑，严格）**：全部同时满足才升 1 档
  1. 总分相比上一日上升 ≥ 5
  2. HS300 **和** CSI1000 单日涨幅均 ≥ 2%
  3. 涨跌家数比 ≥ 0.80

**不对称的理由**（用户原话反复强调）："宁可踏空不可站岗"，2024-10-08 是前车之鉴。上行必须严格，震荡市假突破太多。

### 1.5 输出与下游契约（spec §7、§11）

- **三个输出**：`review-output/regime_YYYY-MM-DD.md`（人看）+ `regime_YYYY-MM-DD.json`（机器读）+ `memory/regime-log.md`（追加一行）
- **下游乘数叠加**：`confidence=low ×0.5 / medium ×0.8`、`switched ×0.8`、`emergency_switch ×0.7`，**可多重叠加**
- JSON 字段名固定（`regime_code`、`playbook.recommended`、`playbook.forbidden`、`playbook.position_limit.{total,single}`、`emergency_switch`、`emergency_reason`），**下游靠这个契约工作，改名要慎重**

---

## 2. 数据源要点与坑

### 2.1 daily_review.py 的真实位置

不在 `workspace/skills/scheduled/daily-review-data/`（那里只有 SKILL.md + skill.json）。实际 Python 代码在：

```
/home/rooot/.openclaw/workspace-bot11/scripts/review/
├── daily_review.py              # 编排器
├── markdown_renderer.py
├── mod_market_overview.py       # → "一、市场全景"
├── mod_sentiment.py             # → "二、情绪温度计"
├── mod_sector_rotation.py       # → "三、板块轮动"
├── mod_limit_up_tracking.py     # → "四、连板 & 题材前瞻"
├── mod_capital_flow.py          # → "五、资金与流动性"
├── mod_intraday_profile.py
├── mod_equity_risk_premium.py
└── mod_shareholder.py
```

- 输出文件：`复盘_YYYY-MM-DD.md`（`daily_review.py` line 136 附近）
- 典型输出在 `workspace-bot11/memory/posts/review-output/复盘_2026-03-20.md`（可作为 fixture 样本）
- 整个 `daily_review.py` 是 mod_xxx.py 子模块模式，regime 集成时最自然的方式是写一个 `mod_regime.py` 追加在编排器末尾

### 2.2 复盘 MD 的实际字段（从 2026-03-20 样本提取）

- **市场全景**：包含上涨家数、下跌家数 → 手工算涨跌家数比
- **情绪温度计**：含 `情绪评分 25 / 100`、`涨停:跌停 32:22`、`赚钱效应`、`上涨比例`
- **连板 & 题材前瞻**：含 `今日涨停：32 家`、`最高连板：0 板`
- **成交量**：MD 里有全市场成交额，但 **5/20 均量比** 可能需要从 akshare 补拉 HS300/CSI1000 成交量历史

**解析策略建议**：写一个宽松的 regex/line-scan 解析器，从复盘 MD 里尽量提取所有能直接拿到的字段，**缺什么再用 akshare 补**。不要假设 MD 结构固定，加健壮的 fallback。

### 2.3 akshare 注意事项

- 版本：1.18.40（已装）
- HS300: `stock_zh_index_daily(symbol="sh000300")` 或类似；CSI1000: `000852`
- 要拉至少 260 个交易日才能算 MA250
- **akshare 接口偶发挂掉**，必须有重试 + 降级。降级策略见 spec §8（缺失维度按 0 分计入，confidence 降级）
- 建议在 parser.py 里做一层缓存（本地 .parquet 或 json），避免每次跑都重拉 260 天

### 2.4 pytest 未装

`pytest` **目前不在系统 python3 里**。第一步需要：

```bash
pip3 install --user pytest
```

或者在脚本目录建一个 venv。用户偏好是系统级工具 + `--user` 安装，除非有特殊原因。

---

## 3. 任务分解（粗粒度）

下一个 session 应按以下顺序推进。每个阶段做完都要跑测试 + git commit。**不要并行所有阶段**。

### 阶段 A：骨架 + 依赖
1. 建目录 `workspace/skills/strategy/market-regime-classifier/{scripts,scripts/tests,references,memory}`
2. 写 `skill.json`（category=strategy，参考 spec §3）
3. 装 pytest，建 `conftest.py` 和 fixture 目录
4. 先跑空 test suite 确认环境

### 阶段 B：scoring.py（纯函数，最容易 TDD）
- 六个打分函数，每个输入原始值、输出 -2~+2 整数
- 表驱动测试，覆盖 5 个区间的边界值
- 合成函数 `total_score(dim_scores: dict) -> int`
- **坑**：指数 vs 均线要接受两个指数的打分并做四舍五入平均，signature 要从一开始就想清楚（避免后面重构）

### 阶段 C：parser.py
- `parse_daily_review(md_path) -> RawMarketData` — 从复盘 MD 抽 5 个维度
- `fetch_index_daily(symbol, n_days=260) -> DataFrame` — akshare 封装 + 缓存
- `compute_ma_scores(hs300, csi1000) -> int` — 拿价格算 MA5/20/60/250 位置，调用 scoring
- **坑**：MD 解析要容错（字段找不到就标 missing，不抛异常）；akshare 失败要触发降级而非崩溃
- Fixture：把 `workspace-bot11/memory/posts/review-output/复盘_2026-03-20.md` 复制一份到 `tests/fixtures/`

### 阶段 D：regime_rules.py（本 skill 最复杂的地方）
- `score_to_raw_regime(score: int) -> str` — 简单区间映射
- `apply_3day_confirmation(history: list[int], current_regime: str, new_candidate: str) -> (final_regime, switched: bool)` — 不对称 3 日确认 + 缓冲区
- `check_emergency_hatch(today_raw, yesterday_raw, today_score, yesterday_score) -> (triggered: bool, direction: str, reasons: list)` — 下行 OR / 上行 AND
- `lookup_playbook(regime) -> dict` — 从常量表返回战法+仓位
- **坑 1**：3 日确认需要读历史，历史存在 `memory/regime-log.md`，首次运行时没有历史，要有初始化逻辑
- **坑 2**：逃生门和 3 日确认的优先级——逃生门优先，触发后直接覆盖并重置 3 日窗口
- **坑 3**："跨档一次"的判定容易写错，多写几个 case 覆盖

### 阶段 E：output_writer.py
- `write_md(result, path)` / `write_json(result, path)` / `append_log(result, log_path)`
- MD 模板直接按 spec §7 的示例来，不要自由发挥
- JSON 字段名**严格按 spec §7 的示例**（`regime_code`/`playbook`/`emergency_switch` 这几个是下游契约）
- **坑**：`regime-log.md` 首次运行要有 header 行的处理

### 阶段 F：classify.py（CLI 编排器）
- 参数：`--date`、`--from-review`、`--format`（spec §9）
- 流程：parse → score → rules → write
- 集成测试：用 fixture MD 跑完整流程，断言输出的 JSON 结构
- 支持非交易日跳过（跟随 daily_review 的交易日检查逻辑——去看 `workspace-bot11/scripts/review/daily_review.py` 里怎么判的）

### 阶段 G：文档
- SKILL.md（触发词、用法、输出示例）
- `references/scoring.md`（打分表详细规则，从 spec §4 抽取）
- `references/playbooks.md`（8 战法简介，从 spec §5 抽取）
- `references/mapping.md`（regime → 战法映射表）
- `references/regime-examples.md`（**留空白骨架**，注明"待填充历史案例"，初始 2-3 个样例即可）

### 阶段 H：集成与历史回放
- 更新 `workspace/skills/CATALOG.md`，新增 "📊 策略 (Strategy)" 章节
- 在 `workspace-bot11/scripts/review/daily_review.py` 末尾追加调用 `classify.py`（或建 `mod_regime.py`）
- **历史回放**：手动跑 2024-09-24（急涨起点）、2024-10-08（急涨回落）、2025 春节前后，看逃生门是否识别对——**这一步不是单元测试，是 sanity check**，用户会要看结果

### 阶段 I：可选
- 为 bot7/bot8 建 symlink（spec §13 最后一条）
- `references/regime-examples.md` 填充真实案例

---

## 4. 坑与预警清单

### 4.1 数据源坑
- **炸板率不存在**：spec 已改成情绪评分，别再尝试从 MD 里找炸板率
- **daily_review MD 格式可能变**：不要硬编码具体字符串，用宽松的 regex，找不到就 missing
- **akshare 偶发挂**：必须降级，不能让 skill 崩溃
- **MA250 需要 260+ 交易日数据**：首次运行要预热，可能要花 30 秒拉数据

### 4.2 逻辑坑
- **3 日确认的初始化**：第一次运行没历史，默认给 "中性震荡"，并在日志里标 `bootstrap=true`
- **逃生门的 `emergency_switch` 只升/降 1 档**：下行允许连续两天各降一档，但单日不能跨档
- **`switched` 和 `emergency_switch` 的关系**：都为 True 时，下游乘数叠加（×0.8 × ×0.7 = ×0.56）
- **时区**：所有日期用本地时间（Asia/Shanghai），避免 UTC 转换出 off-by-one

### 4.3 用户偏好坑（从历史对话提取，重要）
- **用户不喜欢过度工程**：有现成能用的就别重新造轮子（akshare 够用就不要换 tushare）
- **用户会主动改 spec**：实现过程中如果发现规则有问题，**先停下来问用户**，不要自己偷偷改
- **TDD，但不是宗教**：纯函数层（scoring、rules）严格 TDD，parser 和 IO 层允许 "写完再补几个测试"
- **每阶段结束 commit**：commit 粒度按阶段来，message 用中文 + 简短说明
- **不要加用户没要求的 feature**：比如别自作主张加个 web dashboard、可视化图表、通知推送。spec 没写就不要做

### 4.4 环境坑
- **pytest 没装**，第一步就装
- **不要 `pkill`**：CLAUDE.md 里有铁律，任何杀进程操作必须用 `lsof -ti:端口 | xargs kill`，并且优先让用户自己操作
- **CLAUDE.md 定义的基础设施不能碰**：小红书 MCP、gateway、bot profile 都别动，本 skill 跟这些无关

---

## 5. 交接检查清单（新 session 开工前执行）

- [ ] 完整读一遍 spec（`docs/superpowers/specs/2026-04-13-market-regime-classifier-design.md`）
- [ ] 读一遍本 handoff
- [ ] 读一眼真实的复盘 MD 样本（`workspace-bot11/memory/posts/review-output/复盘_2026-03-20.md`）感受真实数据长什么样
- [ ] 扫一眼 `workspace-bot11/scripts/review/daily_review.py` 和 `mod_sentiment.py`，理解模块模式
- [ ] 装 pytest
- [ ] 跟用户确认："我打算先做阶段 A+B（骨架 + scoring），做完会回报"
- [ ] 然后按阶段 A → H 推进，每阶段 commit 一次

---

## 6. 不在本次交付范围

这些明确**不要做**（spec §12 + 对话中确认）：

- 回测框架
- 盘中 regime（日线级别已够）
- 板块/行业 regime（未来由 `sector-pulse` 另做）
- 跨市场（港股/美股）
- 下游 `short-term-sector-momentum` 策略 skill（本 skill 完成后再开工）
- 可视化/dashboard/通知

---

## 7. 完工标准

- [ ] `pytest workspace/skills/strategy/market-regime-classifier/scripts/tests/ -v` 全绿
- [ ] 手动跑 `python3 .../classify.py --date=2026-03-20` 能读真实复盘 MD 并输出 MD + JSON
- [ ] 输出的 JSON 能通过 `jq .playbook.position_limit` 解析出预期结构
- [ ] `regime-log.md` 追加了一行
- [ ] CATALOG.md 能看到新的 "📊 策略" 分类
- [ ] 用户跑了至少 1-2 个历史回放日期，认可 regime 判断合理
- [ ] 本 handoff 里的"用户偏好坑"没被踩

---

## 8. 相关文件索引

| 文件 | 作用 |
|---|---|
| [spec](../specs/2026-04-13-market-regime-classifier-design.md) | 最终设计规格，14 节 |
| [daily_review.py](../../../workspace-bot11/scripts/review/daily_review.py) | 复盘编排器，要在末尾追加 regime 调用 |
| [mod_sentiment.py](../../../workspace-bot11/scripts/review/mod_sentiment.py) | 情绪温度计模块，输出"情绪评分"字段的源头 |
| [复盘样本](../../../workspace-bot11/memory/posts/review-output/复盘_2026-03-20.md) | 真实 MD 样本，当 fixture 用 |
| [CATALOG.md](../../../workspace/skills/CATALOG.md) | skill 总索引，需要加 strategy 章节 |
| [CLAUDE.md](../../../CLAUDE.md) | 项目级铁律，注意不要碰基础设施 |

---

**最后一句话给下一个 session**：spec 是经过用户反复打磨的，每条规则都有理由。实现时如果遇到"这条规则好像没必要吧"或"我加个 feature 会更好"的念头，**先停下来问用户**。用户对这个项目投入了大量时间设计规则，希望实现忠实于 spec，而不是被"优化"。
