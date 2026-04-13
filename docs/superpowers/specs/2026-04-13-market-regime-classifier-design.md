# Market Regime Classifier — 设计规格

**创建日期**：2026-04-13
**Skill 路径**：`workspace/skills/strategy/market-regime-classifier/`
**Skill 分类**：`strategy`（新建 slot）
**作者**：guyunfeng + Claude

---

## 1. 目标与定位

构建一个**通用市场判断器** skill，让任何 bot 在做交易决策前都能先问一句"现在是什么市场？该用什么战法？不该用什么战法？"。

这个 skill 的设计目标是：

- **可解释**：打分规则公开透明，不是黑盒模型
- **稳定**：不会每天在相邻档位间反复横跳
- **实用**：输出直接对应到具体战法推荐和仓位上限，bot 拿到就能用
- **可复用**：是通用底层能力，未来所有策略类 skill（超短、波段、长线）都可以调用它作为 step 0

**范围边界**：这个 skill 只负责判断和推荐，**不负责执行**。具体每种战法的进场/止损/出场规则在下游 strategy skill 里实现。本 skill 对下游提供 JSON 接口，对用户提供 MD 可读输出。

---

## 2. 架构总览

```
                 ┌─────────────────────────┐
                 │  daily_review.py        │
                 │  （已存在，收盘后自动跑）  │
                 │  输出: 复盘_YYYY-MM-DD.md │
                 └───────────┬─────────────┘
                             │
                             ▼ parse
                 ┌─────────────────────────┐
                 │  market-regime-         │
                 │  classifier (本 skill)  │
                 │                         │
                 │  1. 读取 6 维原始数据    │
                 │  2. 六维打分             │
                 │  3. 3 日确认 + 缓冲区    │
                 │  4. 映射 regime + 战法   │
                 └───────────┬─────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
      regime_YYYY-MM-DD  regime_YYYY-MM   regime-log.md
      .md (人看)         -DD.json (机器)  （追加一行摘要）
                             │
                             ▼ (未来)
                 ┌─────────────────────────┐
                 │  short-term-sector-      │
                 │  momentum (下游策略 skill)│
                 │                         │
                 │  step 0: 读 regime JSON │
                 │  step 1: 按 regime 选战法│
                 │  ...                     │
                 └─────────────────────────┘
```

---

## 3. 目录结构

```
workspace/skills/strategy/market-regime-classifier/
├── SKILL.md                 # 主文件：触发、用法、输出格式示例
├── skill.json               # meta（name/description/category=strategy）
├── references/
│   ├── scoring.md           # 六维打分表详细规则、阈值、计算公式
│   ├── playbooks.md         # 8 个战法的 2-3 句简介 + 下游 skill 指针
│   ├── mapping.md           # regime → 战法推荐/禁止/仓位上限 映射表
│   └── regime-examples.md   # 历史案例库（逐步积累，初始可放 2-3 个样例）
└── scripts/
    ├── classify.py          # 主脚本：parse → 打分 → 映射 → 输出
    └── tests/
        └── test_classify.py # 单元测试（六维打分函数、映射函数、降级逻辑）
```

同时在 `workspace/skills/CATALOG.md` 里新增 **"📊 策略 (Strategy)"** 分类章节。

---

## 4. 六维打分规则

**打分维度与阈值**：

| 维度 | +2 | +1 | 0 | -1 | -2 | 数据字段 |
|------|----|----|----|----|----|----|
| **指数 vs 均线** | 站上 5/20/60/250，MA 多头排列 | 站上 5/20/60 | 站上 20，60 不定 | 跌破 20 | MA 空头排列 | 沪深300 + 中证1000 均值 |
| **涨跌家数比** | >0.75 | 0.60-0.75 | 0.40-0.60 | 0.25-0.40 | <0.25 | 市场全景.上涨家数 / 总家数 |
| **情绪（涨停−跌停）** | >80 | 40-80 | 10-40 | −40-10 | <−40 | 情绪温度计.涨停数 − 跌停数 |
| **炸板率** | <10% | 10-20% | 20-30% | 30-40% | >40% | 情绪温度计.炸板率 |
| **最高连板高度** | ≥5 板 | 4 板 | 3 板 | 2 板 | ≤1 板 | 连板前瞻.最高连板 |
| **成交量趋势** | >1.30 | 1.10-1.30 | 0.90-1.10 | 0.70-0.90 | <0.70 | 5 日均量 / 20 日均量 |

**总分范围**：−12 到 +12。各维度权重相等（每维 −2 到 +2）。

**指数选择**："指数 vs 均线" 维度取**沪深300 + 中证1000**，兼顾大盘与中小盘。两指数分别按上表打分后取算术平均，结果四舍五入到最近的整数（例如沪深300 +2、中证1000 +1，平均 1.5，四舍五入为 +2）。

