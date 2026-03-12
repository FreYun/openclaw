# Portfolio-MCP

A股模拟炒股组合管理服务，基于 MCP（Model Context Protocol）协议，提供完整的模拟交易、持仓管理和绩效分析功能。

## 功能概览

- 多用户、多账户管理
- 模拟买卖 A 股（按手交易，1 手 = 100 股）
- 真实费用模型（佣金万三 + 印花税万五）
- 持仓跟踪与盈亏计算
- 每日净值快照与收益曲线
- 组合绩效统计（年化收益、夏普比率、最大回撤等）
- 排行榜（多账户竞技）

## 项目结构

```
portfolio-mcp/
├── portfolio_mcp/           # 主程序包
│   ├── __init__.py
│   ├── __main__.py          # 入口
│   ├── server.py            # MCP Server 实现（18 个工具）
│   └── db.py                # SQLite 数据库层
├── data/
│   ├── portfolio.db          # SQLite 数据库
│   └── daily_update.log      # 更新日志
├── daily_update.py           # 每日自动更新脚本
├── demo_5days.py             # 5 天交易演示
├── pyproject.toml
└── venv/                     # Python 虚拟环境
```

## 环境要求

- Python >= 3.10
- 依赖：`mcp[cli] >= 1.0.0`、`tushare >= 1.4.0`
- 内置 tushare 实时行情接口，无需外部 MCP 依赖

## 安装与运行

### 安装

```bash
cd workspace/portfolio-mcp
python -m venv venv
venv/Scripts/activate   # Windows
pip install -e .
```

### 启动服务

```bash
# 方式一：模块启动
python -m portfolio_mcp

# 方式二：安装后直接运行
portfolio-mcp
```

### MCP 配置

**VSCode（.vscode/mcp.json）：**

```json
{
  "portfolio-mcp": {
    "type": "stdio",
    "command": "${workspaceFolder}/workspace/portfolio-mcp/venv/Scripts/python.exe",
    "args": ["-m", "portfolio_mcp"]
  }
}
```

**Gateway（gateway/config.json）：**

```json
{
  "portfolio-mcp": {
    "type": "stdio",
    "isActive": true,
    "command": "C:\\Users\\Administrator\\.openclaw\\workspace\\portfolio-mcp\\venv\\Scripts\\python.exe",
    "args": ["-m", "portfolio_mcp"]
  }
}
```

## 工具列表（22 个）

### 一、账户管理

| 工具 | 说明 | 关键参数 |
|------|------|----------|
| `create_account` | 创建模拟交易账户 | `user_id`, `name`, `initial_capital` |
| `get_account_info` | 查询账户信息（现金余额、初始资金等） | `user_id`, `name` |
| `list_user_accounts` | 列出用户所有账户 | `user_id` |
| `deposit` | 入金 | `user_id`, `amount`, `name` |
| `withdraw` | 出金 | `user_id`, `amount`, `name` |

### 二、交易操作

| 工具 | 说明 | 关键参数 |
|------|------|----------|
| `calc_max_buy` | 计算可买最大手数（**买入前必调**） | `user_id`, `price`, `fee_rate` |
| `buy_stock` | 买入股票（数量须为 100 的整数倍） | `user_id`, `ts_code`, `price`, `quantity`, `stock_name`, `reason`, `trade_date` |
| `sell_stock` | 卖出股票 | `user_id`, `ts_code`, `price`, `quantity`, `stock_name`, `reason`, `trade_date` |

### 三、持仓查询

| 工具 | 说明 | 关键参数 |
|------|------|----------|
| `get_all_positions` | 查询所有持仓及盈亏 | `user_id`, `name` |
| `update_position_prices` | 批量更新持仓现价 | `user_id`, `prices`（JSON） |

### 四、实时行情与盈亏

