---
name: s5-dragon-pullback
description: S5 龙回头战法 — 前期龙头股 (近 30 日 ≥2 连板) 冷却 2-7 天后, T 日大阳反包, T+1 集合竞价进。每晚 21:00 pipeline 自动出信号，你负责按信号执行妙想模拟盘交易。
---

# S5 龙回头战法

## 战法简述

```
龙头 (近 30 日 ≥2 连板) → 冷却 (2-7 天, 跌 ≥5%) → T 日反包 (涨 ≥7%, 收盘 ≥ T-1 高)
```

仅在 **STRONG_RANGE / NEUTRAL_RANGE / WEAK_RANGE** 三档震荡市激活，BEAR / STRONG_BULL 自动跳过不出信号。

完整战法定义见 [references/strategy.md](references/strategy.md)。

---

## 查询信号

每晚 21:00 pipeline 自动跑完选股，结果写入 `market.db`。直接查 DB 获取信号，不读文件。

### 查昨日候选（开盘前查）

```sql
-- 昨日 S5 候选（T 日 = 昨天，T+1 = 今天买入）
SELECT code, name, industry,
       entry_zone_low, entry_zone_high,
       stop_loss_price, target_1_price, target_2_price,
       position_pct
FROM s5_candidates
WHERE date = (SELECT MAX(date) FROM s5_candidates)
```

```bash
sqlite3 /home/rooot/database/market.db "上面的 SQL"
```

无结果 → 当日无信号，不操作。

### 查某只股的交易计划（持仓管理时查）

```sql
SELECT code, entry_zone_low, entry_zone_high,
       stop_loss_price, target_1_price, target_2_price,
       position_pct, date
FROM s5_candidates
WHERE code = '603933'
ORDER BY date DESC LIMIT 1
```

---

## 每日交易执行

> 你会在交易日被 cron 自动唤醒两次（9:27 买入、14:50 卖出），收到 `[S5 买入指令]` 或 `[S5 卖出指令]` 时按下面流程操作。

### 买入（cron 触发：交易日 9:27）

1. 查昨日候选（上面的 SQL），无候选则回复"今日无 S5 信号"并结束
2. 查账户可用资金：

```bash
bash skills/mx-moni/run.sh "我的资金"
```

3. 对每个 candidate 计算并下单：

```
买入金额 = 可用资金 × position_pct
买入股数 = floor(买入金额 / entry_zone_high / 100) × 100
买入价格 = entry_zone_high（限价）
```

```bash
bash skills/mx-moni/run.sh "买入 603933 价格 19.23 数量 200 股"
```

**规则**：
- 多只候选的 position_pct 之和 > 1.0 时，按比例缩放
- 算出不足 100 股的跳过
- 开盘价 > entry_zone_high → 放弃，不追高

### 卖出（cron 触发：交易日 14:50）

1. 查持仓：

```bash
bash skills/mx-moni/run.sh "我的持仓"
```

2. 无 S5 相关持仓则回复"无 S5 持仓"并结束

3. 对每只 S5 持仓股，按优先级判断：

| 优先级 | 条件 | 动作 |
|--------|------|------|
| 1 | 当前价 ≤ stop_loss_price | 市价卖出（止损） |
| 2 | 当日最高 ≥ target_2_price | 市价卖出（止盈2） |
| 3 | 当日最高 ≥ target_1_price | 市价卖出（止盈1） |
| 4 | 收盘涨停（涨 ≥9.5%） | 不卖，主动持有 |
| 5 | 收盘跌停（跌 ≤-9.5%） | 不卖，卖不掉 |
| 6 | 以上都不满足 | 市价卖出（收盘退出） |

```bash
bash skills/mx-moni/run.sh "市价卖出 603933 200 股"
```

### 记录

每次操作后更新日记 `memory/YYYY-MM-DD.md`：

```markdown
## S5 持仓跟踪
| 股票 | 买入价 | 止损 | 止盈1 | 止盈2 | 买入日期 | 状态 |
|------|--------|------|-------|-------|----------|------|
| 603933 | 19.23 | 17.90 | 20.00 | 20.95 | 2026-04-21 | 持有中 |
```

---

## 关键纪律

1. **T+1**：当天买的当天不能卖
2. **不追高**：开盘价超出入场区间就放弃
3. **跌停不挂单**：挂了也成交不了
4. **无信号不操作**：candidates 为空时只管已有持仓
5. **止损无条件执行**：不要心存侥幸

---

## 参考文档

- [references/strategy.md](references/strategy.md) — 战法完整定义（三段确认的逻辑和阈值来由）
- [references/signal-tuning.md](references/signal-tuning.md) — 调参指南
- [references/examples.md](references/examples.md) — 历史案例
- [references/implementation.md](references/implementation.md) — 底层命令行、数据流、DB 结构（维护用）
