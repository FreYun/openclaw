# finance-data-mcp

A 股金融数据工具包，基于 [Tushare Pro](https://tushare.pro)。

提供两种使用方式：
- **Python 库**：在自己的代码里直接调用，返回 pandas DataFrame
- **MCP 服务器**：让 AI（Claude Desktop、Cursor 等）直接查询金融数据，无需写代码

---

## 目录

1. [前置条件](#前置条件)
2. [安装](#安装)
3. [用法一：Python 库](#用法一python-库)
4. [用法二：MCP 服务器（本机）](#用法二mcp-服务器本机)
5. [用法三：MCP 服务器（跨机器）](#用法三mcp-服务器跨机器)
6. [用法四：自己写 MCP 客户端](#用法四自己写-mcp-客户端)
7. [接口一览](#接口一览)
8. [常见问题](#常见问题)

---

## 前置条件

**Python 版本**：需要 Python 3.10 或更高版本。

```bash
python --version   # 确认 >= 3.10
```

**Tushare Token**：需要在 [tushare.pro](https://tushare.pro) 注册账号并获取 Token。
Token 已内置在包里，直接使用即可。如需换成自己的 Token，见[Token 配置](#token-配置)。

---

## 安装

把 `finance_data_mcp-0.1.0-py3-none-any.whl` 文件复制到目标机器，然后执行：

```bash
pip install finance_data_mcp-0.1.0-py3-none-any.whl
```

**验证安装是否成功：**

```bash
python -c "import finance_data; import finance_data_mcp; print('安装成功')"
```

**验证命令行工具是否可用：**

```bash
finance-data-mcp --help
```

如果提示找不到命令，说明 Python 的 Scripts 目录不在 PATH 里。
- Windows：找到 `C:\PythonXX\Scripts\` 加入 PATH，或直接用 `python -m finance_data_mcp --help`
- Linux/Mac：用 `python -m finance_data_mcp --help`

---

## Token 配置

包内置了默认 Token，**无需任何配置即可直接使用**。

如果你有自己的 Tushare Token，或者默认 Token 积分不够用，可以通过环境变量覆盖：

**Windows（命令提示符）：**
```cmd
set TUSHARE_TOKEN=你的token
```

**Windows（PowerShell）：**
```powershell
$env:TUSHARE_TOKEN = "你的token"
```

**Linux / Mac：**
```bash
export TUSHARE_TOKEN=你的token
```

设置后在同一个终端窗口里启动服务即可生效。

---

## 用法一：Python 库

安装后直接在 Python 代码里 import 使用，所有函数返回 `pandas.DataFrame`。

```python
from finance_data import get_daily_bars, get_stock_list, get_fina_indicator

# 获取全部 A 股列表
stocks = get_stock_list()
print(stocks.head())

# 获取平安银行 2024 年日线行情
bars = get_daily_bars("000001.SZ", "20240101", "20241231")
print(bars.head())

# 获取平安银行财务指标（ROE、EPS 等）
fi = get_fina_indicator("000001.SZ")
print(fi[["end_date", "roe", "eps"]].head())
```

**日期格式说明：**

| 数据类型 | 格式 | 示例 |
|---------|------|------|
| 日线/日度数据 | `YYYYMMDD` | `"20241231"` |
| 月度数据 | `YYYYMM` | `"202412"` |
| 季度数据 | `YYYYQN` | `"2024Q4"` |

**股票/基金/指数代码格式：**

| 类型 | 格式 | 示例 |
|------|------|------|
| 上交所股票 | `xxxxxx.SH` | `"600519.SH"`（茅台） |
| 深交所股票 | `xxxxxx.SZ` | `"000001.SZ"`（平安银行） |
| 上交所指数 | `xxxxxx.SH` | `"000300.SH"`（沪深300） |
| 场内基金ETF | `xxxxxx.SH/SZ` | `"510300.SH"`（沪深300ETF） |

---

## 用法二：MCP 服务器（本机）

这种方式让 Claude Desktop 或 Cursor 等 AI 工具直接调用金融数据，**你不需要写任何代码**，
直接用自然语言问 AI 就行，比如"帮我查一下平安银行最近一个月的日线行情"。

### 第一步：找到配置文件

**Claude Desktop：**
- Windows：`C:\Users\你的用户名\AppData\Roaming\Claude\claude_desktop_config.json`
- Mac：`~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux：`~/.config/Claude/claude_desktop_config.json`

**Cursor：**
- 打开 Cursor → 设置 → MCP → 添加服务器

### 第二步：编辑配置文件

用文本编辑器打开配置文件，写入以下内容（如果文件已有内容，只需把 `mcpServers` 部分合并进去）：

```json
{
  "mcpServers": {
    "finance-data": {
      "command": "finance-data-mcp"
    }
  }
}
```

如果想用自己的 Tushare Token：

```json
{
  "mcpServers": {
    "finance-data": {
      "command": "finance-data-mcp",
      "env": {
        "TUSHARE_TOKEN": "你的token"
      }
    }
  }
}
```

如果 `finance-data-mcp` 命令找不到，改成完整路径：

```json
{
  "mcpServers": {
    "finance-data": {
      "command": "/usr/local/bin/finance-data-mcp"
    }
  }
}
```

### 第三步：重启 AI 客户端

保存配置文件后，完全退出并重新打开 Claude Desktop 或 Cursor。
重启后 AI 就能自动调用这 35 个金融数据工具了。

---

### OpenCode 配置

[OpenCode](https://opencode.ai) 是终端 AI 编程助手（类似 Claude Code），配置文件为 `opencode.json`。

**全局配置**（对所有项目生效）：
- Windows：`%APPDATA%\opencode\opencode.json`
- Linux/Mac：`~/.config/opencode/opencode.json`

**项目配置**：在项目根目录创建 `opencode.json`，只对当前项目生效。

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "finance-data": {
      "type": "local",
      "command": ["finance-data-mcp"],
      "enabled": true
    }
  }
}
```

如果 `finance-data-mcp` 找不到，改成完整路径（注意是数组格式）：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "finance-data": {
      "type": "local",
      "command": ["C:/Python314/Scripts/finance-data-mcp.exe"],
      "enabled": true
    }
  }
}
```

连接远程 SSE 服务（跨机器）：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "finance-data": {
      "type": "remote",
      "url": "http://192.168.1.100:8000/sse",
      "enabled": true
    }
  }
}
```

配置后在终端启动 `opencode`，直接用自然语言问金融数据即可。

---

### OpenClaw 配置

[OpenClaw](https://www.getopenclaw.ai) 是 AI Agent 平台，MCP 配置格式与 Claude Desktop 相同。

配置文件路径：`~/.openclaw/openclaw.json`

```json
{
  "mcpServers": {
    "finance-data": {
      "command": "finance-data-mcp"
    }
  }
}
```

如果想用自己的 Tushare Token：

```json
{
  "mcpServers": {
    "finance-data": {
      "command": "finance-data-mcp",
      "env": { "TUSHARE_TOKEN": "你的token" }
    }
  }
}
```

连接远程 SSE 服务（跨机器）：

```json
{
  "mcpServers": {
    "finance-data": {
      "url": "http://192.168.1.100:8000/sse"
    }
  }
}
```

配置完成后重启 OpenClaw 生效。

---

## 用法三：MCP 服务器（跨机器）

如果你想在服务器上部署，让局域网里的其他机器访问，使用 SSE HTTP 模式。

### 服务端（部署服务的机器）

```bash
# 在服务器上启动，监听所有网卡，端口 8000
finance-data-mcp --transport sse --host 0.0.0.0 --port 8000
```

启动后终端会一直运行，看到类似下面的输出说明启动成功：

```
INFO:     Started server process [...]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**如果需要后台运行（Linux）：**

```bash
nohup finance-data-mcp --transport sse --host 0.0.0.0 --port 8000 > mcp.log 2>&1 &
```

**注意事项：**
- 确保服务器防火墙放行了 8000 端口（或你指定的端口）
- 不建议直接暴露到公网，Tushare Token 有调用配额

### 客户端（访问服务的机器）

**方式 A：让 AI 客户端连 SSE 服务（在 claude_desktop_config.json 里配置）：**

```json
{
  "mcpServers": {
    "finance-data": {
      "url": "http://192.168.1.100:8000/sse"
    }
  }
}
```

把 `192.168.1.100` 换成实际的服务器 IP。

**方式 B：自己写代码访问（见下一节）。**

---

## 用法四：自己写 MCP 客户端

如果你想在自己的程序里调用 MCP 服务，安装客户端依赖后按下面的示例写代码。

```bash
pip install mcp
```

### 连接本机（stdio 模式）

```python
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 连接本机的 MCP 服务（会自动启动 finance-data-mcp 进程）
    server = StdioServerParameters(command="finance-data-mcp")

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 查看所有可用工具
            tools = await session.list_tools()
            print(f"可用工具数：{len(tools.tools)}")

            # 调用工具获取数据
            result = await session.call_tool("get_daily_bars", {
                "ts_code": "000001.SZ",
                "start_date": "20241201",
                "end_date": "20241231",
            })

            # 结果是 JSON 字符串，解析成列表
            data = json.loads(result.content[0].text)
            print(f"获取到 {len(data)} 条 K 线")
            print(data[0])  # 第一条数据

asyncio.run(main())
```

### 连接远程服务器（SSE 模式）

```python
import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    # 替换成实际的服务器地址
    server_url = "http://192.168.1.100:8000/sse"

    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 获取沪深300 ETF 净值
            result = await session.call_tool("get_fund_nav", {
                "ts_code": "510300.SH",
                "start_date": "20241201",
                "end_date": "20241231",
            })
            data = json.loads(result.content[0].text)
            for row in data[:3]:
                print(row)

asyncio.run(main())
```

---

## 接口一览

### 股票行情

| 函数 | 说明 | 积分要求 |
|------|------|---------|
| `get_stock_list(exchange, status)` | A 股上市股票列表 | 基础 |
| `get_daily_bars(ts_code, start_date, end_date)` | 日线 OHLCV 行情（未复权） | 基础 |
| `get_daily_basic(ts_code, start_date, end_date)` | 每日 PE/PB/市值/换手率 | 基础 |
| `get_adj_factor(ts_code, start_date, end_date)` | 复权因子 | 基础 |
| `get_suspend_list(start_date, end_date)` | 停复牌信息 | 基础 |
| `get_money_flow(ts_code, start_date, end_date)` | 个股资金流向 | >= 2000 积分 |
| `get_limit_list(trade_date)` | 涨跌停板统计 | 基础（每天限 1 次） |
| `get_realtime_quotes(codes)` | 实时行情快照（含买五卖五） | 无要求 |

**前/后复权价格计算：**

```python
from finance_data import get_daily_bars, get_adj_factor

bars = get_daily_bars("000001.SZ", "20240101", "20241231")
adj  = get_adj_factor("000001.SZ", "20240101", "20241231")
df   = bars.merge(adj, on=["ts_code", "trade_date"])

latest_factor = df["adj_factor"].iloc[0]
df["close_qfq"] = df["close"] * df["adj_factor"] / latest_factor  # 前复权
df["close_hfq"] = df["close"] * df["adj_factor"]                  # 后复权
```

---

### 财务数据

每次最多返回 60 条，查全量历史需要分批设置 `end_date`。

| 函数 | 说明 |
|------|------|
| `get_income_statement(ts_code, period)` | 利润表（营收、净利润、EPS） |
| `get_balance_sheet(ts_code, period)` | 资产负债表（总资产、总负债、净资产） |
| `get_cash_flow(ts_code, period)` | 现金流量表（经营/投资/筹资现金流） |
| `get_fina_indicator(ts_code)` | 财务指标（ROE/EPS/毛利率/资产负债率等） |
| `get_earnings_forecast(start_date, end_date)` | 业绩预告 |
| `get_express_report(start_date, end_date)` | 业绩快报 |

```python
from finance_data import get_fina_indicator

fi = get_fina_indicator("000001.SZ")
print(fi[["end_date", "roe", "eps", "grossprofit_margin"]].head())
```

---

### 指数 & 行业

| 函数 | 说明 |
|------|------|
| `get_index_list(market)` | 指数列表（`"SSE"` 上交所 / `"SW"` 申万） |
| `get_index_daily(ts_code, start_date, end_date)` | 指数日线行情 |
| `get_index_daily_basic(ts_code, start_date, end_date)` | 指数 PE/PB/股息率 |
| `get_index_members(index_code)` | 指数成分股及权重 |
| `get_industry_classify(src)` | 行业分类（`"SW"` 申万 / `"CI"` 中信） |
| `get_concept_list()` | 概念板块列表 |
| `get_concept_stocks(concept_id)` | 概念板块成分股 |

**常用指数代码：**

| 指数 | 代码 |
|------|------|
| 上证综指 | `000001.SH` |
| 沪深300 | `000300.SH` |
| 中证500 | `000905.SH` |
| 中证1000 | `000852.SH` |
| 创业板指 | `399006.SZ` |
| 科创50 | `000688.SH` |

---

### 场内公募基金（ETF / LOF）

| 函数 | 说明 | 积分要求 |
|------|------|---------|
| `get_fund_list(market, status)` | 基金列表（`market="E"` 为场内） | >= 1500 |
| `get_fund_daily(ts_code, start_date, end_date)` | 日线行情 | 基础 |
| `get_fund_adj_factor(ts_code, start_date, end_date)` | 复权因子 | 基础 |
| `get_fund_nav(ts_code, start_date, end_date)` | 单位净值 & 累计净值 | 基础 |
| `get_fund_div(ts_code)` | 历史分红记录 | 基础 |
| `get_fund_portfolio(ts_code, period)` | 季度十大重仓持股 | >= 1000 |
| `get_fund_share(ts_code, start_date, end_date)` | 每日份额变化 | 基础 |
| `get_fund_manager(ts_code)` | 基金经理任职记录 | 基础 |

**ETF 溢折价计算示例：**

```python
from finance_data import get_fund_daily, get_fund_nav

price = get_fund_daily("510300.SH", start_date="20241201", end_date="20241231")
nav   = get_fund_nav("510300.SH",   start_date="20241201", end_date="20241231")

df = price.merge(nav[["nav_date", "unit_nav"]], left_on="trade_date", right_on="nav_date")
df["premium"] = (df["close"] - df["unit_nav"]) / df["unit_nav"] * 100  # 溢价率 %
print(df[["trade_date", "close", "unit_nav", "premium"]])
```

---

### 宏观经济

| 函数 | 说明 | 日期格式 |
|------|------|---------|
| `get_cpi(start_month, end_month)` | CPI 月度数据 | `YYYYMM` |
| `get_ppi(start_month, end_month)` | PPI 月度数据 | `YYYYMM` |
| `get_gdp(start_q, end_q)` | GDP 季度数据 | `YYYYQN`（如 `"2024Q4"`） |
| `get_money_supply(start_month, end_month)` | M0/M1/M2 货币供应量 | `YYYYMM` |
| `get_shibor(start_date, end_date)` | Shibor 银行间拆放利率 | `YYYYMMDD` |
| `get_shibor_lpr(start_date, end_date)` | LPR 贷款市场报价利率 | `YYYYMMDD` |

---

## 常见问题

**Q：报错 `权限不足` 或 `每小时最多调用 N 次`**

这是 Tushare 的积分限制，不是代码问题。
- `get_money_flow` 需要 >= 2000 积分
- `get_fund_list` 需要 >= 1500 积分
- `get_fund_portfolio` 需要 >= 1000 积分
- 部分接口有每分钟/每小时调用次数上限

**Q：返回空 DataFrame（0 行）**

常见原因：
1. 日期范围内没有数据（如节假日、停牌期）
2. 该基金/股票该时间段无对应数据（如 `fund_portfolio` 部分 ETF 不披露）

**Q：Windows 下中文乱码**

运行测试脚本时加上 UTF-8 参数：

```bash
python -X utf8 test_finance_data.py
```

或在脚本开头已内置了自动处理，直接运行即可：

```bash
python test_finance_data.py
```

**Q：`finance-data-mcp` 命令找不到**

用完整路径替代：

```bash
# 先找到路径
python -c "import sys; print(sys.executable)"
# 然后在同级的 Scripts/ 目录下找 finance-data-mcp.exe（Windows）
# 或 bin/ 目录下（Linux/Mac）
```

**Q：Claude Desktop 配置后没有效果**

1. 确认 JSON 格式正确（可以用 [jsonlint.com](https://jsonlint.com) 验证）
2. 完全退出再重新打开 Claude Desktop（不是最小化，是完全退出）
3. 检查 `command` 路径是否正确

---

## 运行接口测试

```bash
cd d:/code/hq
python test_finance_data.py
```

测试覆盖全部 35 个接口，输出 PASS / WARN / FAIL 三种状态。
`WARN` 表示速率或积分限制，不是代码错误。
