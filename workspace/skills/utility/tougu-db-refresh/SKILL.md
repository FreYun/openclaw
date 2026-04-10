---
name: tougu-db-refresh
description: 通过 research-mcp 的投顾查询工具拉取数据，写入 tougu.db 的产品侧标准表。全局每天执行一次，所有 bot 共用。
---

# 投顾数据库刷新 /tougu-db-refresh

**重要**：这是全局数据刷新任务，不绑定任何单个 bot。产品数据对所有 bot 是一样的，全局每天只需执行一次。

这个 skill 的职责是：

1. 调用 research-mcp 的投顾查询工具作为数据源
2. 解析返回的 `columns + data` 结构
3. 将结果写入 `/home/rooot/.openclaw/data/tougu.db`

## 数据源：research-mcp 工具

通过 MCP 调用 research-mcp 上的工具：

| 工具 | 目标表 | 请求方式 | 状态 |
|------|--------|---------|------|
| `get_strategy_info()` | `tougu_info` | 全量单次 | ✅ 可用 |
| `get_strategy_nav()` | `tougu_nav` | 全量单次 | ✅ 可用 |
| `get_strategy_performance(strategy=批次)` | `tougu_performance` | **分批 25 个/次** | ✅ 可用 |
| `get_strategy_portfolio(strategy=批次)` | `tougu_portfolio` | **分批 25 个/次** | ✅ 可用 |
| `get_strategy_equity_analysis(strategy=批次)` | `tougu_equity_analysis` | **分批 25 个/次** | ✅ 可用 |

## 分批请求规则（通用）

**⚠️ performance / portfolio / equity_analysis 绝对不能无参数全量请求，会导致 MCP 服务 502 崩溃。这是已验证的生产事故。**

这三个工具必须分批调用：

```
批次大小: 25 个产品
总批次数: ceil(产品总数 / 25) ≈ 44 批
每批间隔: 1 秒
超时设置: 单批 120 秒
参数格式: tool_name(strategy="ID1,ID2,...,ID25")
```

分批流程：
1. 从 `tougu_info` 读取全部 `strategy_id` 列表
2. 按 50 个一组切分
3. 逐批调用，每批返回后立即写入目标表
4. 每批间隔 2 秒
5. 单批失败记录 ID 列表，全部跑完后重试一次

## 执行流程

按以下顺序执行：

### Step 1: 刷新 tougu_info

```
调用: get_strategy_info()  （无参数，全量）
预期: ~1088 个产品
写入: 按 strategy_id upsert
```

### Step 2: 刷新 tougu_nav

```
调用: get_strategy_nav()  （无参数，全量最新净值）
预期: ~1064 个产品
写入: 按 (strategy_id, nav_date) upsert
```

### Step 3: 分批刷新 tougu_performance

```
调用: get_strategy_performance(strategy="批次ID")  分批 25 个/次
写入: 按 (strategy_id, as_of_date, period) upsert
```

### Step 4: 分批刷新 tougu_portfolio

```
调用: get_strategy_portfolio(strategy="批次ID")  分批 25 个/次
写入: 按 (strategy_id, nav_date) 先删后插（同一事务内完成）
```

### Step 5: 分批刷新 tougu_equity_analysis

```
调用: get_strategy_equity_analysis(strategy="批次ID")  分批 25 个/次
写入: 宽表转长表，按 (strategy_id, nav_date) 先删后插（同一事务内完成）
```

## 写库规则

### 1. tougu_info
`get_strategy_info` 返回的中文列映射：

| 返回列 | 目标字段 |
|--------|---------|
| `策略ID` | `strategy_id` |
| `策略名称` | `strategy_name` |
| `管理人` | `manager` |
| `最大申购限额` | `max_deposit` |
| `最小申购限额` | `min_deposit` |
| `策略介绍` | `introduction` |
| `策略简介` | `resume` |
| `管理费率` | `strategy_rate` |
| `业绩基准` | `benchmark` |
| `目标年化收益率` | `target_annual_yield` |
| `申购状态` | `buy_status` |

