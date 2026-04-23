# S5 实现细节（维护参考）

## 命令行

```bash
cd /home/rooot/.openclaw/scripts/s5

# T 日收盘后选股
python3 select.py --date=2026-04-16

# T+1 验证（backtest 模式）
python3 verify.py --date=2026-04-17 --mode=backtest

# 批量回测
python3 backfill_all.py --start 20150101 --end 20260420
```

### 输出模式 (`S5_OUTPUT` 环境变量)

```
S5_OUTPUT=both   默认: 文件 + DB 都写
S5_OUTPUT=file   只写 candidates_*.md / .json
S5_OUTPUT=db     只写 market.db 的 s5_* 表
```

---

## 数据流

```
cron 21:00 daily-regime-pipeline.sh
├── [1/5] daily_review.py     → daily / stk_limit / index_daily / regime_raw_daily
├── [2/5] replay.py           → regime_classify_daily (v2)
├── [3/5] s5-prewarm.py       → limit_up_pool / hot_industries_daily / s5_daily_universe / klines_cache
├── [4/5] s5/select.py        → s5_select_runs / s5_candidates / s5_candidate_rejects
└── [5/5] s5/verify.py        → s5_verifications (验证昨日候选)
```

---

## DB 表

| 表 | 写入者 | 说明 |
|---|---|---|
| `s5_select_runs` | select.py | 每次选股的 metadata + 漏斗统计 |
| `s5_candidates` | select.py | 通过三段确认的候选 + 交易计划 |
| `s5_candidate_rejects` | select.py | 差一点的标的抽样（校准用） |
| `s5_verifications` | verify.py | T+1 结局, FK → s5_candidates.id |

---

## 仓位乘数链

```
base = regime.playbook.position_limit.single
× 0.5 (confidence=low)  或  × 0.8 (medium)
× 0.8 (switched)
× 0.7 (emergency_switch)
= final position_pct
```

---

## T+1 验证状态码

| status | 判定 |
|---|---|
| `triggered_at_open` | 开盘价 ∈ entry_zone |
| `triggered_intraday` | 盘中回到 entry_zone |
| `gap_up_skip` | 开盘 > entry_zone_high |
| `gap_down_skip` | 开盘 < entry_zone_low 且继续下跌 |
| `hit_target_1` | 持仓期间触达止盈1 |
| `hit_target_2` | 持仓期间触达止盈2 |
| `stop_hit` | 持仓期间触达止损 |
| `close_exit` | 未触发止盈止损，按收盘价退出 |
| `max_hold_limit_up` | 达到 10 日上限时仍涨停 |

---

## 测试

```bash
cd /home/rooot/.openclaw/scripts/s5 && python3 tests/test_signal_detector.py
```

---

## 历史回测（需手动 prewarm）

pipeline 只 prewarm 当天。回测历史日期需先：

```bash
python3 /home/rooot/.openclaw/scripts/s5-prewarm.py --date=2024-01-15
```

或用 `backfill_all.py` 一次性回填。
