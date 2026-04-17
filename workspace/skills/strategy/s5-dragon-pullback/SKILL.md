---
name: s5-dragon-pullback
description: S5 龙回头战法 — market-regime-classifier 的下游执行器。每日 T 日收盘出 T+1 候选清单 + 入场/止损/仓位; T+1 开盘后跑 verify 检查实际开盘是否触发买点。仅在 STRONG/NEUTRAL/WEAK 震荡档位激活, BEAR/STRONG_BULL 自动跳过。
---

# S5 龙回头战法

`market-regime-classifier` 的下游执行器。每日 T 日收盘后跑 `select.py` 产出 T+1 候选清单 + 入场/止损/仓位; T+1 开盘后跑 `verify.py` 检查实际开盘是否触发买点。

---

## 触发条件

- T 日收盘后 (~16:00), `daily-regime-pipeline.sh` cron 已把 T 日 regime 写入 `market.db.regime_classify_daily`
- 上游 regime ∈ {STRONG_RANGE, NEUTRAL_RANGE, WEAK_RANGE} (S5 在 playbook.recommended)
- 用户说 "今天有没有龙回头""跑一下 S5""有什么候选标的"
- T+1 开盘后 5-10 分钟, 用户说 "S5 验证一下""今天能不能买"

---

## 用法

### 选股 (T 日收盘后)

```bash
cd /home/rooot/.openclaw/workspace/skills/strategy/s5-dragon-pullback

# 默认: 从 market.db.regime_classify_daily 读 regime (v2 规则)
python3 scripts/select.py --date=2026-04-08

# override: 手动指定 regime JSON (跑历史某天或 A/B 实验)
python3 scripts/select.py \
  --date=2026-04-08 \
  --regime-json=/home/rooot/.openclaw/workspace-bot11/memory/review-output/regime_2026-04-08.json
```

**输出** (默认写到 `memory/outputs/`, 若传 `--regime-json` 则写到 JSON 同目录):
- `candidates_YYYY-MM-DD.md` — 人可读候选清单
- `candidates_YYYY-MM-DD.json` — 机器接口

### T+1 验证 (开盘后 5-10 分钟)

```bash
python3 scripts/verify.py \
  --date=2026-04-09 \
  --candidates-json=/path/to/candidates_2026-04-08.json \
  --output-dir=/path/to/output
```

**输出**: `verification_YYYY-MM-DD.md` + `.json`

---

## 信号定义 (三段确认)

```
龙头 (近 30 日 ≥2 连板) → 冷却 (2-7 交易日, 跌幅 ≥5%) → 反包 (T 日涨 ≥7% 且收复 T-1 高)
```

完整规则见 [references/strategy.md](references/strategy.md).

---

## 输出 JSON 接口 (下游契约)

```json
{
  "date": "2026-04-08",
  "strategy": "S5",
  "regime_input": {
    "code": "WEAK_RANGE",
    "regime_name": "弱势震荡",
    "score": 7,
    "confidence": "high",
    "switched": true,
    "emergency_switch": false,
    "position_limit_single_base": 0.15
  },
  "candidates": [
    {
      "code": "002361",
      "name": "神剑股份",
      "industry": "塑料",
      "dragon_peak": {"date": "2026-03-31", "close": 16.5, "max_streak": 4},
      "cooldown": {"days": 4, "drop_pct": -7.58, "t1_close": 15.25},
      "rebound": {"t_pct": 10.03, "t_close": 16.78, "t_low": 15.41, "t_high": 16.78, "t1_high": 16.47},
      "entry": {"zone_low": 16.61, "zone_high": 16.95, "rule": "T 日收盘 ±1%"},
      "stop_loss": {"price": 15.41, "rule": "T 日最低"},
      "target_1": {"price": 17.62, "pct": 5.0},
      "target_2": {"price": 18.46, "pct": 10.0},
      "position_pct": 0.12,
      "position_calc": "0.15 (base) × 0.8 (switched) = 0.1200"
    }
  ],
  "skipped_reason": null,
  "stats": {
    "universe_size": 420,
    "dragon_pool_size": 35,
    "passed_count": 3,
    "hot_industries": ["元件", "通用设备", "汽车零部"]
  }
}
```

跳过路径 (regime=BEAR/STRONG_BULL):
```json
{
  "date": "2026-03-19",
  "strategy": "S5",
  "candidates": [],
  "skipped_reason": "regime=熊, S5 not in playbook.recommended (['S8', 'S7'])",
  "stats": null
}
```

