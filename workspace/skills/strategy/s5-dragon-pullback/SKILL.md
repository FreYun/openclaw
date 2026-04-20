---
name: s5-dragon-pullback
description: S5 龙回头战法 — 前期龙头股 (近 30 日 ≥2 连板) 冷却 2-7 天后, T 日大阳反包 + 收复 T-1 高, T+1 集合竞价进。仅在 STRONG/NEUTRAL/WEAK 震荡档激活, BEAR/STRONG_BULL 自动跳过。
---

# S5 龙回头战法

**代码**: `/home/rooot/.openclaw/scripts/s5/` (本 skill 目录只住说明 + 规则文档)

**信号定义**:
```
龙头 (近 30 日 ≥2 连板) → 冷却 (2-7 交易日, 跌幅 ≥5%) → T 日反包 (涨 ≥7% 且收盘 ≥ T-1 高)
```
完整规则见 [references/strategy.md](references/strategy.md)。

---

## 触发条件

- T 日收盘后 (~16:00), cron `daily-regime-pipeline.sh` 已跑完 (regime + cache 都进 market.db)
- 用户说"今天有没有龙回头""跑一下 S5""有什么候选标的"
- T+1 开盘 5-10 分钟, 用户说"S5 验证一下""今天能不能买"
- regime ∈ `{STRONG_RANGE, NEUTRAL_RANGE, WEAK_RANGE}`; 其它档直接跳过

---

## 命令

```bash
cd /home/rooot/.openclaw/scripts/s5

# T 日收盘后选股
python3 select.py --date=2026-04-16

# T+1 开盘 5-10 分钟验证
python3 verify.py --date=2026-04-17 --candidates-json=/path/to/candidates_2026-04-16.json

# 从 DB 重渲染已有日期 (不重新计算)
python3 render.py candidates --date=2026-04-16
python3 render.py verification --date=2026-04-17
python3 render.py list                                  # 列出所有日期

# 批量回测
python3 backtest.py --start=2026-03-12 --end=2026-04-16 --output-dir=/tmp/s5-backtest
```

### 输出模式 (`S5_OUTPUT` 环境变量)

```
S5_OUTPUT=both   默认: 文件 + DB 都写
S5_OUTPUT=file   只写 candidates_*.md / .json
S5_OUTPUT=db     只写 market.db 的 s5_* 表, 用 render.py 按需渲 MD
```

### 历史日期回测

`select.py --date=YYYY-MM-DD` 需要 `market.db` 里有该日的 `s5_daily_universe` 和 `klines_cache`。cron 跑过的日期自动有;没跑过的 (例如回测 2024 年) 先手动 prewarm:

```bash
python3 /home/rooot/.openclaw/scripts/s5-prewarm.py --date=2024-01-15
```

---

## 输出契约

### `candidates_YYYY-MM-DD.json` (成功)

```json
{
  "date": "2026-04-16", "strategy": "S5",
  "regime_input": {"code": "STRONG_RANGE", "score": 10, "confidence": "high",
                   "switched": false, "emergency_switch": false,
                   "position_limit_single_base": 0.25},
  "candidates": [
    {"code": "603933", "name": "睿能科技", "industry": "其他电子",
     "dragon_peak": {"date": "...", "close": ..., "max_streak": 2},
     "cooldown":    {"days": ..., "drop_pct": -..., "t1_close": ...},
     "rebound":     {"t_pct": 10.01, "t_close": ..., "t1_high": ...},
     "entry":       {"zone_low": ..., "zone_high": ..., "rule": "T 日收盘 ±1%"},
     "stop_loss":   {"price": ..., "rule": "T 日最低"},
     "target_1":    {"price": ..., "pct": 5.0},
     "target_2":    {"price": ..., "pct": 10.0},
     "position_pct": 0.25, "position_calc": "0.25 (base) = 0.2500"}
  ],
  "stats": {"universe_size": 413, "dragon_pool_size": 21, "passed_count": 2,
            "hot_industries": ["电池", "IT服务Ⅱ", "环境治理"]}
}
```

### 跳过 (regime 不匹配)

```json
{"date": "2026-04-17", "strategy": "S5", "candidates": [],
 "skipped_reason": "regime=熊, S5 not in playbook.recommended (['S8', 'S7'])",
 "stats": null}
```

### 仓位乘数链

```
base = regime.playbook.position_limit.single          (来自 market-regime 的 mapping)
× 0.5 (confidence=low)  或  × 0.8 (medium)
× 0.8 (switched)
× 0.7 (emergency_switch)
= final position_pct
```

调参/变更规则见 [references/signal-tuning.md](references/signal-tuning.md)。

---

## T+1 验证状态

| status | 判定 | 操作 |
|---|---|---|
| `triggered` | 开盘价 ∈ entry_zone | ✅ 按计划买 |
| `triggered_late` | 盘中回到 entry_zone | ✅ 回补 |
| `gap_up_skip` | 开盘 > entry_zone_high | ⚠️ 放弃不追 |
| `stop_hit` | 当前价 ≤ stop_loss | ❌ 止损破, 弃 |
| `wait` | 盘中未进入 entry_zone | ⏳ 等 |

backtest 模式下还有: `triggered_at_open / triggered_intraday / hit_target_1 / hit_target_2 / close_hold / no_data`。

---

## 数据流 (所有数据在 market.db, cron 写, S5 读)

```
cron 16:00 daily-regime-pipeline.sh
├── regime_classify_daily       ← replay.py (市场 regime)
├── limit_up_pool               ← s5-prewarm.py (akshare 涨停池)
├── hot_industries_daily        ← s5-prewarm.py (从涨停池派生)
├── s5_daily_universe           ← s5-prewarm.py (top3 行业成分 + 涨停池)
└── klines_cache                ← s5-prewarm.py (research-mcp 近 35 日 K 线)

S5 select.py / verify.py 纯 DB read:
├── s5_select_runs              ← select 落: 每次跑的 metadata + 漏斗统计
├── s5_candidates               ← select 落: 通过三段的候选 + 交易计划
├── s5_candidate_rejects        ← select 落: 差一点的标的抽样 (校准用)
└── s5_verifications            ← verify 落: T+1 结局, FK → s5_candidates.id

T+1 盘中分时 (ak.stock_intraday_em) 是 verify.py 实时拉, 不走 cache
```

规则表 (`regime_code → playbook`) 住在 [/home/rooot/.openclaw/scripts/market-regime/](/home/rooot/.openclaw/scripts/market-regime/) 的 `regime_rules.py`, S5 通过 `regime_loader.py` import 复用。

---

## 测试

```bash
cd /home/rooot/.openclaw/scripts/s5 && python3 tests/test_signal_detector.py
```

期望 `✅ All 11 tests PASS`。

---

## 相关文档

- [references/strategy.md](references/strategy.md) — 战法完整定义 (为什么是三段确认、阈值的来由)
- [references/signal-tuning.md](references/signal-tuning.md) — 调参指南 (哪些阈值可动、改完怎么验证)
- [references/examples.md](references/examples.md) — 历史真实案例库
