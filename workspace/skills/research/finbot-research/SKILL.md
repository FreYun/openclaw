---
name: finbot-research
description: FinBot Research — 个股深度研报 + 估值分析 + 催化剂雷达。方法论源自 FinRobot 8-Agent 股权研究框架，核心计算由 Python 脚本执行。A股/美股/港股通用。
---

# FinBot Research

三个子命令：

| 命令 | 用途 | 产出 |
|------|------|------|
| `/finbot-research deep <公司>` | 个股深度研报（7步完整流程） | 结构化研报 |
| `/finbot-research valuation <公司>` | 独立估值分析（三法+敏感性） | 估值表+矩阵 |
| `/finbot-research catalyst <公司>` | 催化剂雷达（新闻扫描+影响评分） | 催化剂报告 |

触发词：`/finbot-research`、"帮我做一份XX的研报"、"估值一下XX"、"XX有什么催化剂"

---

# 一、个股深度研报 `/finbot-research deep`

**确定：`TODAY`、公司名称、股票代码、市场（A/US/HK）。**

## Step 1 — 公司基本面建模

1. **商业模式拆解**：核心价值创造机制、客户分群、地理市场
2. **收入结构**：按业务线/产品拆分收入占比，识别增长引擎 vs 现金牛
3. **管理层画像**：CEO/CFO 背景、任期、战略方向

**工具**：
- **browser 搜索**（必须执行）：
  - `"{公司名} 商业模式 收入结构 {当前年}"` / `"{company} business model revenue breakdown"`
  - `"{公司名} 年报 投资者关系"` / `"{company} investor relations annual report"`
  - `"{公司名} CEO CFO 管理层 履历"` / `"{company} CEO CFO management team"`
- **A股补充**：`tushare_stock_basic(ts_code)` 获取上市基本信息
- **美股/港股补充**：browser → 公司官网 Investor Relations 页面；美股可查 SEC EDGAR，港股可查 HKEX 披露易

## Step 2 — 财务数据提取与预测

1. **拉取历史数据**（≥3年）：收入、EBITDA、毛利率、SG&A率、EPS、PE

   | 市场 | 工具 |
   |------|------|
   | A股 | `tushare_income` / `tushare_fina_indicator` / `tushare_daily_basic` |
   | 美股/港股 | browser → Yahoo Finance / Google Finance |

2. **调用脚本生成预测**：
   ```bash
   echo '{"historical": [
     {"metrics": "Revenue", "2022A": 394328000000, "2023A": 383285000000, "2024A": 385603000000},
     {"metrics": "EBITDA", "2022A": 130541000000, "2023A": 123000000000, "2024A": 131000000000},
     {"metrics": "EBITDA Margin", "2022A": "33.1%", "2023A": "32.1%", "2024A": "34.0%"},
     {"metrics": "Contribution Margin", "2022A": "43.3%", "2023A": "44.1%", "2024A": "45.5%"},
     {"metrics": "SG&A", "2022A": 25094000000, "2023A": 24932000000, "2024A": 26027000000},
     {"metrics": "SG&A Margin", "2022A": "6.4%", "2023A": "6.5%", "2024A": "6.7%"},
     {"metrics": "EPS", "2022A": 6.11, "2023A": 6.16, "2024A": 6.08},
     {"metrics": "PE Ratio", "2022A": 24.8, "2023A": 26.2, "2024A": 28.5}
   ], "config": {
     "revenue_base_year": "2024A",
     "revenue_growth_assumptions": {"2025E": 0.05, "2026E": 0.06, "2027E": 0.07},
     "margin_improvement": {"Contribution Margin": 0.005, "EBITDA Margin": 0.005},
     "sga_margin_change": -0.003
   }}' | python3 scripts/forecast.py
   ```
   - **增长假设必须基于 Step 1 的分析**，不可凭空编造

## Step 3 — 多方法估值

准备 EBITDA、股价、总股数、净负债、对标公司倍数、FCF，调用：

```bash
echo '{"financial_data": {
  "ebitda": 131000000000,
  "current_price": 173.5,
  "shares_outstanding": 15400000000,
  "net_debt": 50000000000,
  "free_cash_flow": 100000000000,
  "hist_ev_ebitda": [18.5, 20.1, 22.3, 19.8, 21.5]
}, "peer_data": {
  "MSFT": {"ev_ebitda": 25.3},
  "GOOGL": {"ev_ebitda": 18.7}
}, "assumptions": {
  "growth_rate_1_5": 0.08,
  "growth_rate_6_10": 0.04,
  "terminal_growth": 0.025,
  "wacc": 0.09
}}' | python3 scripts/valuation.py
```