| 工具 | 说明 | 关键参数 |
|------|------|----------|
| `get_stock_quote` | 查询任意股票实时行情（现价、涨跌幅、开高低、成交量） | `codes`（逗号分隔） |
| `get_index_quote` | 查询指数实时行情（上证综指、深证成指、沪深300 等） | `codes`（逗号分隔） |
| `get_realtime_pnl` | 盘中实时查看账户收益，自动获取实时股价并计算浮动盈亏 | `user_id`, `name` |
| `auto_daily_update` | 一键盘后更新（获取价格 + 更新持仓 + 记录快照） | `snap_date` |

### 五、交易历史

| 工具 | 说明 | 关键参数 |
|------|------|----------|
| `get_trade_history` | 查询交易记录 | `user_id`, `ts_code`, `start_date`, `end_date`, `limit` |

### 六、绩效分析

| 工具 | 说明 | 关键参数 |
|------|------|----------|
| `record_daily_snapshot` | 记录单个账户每日快照 | `user_id`, `snap_date`, `name` |
| `batch_snapshot_all` | 一键为所有账户记录快照 | `snap_date` |
| `get_daily_returns` | 获取每日收益率序列 | `user_id`, `start_date`, `end_date` |
| `get_portfolio_curve` | 获取净值曲线与统计指标 | `user_id`, `start_date`, `end_date` |
| `get_portfolio_summary` | 获取账户综合概览 | `user_id`, `name` |
| `get_leaderboard` | 获取所有账户排行榜 | `snap_date` |

### 绩效统计指标（`get_portfolio_curve` 返回）

- 净值序列（初始资金归一为 1.0）
- 每日收益率（%）
- 累计收益率（%）
- 最大回撤（%）
- 年化收益率（按 252 个交易日）
- 夏普比率（无风险利率 2%）
- 波动率（年化 %）
- 胜率（正收益天数占比）

## 典型使用流程

```
1. 创建账户
   create_account(user_id="trader_01", initial_capital=1000000)

2. 查询股票实时价格
   get_stock_quote(codes="000001.SZ")
   → 获得当前价 15.50

3. 计算可买数量
   calc_max_buy(user_id="trader_01", price=15.50)
   → 返回最大可买手数、预计费用

4. 买入股票
   buy_stock(
     user_id="trader_01",
     ts_code="000001.SZ",
     price=15.50,
     quantity=100,
     stock_name="平安银行",
     reason="看好银行板块"
   )

5. 盘中看收益
   get_realtime_pnl(user_id="trader_01")

6. 每日收盘一键更新
   auto_daily_update()

7. 查看绩效
   get_portfolio_curve(user_id="trader_01")
```

## 交易规则

| 规则 | 说明 |
|------|------|
| 交易单位 | 1 手 = 100 股，买入须为 100 的整数倍 |
| 买入佣金 | 万三（0.03%），最低 5 元 |
| 卖出佣金 | 万三（0.03%），最低 5 元 |
| 印花税 | 万五（0.05%），仅卖出时收取 |
| 资金检查 | 买入前检查现金是否充足 |
| 持仓计算 | 每次买入自动计算加权平均成本 |

## 股票代码格式

使用 Tushare 格式：
- 深圳：`000001.SZ`（平安银行）
- 上海：`600519.SH`（贵州茅台）

## 数据库

SQLite 数据库位于 `data/portfolio.db`，包含 4 张表：

| 表名 | 说明 |
|------|------|
| `accounts` | 账户信息（user_id, name, initial_capital, cash） |
| `positions` | 持仓（ts_code, quantity, avg_cost, current_price） |
| `trades` | 交易记录（方向、数量、价格、费用、原因） |
| `daily_snapshots` | 每日快照（总资产、现金、股票市值、收益率） |

## 辅助脚本

### daily_update.py

每日自动更新脚本，功能：
- 读取所有持仓，通过 Tushare 获取收盘价
- 更新持仓现价
- 为所有账户记录每日快照
- 输出日志到 `data/daily_update.log`

### demo_5days.py

5 天模拟交易演示，展示完整工作流：开户 → 买入 → 调仓 → 止损 → 查看绩效。