**均线位置判定**：取指数当日收盘价 vs 5/20/60/250 日简单移动平均线的相对位置。"MA 多头排列"定义为 MA5 > MA20 > MA60 > MA250；"MA 空头排列"定义为 MA5 < MA20 < MA60 < MA250。

---

## 5. Regime 映射

**分数 → Regime**：

| 分数区间 | Regime | 含义 |
|---|---|---|
| ≥ +7 | **强牛** | 指数趋势上行 + 情绪高涨 + 放量 |
| +2 ~ +6 | **强势震荡** | 箱体内偏上，情绪积极 |
| −1 ~ +1 | **中性震荡** | 无方向，分化明显 |
| −5 ~ −2 | **弱势震荡** | 箱体内偏下，资金退潮 |
| ≤ −6 | **熊** | 趋势下行 + 情绪低迷 + 缩量 |

**Regime → 战法映射**：

| Regime | 建议战法（优先级） | 禁止战法 | 总仓位上限 | 单票上限 |
|---|---|---|---|---|
| **强牛** | S1 突破 → S2 龙头板 → S6 趋势持有 | S8 空仓、S7 超跌反弹 | 90% | 30% |
| **强势震荡** | S4 回踩 → S5 龙回头 → S3 首板 | S1 突破、S7 超跌反弹 | 70% | 25% |
| **中性震荡** | S5 龙回头 → S4 回踩（严选） | S1 突破、S2 龙头板、S6 趋势持有 | 50% | 20% |
| **弱势震荡** | S5 龙回头（试错） | S1、S2、S3、S6 全部禁用 | 30% | 15% |
| **熊** | S8 空仓 → S7 超跌反弹（1-2 成仓一日游） | S1、S2、S3、S4、S6 全部禁用 | 20% | 10% |

**战法清单（8 个）**：

| ID | 战法名 | 一句话描述 |
|---|---|---|
| S1 | 突破战法 | 强势股横盘平台放量突破，进场买突破位 |
| S2 | 龙头板接力 | 盯高度板（3 板+）梯队龙头，次日竞价接力 |
| S3 | 首板接力 | 当日领涨板块首板，次日竞价低开进 |
| S4 | 回踩战法 | 强势股回踩 5/10 日线不破，次日进 |
| S5 | 龙回头 | 前期龙头冷却后二次放量反包 |
| S6 | 趋势持有 | 指数强势 + 龙头股持仓 5-10 天 |
| S7 | 超跌反弹 | 连续大跌后的技术性反弹，一日游 |
| S8 | 空仓观望 | 不开新仓，只处理已有持仓 |

**下游 skill 绑定**：当前 `short-term-sector-momentum`（未建）负责实现 S3、S4、S5 三个战法。其它战法暂无对应下游 skill，推荐时仅输出战法名和简介，执行由 bot 自己判断或未来补建 skill。

---

## 6. 稳定性机制

**切换规则**（统一描述 3 日确认 + 缓冲区）：

Regime 的切换判定基于最近 **3 个交易日（含今日）** 的总分。维持当前 regime 是默认行为，只有满足以下条件才切换：

- **向更乐观方向切换**（如中性震荡 → 强势震荡）：最近 3 日总分均 **≥ 新档位下限**。例如切到"强势震荡"（区间 +2~+6），需要 3 日得分都 ≥ +2。
- **向更悲观方向切换**（如中性震荡 → 弱势震荡）：最近 3 日总分均 **≤ 新档位上限 − 1**（多 1 分缓冲）。例如切到"弱势震荡"（区间 −5~−2），需要 3 日得分都 ≤ −3。缓冲的目的是避免市场刚变冷就切悲观档，错过反弹。
- **跨档切换**（如强势震荡 → 弱势震荡，跨过中性）：仍按相邻规则逐档判断，若 3 日同时满足两档的悲观条件，允许一次跨档。

**切换示例**：

- 昨天是"中性震荡"（得分 0），今天得分跳到 +3（落在"强势震荡"区间）
- 只有 1 天符合新 regime，**当日输出仍为"中性震荡"**，同时在 `switch_warning` 中标注"今日得分 +3 已进入强势震荡区间，若持续 2 天将切换"
- 第 2、3 天如果仍 ≥ +2，正式切换为"强势震荡"

**日志追踪**：

每次 skill 运行追加一行到 `workspace/skills/strategy/market-regime-classifier/memory/regime-log.md`，格式：

```
| 日期 | 6维原始值 | 6维得分 | 总分 | 当日 regime | 是否切换 |
|---|---|---|---|---|---|
| 2026-04-13 | MA:+1, 涨跌:0.55, 情绪:25, 炸板:18%, 连板:3, 量比:1.05 | 1,0,1,1,0,0 | +3 | 中性震荡 | - |
```