**三种方法**：
- **EV/EBITDA 倍数法**（置信度70%）：历史均值 ± 1σ
- **对标估值法**（置信度60%）：2-3家同行倍数区间
- **DCF 折现法**（置信度50%）：10年FCF折现 + 终值，WACC ±1%敏感性
- **综合目标价** = Σ(目标价 × 置信度) / Σ(置信度)

详细方法论见 `valuation-methods.md`。

## Step 4 — 敏感性分析

用 Step 2 的预测数据：

```bash
echo '{"base_forecast": [<Step2 forecast输出>],
  "revenue_range": [-0.05, 0.05], "margin_range": [-0.02, 0.02], "steps": 5
}' | python3 scripts/sensitivity.py
```

输出：1D 收入/利润率敏感性 + **2D 交叉矩阵** + 90%/95%/99% 置信区间。
核心问题：**哪个假设对估值最敏感？**

## Step 5 — 风险评估（纯推理）

5 类风险系统扫描：

| 类别 | 关注点 |
|------|--------|
| ① 市场风险 | 需求变化、宏观逆风、行业颠覆 |
| ② 竞争风险 | 价格战、份额流失、技术过时 |
| ③ 运营风险 | 供应链中断、执行失败、关键人员 |
| ④ 财务风险 | 债务约束、现金流恶化、融资依赖 |
| ⑤ 监管/ESG | 政策变化、诉讼、环境责任 |

- 筛选 **Top 3-5**，评估对收入/利润/估值的影响 + 缓释措施
- browser 搜索补充：`"{公司名} 风险 诉讼 监管"`

## Step 6 — 竞争格局与护城河（纯推理）

1. **竞争地图**：2-3 个主要竞争对手 + 新兴威胁
2. **护城河判定**：网络效应 / 无形资产 / 成本优势 / 转换成本
3. **护城河趋势**：扩大 / 稳定 / 收窄
4. **财务对标**：与竞争对手 PE/PB/PS/ROE 对比

## Step 7 — 催化剂与新闻整合

1. browser 搜索近 30 天重大新闻，标注时效 🟢≤7天 / 🟡8-30天 / 🔴>30天
2. 调用脚本：
   ```bash
   echo '{"news_data": [
     {"title": "...", "text": "...", "publishedDate": "2026-03-25", "site": "Reuters"}
   ], "ticker": "NVDA", "company_name": "NVIDIA"}' | python3 scripts/catalyst.py
   ```
3. 综合判定投资论点状态：
   - ✅ **CONFIRMED** — 基本面稳固，催化剂正面
   - ✅ **论点成立** — 基本面稳固，催化剂正面
   - ⚠️ **待观察** — 存在不确定性
   - ❌ **论点破裂** — 核心假设被打破

## 图表生成（可选）

任何步骤完成后可生成 PNG 图表：
```bash
echo '{"chart_type": "<类型>", "data": {...}, "output_path": "/tmp/equity-charts/xxx.png", "ticker": "NVDA"}' | python3 scripts/charts.py
```

| chart_type | 用途 | 数据来自 |
|------------|------|---------|
| `revenue_ebitda` | 收入+EBITDA趋势（双轴柱线图） | forecast.py |
| `sensitivity` | 敏感性热力图 | sensitivity.py 的 combined_matrix |
| `peer_ev_ebitda` | 同行EV/EBITDA对比柱图 | 手动构建 |
| `football_field` | 估值区间足球场图 | valuation.py 的 football_field |

## 深度研报输出格式

```
# {公司名称} 股权研究报告
📅 {TODAY} | 数据截至 {最新财报期}

## 投资结论
- 论点状态：✅ 论点成立 / ⚠️ 待观察 / ❌ 论点破裂
- 目标价：¥/$ X（当前 ¥/$ Y，上行空间 Z%）
- 估值区间：¥/$ Low — ¥/$ High
- 核心逻辑（3句话）

## 公司概览（300-400字）
## 财务分析（历史表 + 预测表 + CAGR）
## 估值分析（三法对比 + 敏感性矩阵）
## 风险因素（Top 5，按类别）
## 竞争格局（护城河评估 + 对标表）
## 催化剂（Top 5 + 影响评分）
## 关键指标洞察
  每个维度回答 WHY → WHAT → SO WHAT：
  1. 收入增长  2. 毛利率  3. SG&A率  4. EBITDA利润率
## 数据来源（每项标注来源 + 🟢/🟡/🔴 时效）
```

---

# 二、独立估值 `/finbot-research valuation`

当只需要估值结论（不需要完整研报）时使用。

### Step 1 — 数据准备

拉取：最新 EBITDA、当前股价、总股数、净负债（可选）、FCF（可选）、历史 EV/EBITDA、对标公司倍数。

