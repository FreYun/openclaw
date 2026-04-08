# 每日复盘数据采集

一键运行 `daily_review.py`，自动采集当日A股全量复盘数据，输出结构化 Markdown 文件。

---

## 触发条件

- 交易日收盘后需要写日复盘/周复盘时
- 用户说"跑数据""采集复盘数据""准备复盘"等

---

## 用法

```bash
# 采集今日数据
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/review/daily_review.py

# 采集指定日期
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/review/daily_review.py 2026-03-25
```

**输出文件：** `review-output/复盘_YYYY-MM-DD.md`

---

## 数据模块

脚本按顺序执行以下模块，每个模块独立容错（单个失败不影响其他）：

| 顺序 | 模块 | 采集内容 | 数据源 |
|------|------|---------|--------|
| 1 | 市场全景 | 主要指数涨跌、涨跌家数、成交额 | akshare + Tushare |
| 2 | 日内画像 | 分时走势特征、量能分布、关键时点 | Tushare 分钟线 |
| 3 | 情绪温度计 | 涨跌停数、炸板率、情绪评分（依赖模块1的 breadth） | 基于模块1计算 |
| 4 | 板块轮动 | 行业/概念 TOP5 + 后5 及领涨股 | akshare |
| 5 | 连板前瞻 | 涨停数、最高连板、连板股梯队、题材分布 | akshare + Tushare |
| 6 | 资金与流动性 | 北向资金、融资融券、主力资金流向 | Tushare |
| 7 | 股东行为 | 增减持、回购、解禁 | Tushare |
| 8 | 股债收益比 | ERP走势、沪深300 PE、历史分位 | Tushare |

---

## 注意事项

- 脚本会自动检查是否为交易日，非交易日自动跳过
- Tushare 涨停接口每日限调1次，重复跑可能获取不到连板数据
- 日志输出到 `review-output/logs/review_YYYY-MM-DD.log`
- 模块1（市场全景）必须最先运行，因为模块3（情绪）依赖其 breadth 数据
