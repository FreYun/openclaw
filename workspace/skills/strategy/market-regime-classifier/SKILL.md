# 市场 Regime 判断器

读取 `daily_review.py` 的复盘 MD 和 akshare 指数数据，六维打分后映射到 5 档市场 regime，输出战法推荐与仓位上限，供策略型 bot 做决策前的 step 0。

---

## 触发条件

- 交易日收盘后，`daily_review.py` 跑完复盘 MD 之后
- 用户说"现在是什么市场""该用什么战法""今天能不能突破""跑一下 regime"
- 策略型 skill（如 `short-term-sector-momentum`）启动时作为 step 0
- 盘中出现异动（突发大跌/大涨），用户要求立即重算

---

## 用法

```bash
# 跑今日
cd /home/rooot/.openclaw/workspace/skills/strategy/market-regime-classifier
python3 scripts/classify.py

# 跑指定日期
python3 scripts/classify.py --date=2026-04-13

# 指定 review MD 路径
python3 scripts/classify.py --from-review=/path/to/复盘_2026-04-13.md

# 只要 JSON
python3 scripts/classify.py --format=json
```

**输出**（默认写到输入 review MD 的同目录）：

- `regime_YYYY-MM-DD.md` — 人可读的结论 + 六维明细 + 战法推荐详情
- `regime_YYYY-MM-DD.json` — 机器可读接口（下游 strategy skill 读这个）
- `memory/regime-log.md` — 追加一行日志（供 3 日确认和事后回溯）

---

## 输出的 JSON 接口（下游契约）

```json
{
  "date": "2026-04-13",
  "regime": "中性震荡",
  "regime_code": "NEUTRAL_RANGE",
  "score": {"total": 3, "breakdown": { ... }},
  "confidence": "high",
  "missing_dims": [],
  "switch_warning": "...",
  "playbook": {
    "recommended": [{"id": "S5", "name": "龙回头", "priority": 1}],
    "forbidden": ["S1", "S2", "S6"],
    "position_limit": {"total": 0.50, "single": 0.20}
  },
  "last_regime": "中性震荡",
  "switched": false,
  "emergency_switch": false,
  "emergency_reason": []
}
```

下游乘数叠加规则：`confidence=low ×0.5`、`confidence=medium ×0.8`、`switched ×0.8`、`emergency_switch ×0.7`（可多重叠加）。

---

## 六维打分 / Regime 映射 / 战法清单

详见：
- [references/scoring.md](references/scoring.md) — 六维打分规则与阈值
- [references/mapping.md](references/mapping.md) — regime → 战法推荐/禁止/仓位上限映射
- [references/playbooks.md](references/playbooks.md) — 8 个战法（S1–S8）简介
- [references/regime-examples.md](references/regime-examples.md) — 历史案例库

---

## 设计规格

完整设计见 `docs/superpowers/specs/2026-04-13-market-regime-classifier-design.md`。所有规则都是与研究部反复打磨过的，修改前请先确认。