若净负债/FCF 不可得，脚本使用默认假设（净负债=EV×10%，FCF=EBITDA×60%）。

### Step 2 — 三法估值

```bash
echo '{"financial_data": {...}, "peer_data": {...}, "assumptions": {...}}' | python3 scripts/valuation.py
```

### Step 3 — 敏感性分析（可选，需有预测数据）

```bash
echo '{"base_forecast": [...], "revenue_range": [-0.05,0.05], "margin_range": [-0.02,0.02]}' | python3 scripts/sensitivity.py
```

### Step 4 — 输出

```
## {公司} 估值分析 | {TODAY}

| 方法 | 目标价 | 区间 | 置信度 |
|------|--------|------|--------|
| EV/EBITDA | ¥/$ XX | XX-XX | 70% |
| 对标估值 | ¥/$ XX | XX-XX | 60% |
| DCF | ¥/$ XX | XX-XX | 50% |
| **综合** | **¥/$ XX** | **XX-XX** | — |

当前价 ¥/$ YY → 上行空间 Z%

### 敏感性矩阵（如有）
### 关键假设

数据来源：[来源 + 🟢/🟡/🔴]
```

---

# 三、催化剂雷达 `/finbot-research catalyst`

快速扫描近期新闻，识别催化事件并量化影响。

### Step 1 — 新闻收集

使用 **browser 工具**搜索至少 3 条查询（A股优先证券时报、财联社、东方财富；美股/港股优先 Reuters、Bloomberg、CNBC）：
1. `"{公司名} 最新消息"` / `"{company} latest news"`
2. `"{公司名} 分析师评级"` / `"{ticker} analyst rating"`
3. `"{公司名} 政策 监管"` / `"{company} regulatory"`
4. `"{公司名} 业绩指引"` / `"{ticker} earnings guidance"`（可选）

每条新闻标注时效：🟢≤7天 / 🟡8-30天 / 🔴>30天
收集到的新闻标题、摘要、发布日期、来源网站作为 `news_data` 传入 Step 2 脚本。

### Step 2 — 分析

```bash
echo '{"news_data": [...], "ticker": "...", "company_name": "..."}' | python3 scripts/catalyst.py
```

**6 类事件分类**：产品发布 / 财报指引 / 监管法律 / 并购合作 / 管理层变动 / 市场格局

**情绪判定优先级**：
1. 分析师动作（升降级、目标价调整）— 最高优先
2. 关键词匹配（中英文双语）

**影响评估**：加权分数 = 影响等级(1-3) × 概率 × 情绪方向(+1/-1/0)

### Step 3 — 输出

```
## {公司} 催化剂雷达 | {TODAY}

### 正面催化剂（上行潜力）
1. **[类型]**（日期 🟢）: 描述
   影响:高 | 概率:X% | 评分:+X.XX

### 风险催化剂（下行风险）
1. **[类型]**（日期 🟡）: 描述
   影响:高 | 概率:X% | 评分:-X.XX

### 待观察事件
1. 描述（日期）

### 投资论点状态
✅ 论点成立 / ⚠️ 待观察 / ❌ 论点破裂
**理由**：...
```

---

# 注意事项

- **增长假设有据可依**：预测必须基于商业模式分析，不可凭空编造
- **估值是区间不是点**：永远给范围，不给单一数字
- **风险不能为空**：即使最好的公司也至少列 3 条
- **时效标注**：所有数据标注来源和 🟢/🟡/🔴
- **论点必须表态**：论点成立 / 待观察 / 论点破裂，不可模棱两可
- **脚本路径**：scripts/ 下的 Python 脚本通过 `echo 'JSON' | python3 scripts/xxx.py` 调用，路径相对于本 SKILL.md 所在目录
- **脚本工作目录**：调用任何脚本前须先 `cd` 到本 SKILL.md 所在目录（skill 根目录），例如：`cd /path/to/finbot-research && echo '{...}' | python3 scripts/valuation.py`
- **脚本失败降级**：若 Python 脚本执行失败（依赖缺失、JSON 格式错误等），按以下顺序处理：
  1. 检查错误信息，修正 JSON 输入格式后重试一次
  2. 若仍失败，跳过该脚本，改为**手动推理**完成对应步骤，并在输出中注明"⚠️ 脚本未执行，以下为手动估算"
  3. 不可因脚本失败而中止整个研报/估值流程

# 配套技能

| 技能 | 何时调用 |
|------|---------|
| `/sector-pulse` | 需要行业级分析而非个股时 |
| `/research-stock` | 只需快速数据查询时 |
| `/technical-analyst` | 需要技术面分析配合时 |
| `/market-environment-analysis` | 需要宏观环境评估时 |
- **论点必须表态**：论点成立 / 待观察 / 论点破裂，不可模棱两可
