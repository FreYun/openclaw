# TMT Research Methodology

> **References** (read on demand, not at startup):
> - `methodology/frameworks.md` — S-curve, value chain, expectations gap, catalyst calendar, valuation
> - `methodology/views-and-risks.md` — view formation (3-scenario + conviction), 7 TMT risk types
> - `methodology/tools.md` — MCP tool reference, Tushare/Gateway call examples, code formats, URLs

---

## Scenario Router

### A. Daily Market Review

Trigger: "看看美股昨晚情况", "盘面怎么看", "复盘"

1. **Index scan** → `market_snapshot` (gateway) or `/market-environment-analysis`
2. **Hot stocks** → browser xueqiu.com/search + `search_news` (gateway)
3. **News attribution** → browser + `/news-factcheck` if dubious
4. **Causal chain** → News→Company→Sector→A-share transmission (**core reasoning step**)
5. **A-share mapping** → `tushare_daily_basic(ts_code, trade_date)` + browser xueqiu
6. **Forward view** → 3-scenario (see `methodology/views-and-risks.md`)
7. **Record** → `/record` → `memory/views/`

Output rule: must have directional call + causal chain.

### B. Deep Sector Research

Trigger: "深挖存储芯片", "机器人产业链", "AI算力什么阶段"

1. **History check** → `qmd search "{sector}"`, incremental if exists
2. **S-curve positioning** → which stage? (see `methodology/frameworks.md`)
3. **Value chain mapping** → browser eastmoney reports + xueqiu + `search_report` (gateway)
4. **Data pull** → `tushare_fina_indicator` + `tushare_daily_basic` + `tushare_income` for leaders
5. **Expectations gap** → consensus vs my data (see frameworks.md)
6. **Capital flow** → `tushare_moneyflow_hsgt` + `tushare_hsgt_top10`
7. **Full workflow** → `/sector-pulse`
8. **Record** → `/record` → `research/` + `views/` + `predictions/`

Rule: must visit eastmoney reports + xueqiu discussions.

### C. Event-Driven Analysis

Trigger: "GTC怎么看", "XX财报炸了", "出口管制新政"

1. **Classify** → product launch / policy / earnings / geopolitical
2. **1st-order impact** → direct beneficiaries → browser + `search_news` + `/news-factcheck`
3. **2nd-order impact** → supply chain transmission (see frameworks.md) — **your edge**
4. **Pricing speed** → already priced in? → `tushare_daily` + `stock_research` (gateway)
5. **Decay** → impact typically fades after 3 trading days
6. **Record** → `/record` → `research/`

### D. Quick Stock Scan

Trigger: "快看一下寒武纪"

1. **Snapshot** → `stock_research` (gateway) or `tushare_daily_basic` + `tushare_fina_indicator`
2. **Valuation anchor** → PE/PS percentile vs history & peers
3. **Catalyst** → browser xueqiu stock page
4. **Risk in one line** → (see `methodology/views-and-risks.md`)

Verbal report. `/stock-watcher add` if worth tracking.

### E. View Maintenance

Trigger: heartbeat / new data / research dept asks

1. **Falsification check** → compare `memory/views/` conditions vs `tushare_daily_basic`/`tushare_fina_indicator`
2. **Decision**: hold if assumptions intact; flag if single anomaly; **update immediately** if falsified; **notify research dept** if direction reversal
3. **Prediction tracking** → `memory/predictions/tracker.md`

---

## Scenario→Tool Quick Map

| Scenario | MCP Tools | Browser | Memory |
|----------|-----------|---------|--------|
| Daily review | `market_snapshot`, `search_news`, `tushare_daily_basic` | xueqiu + 10jqka | → views/ |
| Sector deep | `tushare_fina_indicator`, `tushare_income`, `tushare_moneyflow_hsgt`, `search_report` | eastmoney + xueqiu | → research/ + views/ |
| Event | `search_news`, `tushare_daily`, `stock_research` | event source + xueqiu | → research/ |
| Stock scan | `stock_research` or `tushare_daily_basic` + `tushare_fina_indicator` | xueqiu stock page | → stock-watcher |
| View maint | `tushare_daily_basic`, `tushare_fina_indicator` | — | → views/ |

**Escalate to research dept**: view reversal, first-time sector coverage, unresolvable data conflict.

---

## Output Quality Checklist

- [ ] Clear directional call (not "opportunities and risks coexist")
- [ ] Key data sourced + timestamped (🟢🟡🔴)
- [ ] Expectations gap articulated (consensus vs my view)
- [ ] Falsification conditions written (specific, observable)
- [ ] ≥2 relevant risks mentioned
- [ ] Historical view consistency checked (`qmd search`)
- [ ] Logic self-check passed (growth/margin/valuation triangle consistent)
- [ ] Cross-validated (≥2 independent sources)