便于事后回溯和校准阈值。

---

## 7. 输入与输出

### 输入

**主输入**：`daily_review.py` 的输出 MD 文件路径（默认 `review-output/复盘_YYYY-MM-DD.md`）

**辅助输入**：
- 沪深300、中证1000 的日线数据（通过 akshare 实时取，用于 MA 计算，daily_review 未覆盖这部分）
- 历史 regime-log.md（用于 3 日确认判断）

### 输出

**MD 文件**：`review-output/regime_YYYY-MM-DD.md`

结构：

```markdown
# 市场 Regime 判断 — 2026-04-13

## 结论

- **当前 regime**：中性震荡 🟡
- **总分**：+3 / 12（处于 −1 ~ +1 区间之外但未满 3 日确认，维持上一档）
- **切换警戒**：今日已进入"强势震荡"区间，若持续 2 天将切换
- **建议战法**：S5 龙回头 → S4 回踩（严选）
- **禁止战法**：S1 突破、S2 龙头板、S6 趋势持有
- **仓位上限**：总 50% / 单票 20%

## 六维打分明细

| 维度 | 原始值 | 得分 | 说明 |
|---|---|---|---|
| 指数 vs 均线 | 沪深300 站 20 均线，中证1000 跌破 | +1 | 大盘强中小盘弱 |
| ... | | | |

## 战法推荐详情

**S5 龙回头**（优先级 1）
- 适用原因：震荡市板块快速轮动，老龙头冷却后二次放量概率高
- 核心买点：前期领涨板块断板后 3-10 天，当天重新放量且主力资金净流入
- 详细执行：见 `skills/strategy/short-term-sector-momentum/`（如已构建）

**S4 回踩战法**（优先级 2，严选模式）
...

## 禁止战法原因

**S1 突破**：震荡市箱体顶放量是出货信号，假突破远多于真突破
...

## 数据可信度

✅ 所有 6 维数据完整
```

**JSON 文件**：`review-output/regime_YYYY-MM-DD.json`

```json
{
  "date": "2026-04-13",
  "regime": "中性震荡",
  "regime_code": "NEUTRAL_RANGE",
  "score": {
    "total": 3,
    "breakdown": {
      "ma_position": 1,
      "advance_decline": 0,
      "sentiment": 1,
      "fail_rate": 1,
      "streak_height": 0,
      "volume_trend": 0
    }
  },
  "raw_data": {
    "ma_position": {"hs300": "above_20", "csi1000": "below_20"},
    "advance_decline_ratio": 0.55,
    "sentiment_delta": 25,
    "fail_rate": 0.18,
    "max_streak": 3,
    "volume_ratio_5_20": 1.05
  },
  "confidence": "high",
  "missing_dims": [],
  "switch_warning": "今日得分已进入强势震荡区间，若持续 2 天将切换",
  "playbook": {
    "recommended": [
      {"id": "S5", "name": "龙回头", "priority": 1},
      {"id": "S4", "name": "回踩战法", "priority": 2, "mode": "strict"}
    ],
    "forbidden": ["S1", "S2", "S6"],
    "position_limit": {"total": 0.50, "single": 0.20}
  },
  "last_regime": "中性震荡",
  "switched": false
}
```

**日志文件**：`workspace/skills/strategy/market-regime-classifier/memory/regime-log.md`（追加一行）

---

## 8. 降级策略（数据缺失）

采用**降级打分 + 标注模式**：

- 某维度数据缺失 → 该维度得分按 **0（中性）** 计入总分
- JSON 输出中 `missing_dims` 字段列出缺失维度
- JSON 的 `confidence` 字段根据缺失维度数降级：
  - 0 维缺失：`high`
  - 1-2 维缺失：`medium`
  - ≥3 维缺失：`low`（并在 MD 输出中显著标红提示用户手动确认）
- 不中断流程，始终输出结论

---

## 9. 触发方式

**自动模式**：作为 `daily_review.py` 的最后一个模块被调用

- 修改 `daily_review.py`，在所有现有模块跑完后追加一次 `classify.py --from-review=<review_md_path>`
- 非交易日自动跳过（跟随 daily_review 的交易日检查）

**手动模式**：

```bash
# 跑今天
python3 workspace/skills/strategy/market-regime-classifier/scripts/classify.py

# 跑指定日期
python3 .../classify.py --date=2026-04-13

# 指定 review MD 路径
python3 .../classify.py --from-review=review-output/复盘_2026-04-13.md

# 只输出 JSON
python3 .../classify.py --format=json
```

手动模式典型场景：盘中出现异动（如午后突发大跌），用户想立即重算一次。此时应允许手动触发即使当前不是收盘时间。

