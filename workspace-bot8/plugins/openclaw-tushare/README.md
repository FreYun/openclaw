# openclaw-tushare

A-股金融数据插件，基于 [Tushare Pro](https://tushare.pro) API，为 OpenClaw agent 提供 13 个结构化数据工具。

覆盖行情、估值、财务报表、北向资金、十大股东、业绩预告等核心投研数据。

---

## 前置条件

- OpenClaw 已安装并运行
- Tushare Pro 账号，积分 ≥ 2000（才能访问财务报表类接口）
- 在 [tushare.pro](https://tushare.pro/user/info) 获取 API Token

---

## 安装

### 方式一：从本地目录安装（推荐）

```bash
# 克隆或解压插件目录后执行：
openclaw plugins install /path/to/openclaw-tushare

# 或用 --link 模式（开发用，不复制文件）：
openclaw plugins install -l /path/to/openclaw-tushare
```

### 方式二：从压缩包安装

```bash
openclaw plugins install openclaw-tushare-1.0.0.tgz
```

---

## 配置

安装后，在 `openclaw.json` 的 `plugins.entries` 中填入 Token：

```json
{
  "plugins": {
    "allow": ["openclaw-tushare"],
    "entries": {
      "openclaw-tushare": {
        "enabled": true,
        "config": {
          "token": "你的 Tushare Token"
        }
      }
    }
  }
}
```

也可以通过 CLI 设置：

```bash
openclaw config set plugins.entries.openclaw-tushare.config.token <YOUR_TOKEN>
```

**重启 gateway 生效：**

```bash
openclaw gateway restart
# 或直接重启 openclaw 进程
```

---

## 验证安装

```bash
openclaw plugins list
# 应看到 openclaw-tushare  loaded
```

---

## 可用工具（13 个）

| 工具名 | 说明 | 所需积分 |
|--------|------|---------|
| `tushare_trade_cal` | 交易日历，判断某日是否交易日 | 基础 |
| `tushare_stock_basic` | 股票列表，含行业、上市日期等 | 基础 |
| `tushare_daily` | 日线行情（开高低收、量额、涨跌幅） | 基础 |
| `tushare_daily_basic` | 估值数据（PE/PB/PS/市值/换手率） | 基础 |
| `tushare_index_daily` | 指数日线（上证、深证、沪深300等） | 基础 |
| `tushare_moneyflow_hsgt` | 北向/南向资金日汇总 | 基础 |
| `tushare_hsgt_top10` | 沪深港通十大成交股 | 基础 |
| `tushare_income` | 利润表（营收、净利润、EPS） | 2000+ |
| `tushare_balancesheet` | 资产负债表（总资产、负债、净资产） | 2000+ |
| `tushare_cashflow` | 现金流量表（经营/投资/筹资 CF） | 2000+ |
| `tushare_fina_indicator` | 财务指标（ROE/ROA/毛利率/净利率） | 2000+ |
| `tushare_top10_holders` | 前十大股东（持股比例、持股变动） | 2000+ |
| `tushare_forecast` | 业绩预告（预增/预减/净利润区间） | 2000+ |
| `tushare_dividend` | 分红历史（每股股利、除权日） | 基础 |

> **注意**：利润表、资产负债表、现金流、财务指标、股东数据需要积分 ≥ 2000，否则 API 返回权限错误。

---

## 参数说明

### 股票代码格式

| 市场 | 示例 |
|------|------|
| 上交所 | `600519.SH`（茅台） |
| 深交所 | `000001.SZ`（平安银行） |
| 北交所 | `430047.BJ` |

### 日期格式

所有日期参数统一使用 `YYYYMMDD`，例如 `20241231`。

### 报告期格式

财务报表的 `period` 参数：

| 报告期 | 示例 |
|--------|------|
| 年报 | `20241231` |
| 三季报 | `20240930` |
| 半年报 | `20240630` |
| 一季报 | `20240331` |

### 常用指数代码

| 代码 | 指数 |
|------|------|
| `000001.SH` | 上证综指 |
| `399001.SZ` | 深证成指 |
| `399006.SZ` | 创业板指 |
| `000300.SH` | 沪深 300 |
| `000905.SH` | 中证 500 |
| `000852.SH` | 中证 1000 |
| `HSI.HI` | 恒生指数 |
| `HSCEI.HI` | 恒生国企指数 |

---

## 使用示例

agent 对话中直接提问，插件会自动调用对应工具：

```
查一下茅台最近一周的行情和估值
→ tushare_daily + tushare_daily_basic

茅台 2024 年报 ROE 和毛利率是多少？
→ tushare_fina_indicator(ts_code="600519.SH", period="20241231")

昨天北向资金净流入多少？十大成交股是哪些？
→ tushare_moneyflow_hsgt + tushare_hsgt_top10

平安银行前十大股东有变动吗？
→ tushare_top10_holders(ts_code="000001.SZ")
```

---

## 打包发布

```bash
# 打包为 tgz（用于分发）
cd /path/to/openclaw-tushare
tar -czf openclaw-tushare-1.0.0.tgz \
  --exclude='.git' \
  --exclude='node_modules' \
  --transform 's|^\.|openclaw-tushare|' \
  .
```

---

## 数据来源

所有数据由 [Tushare Pro](https://tushare.pro) 提供。使用前请阅读其[服务条款](https://tushare.pro/about)。本插件仅做接口封装，不存储任何数据。