写入方式：按 `strategy_id` upsert。

### 2. tougu_nav
`get_strategy_nav` 返回的中文列映射：

| 返回列 | 目标字段 |
|--------|---------|
| `策略ID` | `strategy_id` |
| `策略名称` | `strategy_name` |
| `净值日期` | `nav_date` |
| `净值` | `nav` |

写入方式：按 `(strategy_id, nav_date)` upsert。

### 3. tougu_performance
`get_strategy_performance` 每批返回的中文列映射：

| 返回列 | 目标字段 |
|--------|---------|
| `策略ID` | `strategy_id` |
| `策略名称` | `strategy_name` |
| `截止日期` | `as_of_date` |
| `区间` | `period` |
| `收益率` | `return_pct` |
| `最大回撤` | `max_drawdown_pct` |
| `波动率` | `volatility_pct` |
| `夏普比率` | `sharpe_ratio` |
| `卡玛比率` | `calmar_ratio` |

写入方式：按 `(strategy_id, as_of_date, period)` upsert。

### 4. tougu_portfolio
`get_strategy_portfolio` 每批返回的中文列映射：

| 返回列 | 目标字段 |
|--------|---------|
| `策略ID` | `strategy_id` |
| `策略名称` | `strategy_name` |
| `持仓日期` | `nav_date` |
| `基金代码` | `fund_code` |
| `基金名称` | `fund_name` |
| `基金类型` | `fund_type` |
| `持仓比例` | `weight_pct` |
| `标签日期` | `label_date` |
| `主题1` | `theme_1` |
| `主题1占比` | `theme_1_pct` |
| `主题2` | `theme_2` |
| `主题2占比` | `theme_2_pct` |

写入方式：按 `(strategy_id, nav_date)` 先删后插，同一事务内完成，避免持仓重复累计。

### 5. tougu_equity_analysis
`get_strategy_equity_analysis` 返回宽表，固定前 3 列（`策略ID`、`策略名称`、`持仓日期`），后面每列是动态主题名。

落库时转成长表：

| 目标字段 | 来源 |
|---------|------|
| `strategy_id` | 第 1 列 `策略ID` |
| `strategy_name` | 第 2 列 `策略名称` |
| `nav_date` | 第 3 列 `持仓日期` |
| `sector` | 第 4+ 列的**列名**（动态主题名） |
| `sector_pct_in_equity` | 第 4+ 列的**值** |

写入方式：按 `(strategy_id, nav_date)` 先删后插，同一事务内完成。

## 失败处理

- 某个工具返回 `success=False`，记录错误信息，**继续执行下一个工具**（不要整体中断）
- 分批时单批失败，记录失败批次的 ID 列表，全部批次跑完后重试失败批次一次
- 对 `tougu_portfolio` / `tougu_equity_analysis`，必须在同一事务中完成"删旧 + 插新"

## 验证

刷新后检查：

1. `tougu_info` 行数（预期 ~1088）
2. `tougu_nav` 最新 nav_date 是否为今天或最近交易日
3. `tougu_performance` 最新 as_of_date 是否更新
4. `tougu_portfolio` 行数 > 0
5. `tougu_equity_analysis` 行数 > 0
6. 随机抽样 1 个 `strategy_id`，检查五张表是否能对应上

## 输出要求

执行完后汇报：

- 五个工具各自是否成功
- 五张表各写入多少行
- 分批执行情况（总批次/成功/失败）
- 是否有失败项及原因

## 注意事项

- `tougu_nav` 是整个投资链路最关键的表。没有净值数据，bot 的收益快照会 fallback 到 1.0，收益率永远为 0%
- `tougu_performance` 每天按新 as_of_date 追加，长期会膨胀。建议定期清理只保留最近 7 天的 as_of_date
- `tougu_info` 是覆盖写入，不会膨胀
- **performance / portfolio / equity_analysis 全量无参数请求会打崩 MCP 服务**，这是已验证的生产事故，绝对不能做