---

## 10. 测试策略

**单元测试** (`scripts/tests/test_classify.py`)：

1. **打分函数测试**：每个维度的打分函数单独测试，覆盖 5 个区间的边界值
2. **映射函数测试**：5 个分数区间 → 5 个 regime，每个区间取典型值验证
3. **3 日确认逻辑测试**：构造 mock regime-log，验证"连续 3 日"判断和"缓冲区"判断
4. **降级逻辑测试**：缺失 1/2/3 维数据时的 confidence 降级
5. **Regime 切换测试**：昨日 A → 今日打分进入 B 区间 → 3 日后切换 B 的完整路径

**历史回放验证**（集成测试）：

拿 2024 年 9 月 24 日（急涨起点）、2024 年 10 月 8 日（急涨回落）、2025 年春节前后几个典型行情日作为 ground truth，手工标注 regime，然后跑脚本看是否能识别正确。初始放 3-5 个样例到 `references/regime-examples.md`，后续逐步积累。

**不做回测**：本 skill 不涉及具体交易决策，不需要回测框架。回测留给下游 strategy skill。

---

## 11. 下游约定（为超短策略 skill 预留的接口）

未来的 `short-term-sector-momentum` skill 启动时应：

1. 调用 `regime-classifier` 并读取最新的 `regime_YYYY-MM-DD.json`
2. 根据 `playbook.recommended` 决定今日执行哪种战法（S3/S4/S5）
3. 根据 `playbook.forbidden` 决定禁用的战法（即使策略本身实现了也不执行）
4. 根据 `playbook.position_limit` 决定总仓位和单票上限
5. 如果 `confidence == "low"`，将 `position_limit.total` 再乘 0.5 使用；`confidence == "medium"` 乘 0.8
6. 如果 `switched == true`（regime 切换日），`position_limit.total` 再乘 0.8 使用（切换首日保守）

---

## 12. 风险与限制

**已知限制**：

1. **A 股 regime 不存在完美分类**：5 档只是工程近似，边界模糊时（比如总分 ±1.5 左右）判断意义下降，用户应结合 `confidence` 和 `switch_warning` 自己综合判断
2. **3 日确认会滞后**：急转行情（如 2024-09-24）会在前 2 天仍输出旧 regime。这是为稳定性主动付出的代价。如果需要更灵敏，可以后续加"急变模式"：单日总分变化 ≥ 5 时立即强制切换
3. **指数选择偏中小盘**：中证1000 权重 50% 导致 regime 偏向题材股活跃度。做大盘蓝筹策略的 bot 调用时需注意这一点
4. **阈值需要校准**：初始阈值是根据经验设定，上线后应每月看 `regime-log.md` 校准一次，尤其是"炸板率"和"连板高度"两个维度（A 股情绪波动大）

**不处理的场景**：

- 盘中 regime（只做日线级别，不做分时切换判断）
- 行业/板块级别的 regime（只做大盘整体判断，板块判断由 `sector-pulse` 负责）
- 跨市场判断（只做 A 股，不涉及港股/美股）

---

## 13. 交付清单

本 skill 交付需要的文件：

- [ ] `workspace/skills/strategy/market-regime-classifier/SKILL.md`
- [ ] `workspace/skills/strategy/market-regime-classifier/skill.json`
- [ ] `workspace/skills/strategy/market-regime-classifier/references/scoring.md`
- [ ] `workspace/skills/strategy/market-regime-classifier/references/playbooks.md`
- [ ] `workspace/skills/strategy/market-regime-classifier/references/mapping.md`
- [ ] `workspace/skills/strategy/market-regime-classifier/references/regime-examples.md`（含 3-5 个历史案例）
- [ ] `workspace/skills/strategy/market-regime-classifier/scripts/classify.py`
- [ ] `workspace/skills/strategy/market-regime-classifier/scripts/tests/test_classify.py`
- [ ] `workspace/skills/strategy/market-regime-classifier/memory/regime-log.md`（空文件，首次运行创建）
- [ ] 修改 `workspace/skills/CATALOG.md`：新增 "📊 策略 (Strategy)" 分类章节
- [ ] 修改 `workspace/skills/scheduled/daily-review-data/` 的 `daily_review.py`：追加 regime 计算步骤
- [ ] （可选）为需要的 bot（bot7 / bot8 / 未来的策略 bot）创建 symlink：`workspace-botN/skills/market-regime-classifier → ../../workspace/skills/strategy/market-regime-classifier`

---

## 14. 下一步

本设计通过后，进入 `writing-plans` 阶段，将上述 14 节内容拆成可执行的实施计划（按 scripts/classify.py 主逻辑 → 子维度打分 → 映射层 → 输出层 → daily_review 集成 → 测试的顺序分阶段实现）。
