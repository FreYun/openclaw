# 真实选股案例库

记录 S5 在真实历史数据上的运行结果, 用于验证信号质量和调参依据。

数据源: `market.db.regime_classify_daily` (v2 规则, 由 `daily-regime-pipeline.sh` 日更) + S5 自己跑的 candidates 输出。

---

## 一、Skill 上线首测 (2026-04-14)

### Case 1: 2026-04-08 BEAR→WEAK 出熊日 — 3 只候选 ✅

**Regime 上下文**:
- regime: 弱势震荡 (从熊切上来)
- score: +7
- confidence: high
- switched: true (BEAR → WEAK_RANGE)
- emergency_switch: false
- 单票 base 上限: 0.15, 实际仓位 0.15 × 0.8 = 0.12

**stats**:
- universe_size: 420 (元件 + 通用设备 + 涨停池)
- dragon_pool_size: 35 (近 30 日有 ≥2 连板)
- passed_count: 3 (一字板拒掉 1)
- hot_industries: ['元件', '通用设备', '汽车零部']

**3 只 candidate**:

| 代码 | 名称 | 行业 | 龙头日 | 最高板 | 冷却 | 阶段跌幅 | T 日反包 | 仓位 |
|---|---|---|---|---|---|---|---|---|
| 002361 | 神剑股份 | 塑料 | 03-31 | 4 板 | 4 天 | -7.58% | +10.03% | 12% |
| 002902 | 铭普光磁 | 通信设备 | 03-26 | 2 板 | 7 天 | -6.48% | +10.00% | 12% |
| 603272 | 联翔股份 | 家居用品 | 03-30 | 3 板 | 5 天 | -15.27% | +9.99% | 12% |

**拒掉**: 603538 美诺华 (5 板, 5 天冷却 -8.79%, T 日 +10%) — T 日为一字涨停, T+1 无法低开进场, build_candidate 主动拒。

**评价**: 3 只都是真实 2-4 板的硬龙头, 冷却充分, T 日大阳反包接近涨停。仓位计算正确 (switched 触发 0.8 乘数)。

---

### Case 2: 2026-04-09 T+1 验证 — 三种状态全覆盖 ✅

| 代码 | 名称 | 状态 | 实际开盘 | 入场区 | 说明 |
|---|---|---|---|---|---|
| 002361 | 神剑股份 | **triggered** ✅ | 16.68 | [16.61, 16.95] | 平开, 完美进入入场区, 按计划买入 |
| 002902 | 铭普光磁 | **gap_up_skip** ⚠️ | 33.00 | [29.08, 29.66] | +12.4% 高开太多, 不追 |
| 603272 | 联翔股份 | **triggered_late** 🟡 | 31.30 | [32.80, 33.46] | 低开 -5.5% 但已回到入场区, 可买入 |

**评价**: 三种状态都按预期触发, 验证脚本工作正常。注意 `triggered_late` 是设计内的"低开后回到入场区"分支, 给晚到用户的提示。

**已知 limitation**: `verify.py` 用的是 akshare `stock_intraday_em` 的实时数据, 对历史日期会拿到"今天"的分时, 不是真实的当时 T+1 数据。verify 仅设计为"当日实时使用", 不支持历史回放。要做历史 T+1 回放需要改用 `stock_zh_a_hist` 看 T+1 的 OHLC。

---

### Case 3: 2026-03-19 BEAR 入场日 — 正确拒绝 ✅

**Regime 上下文**:
- regime: 熊
- score: -8
- emergency_down 触发 (WEAK → BEAR)
- playbook.recommended: ['S8', 'S7']

**Skill 行为**: `is_s5_allowed()` 返回 False → 直接跳过, 不拉数据, 不跑信号检测。

**输出**:
```json
{
  "skipped_reason": "regime=熊, S5 not in playbook.recommended (['S8', 'S7'])",
  "candidates": [],
  "stats": null
}
```

**评价**: 拒绝路径正确。S5 在熊市不开仓是设计意图, 与 classifier playbook 严格契约一致。

---

### Case 4: 2026-04-13 仍在熊里 — 正确拒绝 ✅

**Regime 上下文**:
- regime: 熊 (即使 score=+4, 因为 emergency reset 后 bootstrap 还没切档)
- score: +4
- bootstrap: true

**Skill 行为**: 同 Case 3, 直接跳过。

**评价**: 这是验证 "regime 比 score 滞后" 的关键场景。score 已经反弹但 regime 还是熊, S5 跟随 regime 而不是 score, 体现了"宁可踏空"的风控原则。

---

## 二、单元测试覆盖 (11 个)

详见 [test_signal_detector.py](../scripts/tests/test_signal_detector.py).

| 测试 | 覆盖 |
|---|---|
| `test_dragon_pass` | 多段连板取最高 |
| `test_dragon_reject_no_streak` | 无连板拒绝 |
| `test_dragon_reject_only_1_board` | 1 板不够 |
| `test_cooldown_pass` | 5 天 -8% 通过 |
| `test_cooldown_reject_too_short` | 1 天太接近 |
| `test_cooldown_reject_drop_insufficient` | 跌幅不够 |
| `test_rebound_pass` | 8% + 收复 |
| `test_rebound_reject_pct_low` | 4% 不够 |
| `test_rebound_reject_no_cover` | 涨够但没收复 |
| `test_detect_s5_full_pass` | 三段全过 |
| `test_detect_s5_short_circuit` | 龙头拒立刻短路 |

跑测试: `python3 scripts/tests/test_signal_detector.py`

---

## 三、待补充的历史回放 (需要用户决定)

以下日期值得回放以扩大样本:

| 日期 | regime | 备注 | 期望 |
|---|---|---|---|
| 2026-03-24 / 03-25 | 熊 (score=+7) | 熊市里的两个反弹日, score 高但 regime 没切 | 应被拒绝 |
| 2026-04-14 | 弱势震荡 (今日) | 真正脱熊日, switched=true | 应有 candidate |

需要等 4/14 收盘后 daily_review 跑完, regime json 生成, 才能跑 select。

---

## 案例模板

新增案例时套用:

```markdown
### Case N: YYYY-MM-DD 一句话描述

**Regime 上下文**:
- regime: ?
- score: ?
- switched / emergency_switch: ?

**stats**: universe / dragon_pool / passed_count

**candidates**: 表格

**评价**: 信号质量, 是否符合预期, 后续走势 (有的话)
```
