# 半导体存储芯片产业链跟踪 skill

跟踪全球半导体存储芯片产业链，覆盖 DRAM → NAND Flash → HBM → NOR Flash 四大品类。重点关注：存储芯片价格周期与供需、HBM/AI 驱动的结构性需求爆发、国产替代进展（长鑫存储/长江存储）、存储模组/接口芯片/封测设备等 A 股投资机会。输出可用于小红书笔记、公众号文章、飞书提醒。

---

## 触发条件

### 定时触发（heartbeat）

| 时间 | 任务 | 说明 |
|------|------|------|
| 每日 9:00 | **早盘信息巡逻** | 搜索隔夜海外存储原厂动态（三星/SK海力士/美光）、DRAM/NAND 现货价格、AI 算力资本支出 |
| 每日 16:00 | **收盘数据更新** | 更新存储板块 A 股涨跌、核心标的异动、DRAM/NAND 现货指数 |
| 每周五 20:00 | **周报数据采集** | 汇总本周 DRAM/NAND 合约价变化、HBM 动态、国产替代进展、研报观点 |
| 每周日 10:00 | **周报生成** | 输出存储芯片产业链周报草稿 |
| 每月初 | **研报巡检** | 通过 research-gateway search_report 搜索最新存储/半导体研报 |

### 被动触发

- 研究部说 "查一下存储"、"DRAM 涨了多少"、"HBM 什么情况"、"长鑫存储"、"兆易创新" 等
- DRAM/NAND 现货价格单周波动 > 5%
- 三大原厂发布涨价函 / 季度财报 / 产能规划
- 长鑫存储 / 长江存储重大进展（技术突破、扩产、IPO）
- 知识星球 / 雪球出现存储板块相关热帖
- NVIDIA / AMD 新一代 AI 芯片发布（拉动 HBM 需求）
- 美国对华半导体出口管制政策变动

---

## 信息源与工具

### 数据源优先级

**存储芯片价格数据优先级**：TrendForce（集邦咨询）> CFM（中国闪存市场）> DRAMeXchange > WSTS > 各原厂财报

- **合约价**：TrendForce 是全球存储合约价的权威源（季度/月度预测）
- **现货价**：CFM（chinaflashmarket.com）、DRAMeXchange 实时报价
- **出货量/市占率**：TrendForce、Omdia、Yole
- **设备/产能**：SEMI、TrendForce、各原厂资本支出指引

### 联网搜索

```bash
# TrendForce 价格预测（首选）
web_search("TrendForce DRAM 合约价 季度")
web_search("TrendForce NAND Flash 合约价 季度")
web_search("TrendForce HBM 价格 出货")

# CFM 现货价格
web_search("chinaflashmarket DRAM 现货价格")
web_search("chinaflashmarket NAND 现货价格")
web_search("中国闪存市场 存储芯片 价格")

# 原厂动态
web_search("三星 DRAM NAND 涨价 产能")
web_search("SK海力士 HBM 存储 产能")
web_search("美光 Micron 财报 存储")

# 国产替代
web_search("长鑫存储 CXMT DDR5 LPDDR5X 进展")
web_search("长江存储 YMTC 3D NAND 扩产")
web_search("兆易创新 NOR Flash 涨价")

# AI 驱动
web_search("AI服务器 存储需求 HBM DRAM")
web_search("云厂商 资本支出 2026 AI基础设施")
web_search("NVIDIA Rubin Feynman HBM4")
```

关键词库（轮换使用）：
- DRAM 类：`DRAM 合约价`、`DDR5 价格`、`DDR4 缺货`、`LPDDR5X`、`服务器DRAM`、`车规DRAM`
- NAND 类：`NAND Flash 合约价`、`企业级SSD`、`3D NAND 层数`、`QLC SSD`、`消费级SSD 价格`
- HBM 类：`HBM4 量产`、`HBM3E 价格`、`高带宽内存`、`HBF 高带宽闪存`、`CoWoS 产能`
- NOR Flash：`NOR Flash 涨价`、`车规NOR Flash`、`兆易创新 NOR`
- 国产替代：`长鑫存储 IPO`、`长江存储 Fab3`、`国产存储 设备`、`存储 自主可控`
- 设备材料：`北方华创 存储`、`中微公司 刻蚀`、`拓荆科技`、`半导体设备 国产化`

### 研报搜索（research-gateway）

通过 research-gateway 的 `search_report` 工具搜索专业研报，关键词：
- `存储芯片`、`DRAM NAND`、`半导体存储`、`存储周期`
- `HBM 高带宽内存`、`HBM4`、`AI存储`
- `长鑫存储`、`长江存储`、`国产替代 存储`
- 具体公司名：`兆易创新`、`澜起科技`、`江波龙`、`佰维存储`、`北京君正`

### 浏览器信息源（用 bot11 profile）

| 平台 | 用法 | 关注内容 |
|------|------|---------|
| **TrendForce** | web_search("site:trendforce.com memory DRAM NAND") | **首选价格源**。DRAM/NAND 合约价预测、HBM 出货、市占率 |
| **CFM 闪存市场** | web_search("site:chinaflashmarket.com 价格") | DRAM/NAND 现货日报、涨价函、行业快讯 |
| **雪球** | `browser navigate "https://xueqiu.com/k?q=存储芯片+DRAM+HBM" --browser-profile bot11` | 存储个股讨论、券商观点、板块异动 |
| **知识星球** | 通过 zsxq-reader skill 读取 | 黑马调研中半导体/存储相关研报纪要 |
| **SEMI** | web_search("SEMI 半导体设备 晶圆 出货") | 全球半导体设备销售额、晶圆出货量 |
| **电子工程专辑** | web_search("site:eet-china.com 存储 DRAM HBM") | 国产存储技术进展、行业深度分析 |

### 数据接口

```python
# 存储板块概念股（akshare）
import akshare as ak

# 存储芯片概念板块
df = ak.stock_board_concept_cons_em(symbol="存储芯片")
df = ak.stock_board_concept_cons_em(symbol="芯片概念")

# 半导体板块行情
df = ak.stock_board_concept_hist_em(symbol="存储芯片", period="日k")

# 个股行情
df = ak.stock_zh_a_hist(symbol="603986", period="daily")  # 兆易创新
df = ak.stock_zh_a_hist(symbol="688008", period="daily")  # 澜起科技
```

---

## Memory 路径

运行时数据存放在 `memory/memory-chip/` 目录，详见「知识库维护」subSkill。

---

## 配套技能

| 技能 | 何时使用 |
|------|---------|
| `research-gateway` (search_report) | 搜索存储/半导体/AI专业研报 |
| `zsxq-reader` | 从知识星球获取半导体/存储相关研报纪要 |
| `xhs-op/内容策划` | 将存储内容纳入小红书选题 |
| `mp-content-writer` | 输出公众号长文（周报/品类深度） |
| `xhs-browser-publish` | 发布小红书笔记 |