---

## 数据源

| 数据 | 来源 | 备注 |
|---|---|---|
| 涨停池 (确定热门行业) | akshare `stock_zt_pool_em` | 2-3 周历史窗口 |
| 行业成分股 | akshare `stock_board_industry_cons_em` | 当日 |
| 个股 K 线 (批量) | research-mcp HTTP `get_stock_daily_quote` | 一次 200 只 35 天 ≈ 3 秒 |
| T+1 盘中分时 | akshare `stock_intraday_em` | 实时 |

详见 [references/strategy.md](references/strategy.md) 的"已知边界"。

---

## 文件清单

- [scripts/select.py](scripts/select.py) — T 日选股入口
- [scripts/regime_loader.py](scripts/regime_loader.py) — 从 `market.db.regime_classify_daily` 读 regime (复用 classifier 的 playbook mapping)
- [scripts/verify.py](scripts/verify.py) — T+1 验证入口 (live + backtest 双模式)
- [scripts/backtest.py](scripts/backtest.py) — 批量回测 (一段日期连跑 select+verify+汇总)
- [scripts/signal_detector.py](scripts/signal_detector.py) — 三段信号判定 (纯函数)
- [scripts/data_fetcher.py](scripts/data_fetcher.py) — akshare + research-mcp HTTP 混合数据层 + market.db cache
- [scripts/candidate_builder.py](scripts/candidate_builder.py) — candidate 组装 + 仓位计算
- [scripts/output_writer.py](scripts/output_writer.py) — MD/JSON 文件输出 (file 模式)
- [scripts/db_writer.py](scripts/db_writer.py) — s5.db 读/写 helper (db 模式)
- [scripts/render.py](scripts/render.py) — 从 s5.db 读 → 渲染 MD (DB-only 模式下重建 MD)
- [scripts/migrate.py](scripts/migrate.py) — 历史 JSON 文件 → DB 一次性迁移
- [scripts/tests/test_signal_detector.py](scripts/tests/test_signal_detector.py) — 11 个单元测试
- [references/strategy.md](references/strategy.md) — 战法完整定义
- [references/signal-tuning.md](references/signal-tuning.md) — 调参指南
- [references/examples.md](references/examples.md) — 真实选股案例库

## 数据存储 (DB 双层架构)

S5 用两个 SQLite 数据库:

| DB | 位置 | 内容 |
|---|---|---|
| `market.db` | `/home/rooot/database/market.db` (仓库外) | **共享层**: regime / 涨停池 / K 线缓存 / 热门行业。所有 strategy skill 都读这里。路径常量见 `strategy/_lib/db.py` |
| `s5.db` | `workspace/skills/strategy/s5-dragon-pullback/.data/s5.db` | **S5 专属**: select_runs / candidates / candidate_rejects / verifications |

### 输出模式 (S5_OUTPUT 环境变量)

```bash
S5_OUTPUT=both   # 默认: 同时写文件 + DB
S5_OUTPUT=file   # 只写文件 (不写 DB)
S5_OUTPUT=db     # 只写 DB (不写文件, 用 render.py 按需生成 MD)
```

classifier 也有同样的环境变量 `CLASSIFIER_OUTPUT=both|file|db`。

### 从 DB 渲染 MD

```bash
python3 scripts/render.py candidates --date=2026-04-08          # 输出到 stdout
python3 scripts/render.py candidates --date=2026-04-08 --output=/tmp/x.md
python3 scripts/render.py verification --date=2026-04-09
python3 scripts/render.py list                                   # 列出 DB 所有日期
```

### 历史文件迁移

一次性把已有 JSON 导入 DB:
```bash
python3 scripts/migrate.py \
    --regime-dir=/home/rooot/.openclaw/workspace-bot11/memory/review-output \
    --s5-dir=/tmp/s5-test \
    [--no-archive]    # 不移文件, 只导入
```

---

## 测试

```bash
python3 scripts/tests/test_signal_detector.py
```

应输出 `✅ All 11 tests PASS`.

---

## 已验证场景

- ✅ 2026-04-08 (BEAR→WEAK 出熊日, score=+7) — 3 只候选
- ✅ 2026-04-09 (T+1 验证): triggered / gap_up_skip / triggered_late 三种状态都覆盖
- ✅ 2026-03-19 (BEAR 入场日) — 正确拒绝
- ✅ 2026-04-13 (仍在熊里) — 正确拒绝

详见 [references/examples.md](references/examples.md).
