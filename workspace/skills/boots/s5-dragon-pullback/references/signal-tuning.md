# 信号阈值调参指南

所有阈值在 [scripts/signal_detector.py](../scripts/signal_detector.py) 的 `DEFAULTS` 字典里。改完跑单元测试 + 4/8 集成验证。

---

## 当前默认值

```python
DEFAULTS = {
    "dragon_lookback_days": 30,        # 龙头回查窗口
    "dragon_min_streak": 2,             # 最低连板数
    "cooldown_min_days": 2,             # 冷却最少天数
    "cooldown_max_days": 7,             # 冷却最多天数
    "cooldown_min_drop_pct": 5.0,       # 冷却最小阶段跌幅 (%)
    "rebound_min_pct": 7.0,             # T 日反包最低涨幅 (%)
    "rebound_must_cover_t1_high": True, # T 日收盘必须 ≥ T-1 最高
}
```

---

## 调参方向

### 信号过少 (连续多日 0 candidate)

按收益/风险敏感度从低到高:

1. **行业 top3 → top5**: 改 `select.py.build_universe` 的 `derive_hot_industries(top_n=5)`。最安全, 扩大搜索面而不放松信号。
2. **冷却跌幅 5% → 4%**: 允许更浅的回调进入候选。可能引入横盘后的弱反包。
3. **反包涨幅 7% → 5%**: 允许更弱的反包。会显著增加 candidate 数, 但质量下降明显, 慎用。
4. **冷却天数 2-7 → 2-10**: 拉长冷却容忍区间。可能引入"老题材"。
5. **dragon_min_streak 2 → 1**: 单日涨停就算龙头。最大胆改动, 会引入大量"一日游哥哥"。**不推荐**, 等其他都试过再考虑。

### 信号过多 (每日 5+ candidate, 看不过来)

1. **dragon_min_streak 2 → 3**: 只要 ≥3 板的硬龙头。立刻减半。
2. **冷却跌幅 5% → 8%**: 要求更深的回调, 排除浅调整。
3. **反包涨幅 7% → 8%**: 卡掉接近涨停才算反包的硬条件。
4. **加资金流过滤**: 在 `select.py` 调 `data_fetcher.fetch_klines_batch` 之后, 加一步用 research-mcp `get_stock_fund_flow` 筛主力净流入 > 0 的。代码框架已经预留, 接口直接套。
5. **加北向持股变动过滤**: research-mcp `get_stock_northbound_holding`。

### 信号质量不好 (candidate 多, 实战 T+1 经常失败)

跑 24 天回测, 看哪些日子的 candidate 在 T+1 全军覆没:

```bash
for d in 2026-03-12 2026-03-13 ... 2026-04-14; do
    python3 scripts/select.py --date=$d --regime-json=...
done
```

然后看 verification 状态分布。如果 `gap_up_skip` 比例 > 50%, 说明反包股次日普遍高开过多, 入场区可以放宽到 ±2%。如果 `stop_hit` 比例 > 30%, 说明止损位太紧, 考虑给 1% 缓冲。

---

## 不能动的硬规则

以下规则改了会破坏整个 skill 的设计意图, 不要动:

1. **regime 拒绝路径**: BEAR/STRONG_BULL 直接跳过, 不允许"我就是要在熊市抄底"。这是与 classifier 的契约。
2. **仓位乘数链**: 与 classifier `mapping.md` 一致, 改了会导致下游 portfolio skill 算错总仓。
3. **JSON 输出 schema**: 字段名固定, 改名要同步通知所有下游。

---

## 校准流程

1. 收集至少 10 个不同日期的 candidate + verification 结果
2. 按 regime/confidence 分组统计:
   - candidate 数量分布
   - T+1 触发率 (`triggered + triggered_late` / total)
   - T+1 失败率 (`gap_up_skip + stop_hit` / total)
3. 与用户讨论, **先停下来问要不要改阈值**
4. 改完跑全套单元测试 + 4/8 / 4/14 集成测试

校准时 **不要单方面改阈值**, 任何阈值修改都要事先与用户对齐, 改完后在 [examples.md](examples.md) 记录调参原因和影响。
