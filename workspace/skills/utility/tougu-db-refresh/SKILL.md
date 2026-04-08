---
name: tougu-db-refresh
description: 通过 tougu_tools.py 的五个查询函数拉取投顾数据，并写入 tougu.db 的五张标准表。用于定时刷新全局产品数据（所有 bot 共用，全局只需执行一次）。
---

# 投顾数据库刷新 /tougu-db-refresh

**重要**：这是全局数据刷新任务，不绑定任何单个 bot。产品数据对所有 bot 是一样的，全局每天只需执行一次。后续这些函数会注册到 research-mcp，届时直接通过 MCP 调用替代 Python 函数调用。

这个 skill 不修改 `tougu_tools.py` 本身。

它的职责是：

1. 调用 [tougu_tools.py](../../../workspace-bot1/memory/portfolio/code/mcp/tougu_tools.py) 里的五个函数作为数据源
2. 解析函数返回的 `columns + data` 结构
3. 将结果写入 `/home/rooot/.openclaw/data/tougu.db`

目标表（产品侧 5 表，供 tougu-portfolio-mcp 读取）：

- `tougu_info` — 产品基本信息（含 min_deposit / max_deposit / buy_status）
- `tougu_nav` — 每日净值（**关键表：收益计算依赖此数据**）
- `tougu_performance` — 多区间绩效
- `tougu_portfolio` — 持仓基金明细
- `tougu_equity_analysis` — 权益主题分析

## 数据源函数

按以下顺序调用：

1. `tool_get_strategy_info(strategy=None)`
2. `tool_get_strategy_nav(strategy=None, as_of_date=None)`
3. `tool_get_strategy_performance(strategy=None, as_of_date=None)`
4. `tool_get_strategy_portfolio(strategy=None, as_of_date=None)`
5. `tool_get_strategy_equity_analysis(strategy=None, as_of_date=None)`

源文件位置：
- [tougu_tools.py](../../../workspace-bot1/memory/portfolio/code/mcp/tougu_tools.py)

## 写库规则

### 1. tougu_info
把 `tool_get_strategy_info` 返回的中文列映射到：

- `策略ID` -> `strategy_id`
- `策略名称` -> `strategy_name`
- `管理人` -> `manager`
- `最大申购限额` -> `max_deposit`
- `最小申购限额` -> `min_deposit`
- `策略介绍` -> `introduction`
- `策略简介` -> `resume`
- `管理费率` -> `strategy_rate`
- `业绩基准` -> `benchmark`
- `目标年化收益率` -> `target_annual_yield`
- `申购状态` -> `buy_status`

写入方式：按 `strategy_id` upsert。

### 2. tougu_nav
把 `tool_get_strategy_nav` 返回的中文列映射到：

- `策略ID` -> `strategy_id`
- `策略名称` -> `strategy_name`
- `净值日期` -> `nav_date`
- `净值` -> `nav`

写入方式：按 `(strategy_id, nav_date)` upsert。

### 3. tougu_performance
把 `tool_get_strategy_performance` 的每一行写入：

- `策略ID` -> `strategy_id`
- `策略名称` -> `strategy_name`
- `截止日期` -> `as_of_date`
- `区间` -> `period`
- `收益率` -> `return_pct`
- `最大回撤` -> `max_drawdown_pct`
- `波动率` -> `volatility_pct`
- `夏普比率` -> `sharpe_ratio`
- `卡玛比率` -> `calmar_ratio`

写入方式：按 `(strategy_id, as_of_date, period)` upsert。

### 4. tougu_portfolio
把 `tool_get_strategy_portfolio` 的每一行写入：

- `策略ID` -> `strategy_id`
- `策略名称` -> `strategy_name`
- `持仓日期` -> `nav_date`
- `基金代码` -> `fund_code`
- `基金名称` -> `fund_name`
- `基金类型` -> `fund_type`
- `持仓比例` -> `weight_pct`
- `标签日期` -> `label_date`
- `主题1` -> `theme_1`
- `主题1占比` -> `theme_1_pct`
- `主题2` -> `theme_2`
- `主题2占比` -> `theme_2_pct`

写入方式：按 `(strategy_id, nav_date)` 先删后插，避免同一批持仓重复累计。

### 5. tougu_equity_analysis
`tool_get_strategy_equity_analysis` 的返回是宽表：

- 固定前 3 列：`策略ID`、`策略名称`、`持仓日期`
- 后面每一列都是一个动态主题

落库时要转成长表写入：

- `strategy_id`
- `strategy_name`
- `nav_date`
- `sector`
- `sector_pct_in_equity`

写入方式：按 `(strategy_id, nav_date)` 先删后插。

## 执行方式

优先直接运行一个内联 Python 刷新逻辑，示例流程：

1. `import tougu_tools`
2. 调 5 个函数拿结果
3. 校验 `success == True`
4. 用 `sqlite3` 连接 `tougu.db`
5. 按上面的映射规则写表
6. 输出每张表刷新了多少条记录

## 失败处理

- 某个函数返回 `success=False`，停止后续写入并报告失败原因
- 不要写入半截结构化脏数据
- 对 `tougu_portfolio` / `tougu_equity_analysis`，必须在同一事务中完成“删旧 + 插新”

## 验证

刷新后至少检查：

1. `tougu_info` 是否有行数
2. `tougu_nav` 是否有行数
3. `tougu_performance` 是否有行数
4. `tougu_portfolio` 是否有行数
5. `tougu_equity_analysis` 是否有行数
6. 随机抽样 1 个 `strategy_id`，检查五张表是否能对应上

## 输出要求

执行完后只汇报：

- 五个函数是否成功
- 五张表各写入多少行
- 是否有失败项

不要改 `tougu_tools.py`。只把它当作数据源。

## 注意事项

- `tougu_nav` 是整个投资链路最关键的表。没有净值数据，bot 的 `record_daily_snapshot` 会 fallback 到 1.0，收益率永远为 0%。净值灌入后收益计算自动生效。
- `tougu_performance` 每天按新 as_of_date 追加，长期会膨胀（~240 万行/年）。建议定期清理只保留最近 7 天的 as_of_date。
- `tougu_info` 和 `tougu_portfolio` 是覆盖/删后重插，不会膨胀。
