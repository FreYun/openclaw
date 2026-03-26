# 基金与指数数据工具

指数概览、基金净值、持仓组合管理等数据工具集。

---

## 触发条件

- 需要查看大盘指数和市场宽度时
- 需要更新基金持仓或查询净值时
- 写周复盘需要持仓变动数据时

---

## 工具列表

### 1. 指数概览

```bash
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/data/index_overview.py
```

主要指数（上证综指等）当日表现 + 全市场涨跌家数统计（涨/跌/平/涨停/跌停）。

**适用场景：** 快速获取大盘全貌，daily_review.py 已包含此数据，独立使用时用于盘中快查。

### 2. 持仓组合更新

```bash
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/data/portfolio_update.py
```

获取最新基金净值，计算持仓成本和当前市值，生成每日快照和汇总 Markdown。

**适用场景：** 周复盘中的"持仓/组合变动"章节数据来源。

### 3. 基金净值查询

```bash
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/data/query_funds_akshare.py
```

批量查询基金周度净值历史和申购费率。

### 4. 申购费计算

```bash
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/data/recalc_fees.py
```

根据申购金额、确认日净值和费率，计算实际份额和费用明细。
