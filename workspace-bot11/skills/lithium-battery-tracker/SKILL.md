# 锂电池产业链跟踪 skill

跟踪锂电池全产业链核心品种与上市公司，覆盖锂资源→四大材料→电池制造→终端应用。重点关注：碳酸锂价格与供需、四大材料价格与竞争格局、电池龙头出货量、储能/动力需求节奏、固态电池进展。输出可用于小红书笔记、公众号文章、飞书提醒。

---

## 触发条件

### 定时触发（heartbeat）

| 时间 | 任务 | 说明 |
|------|------|------|
| 每日 9:00 | **早盘信息巡逻** | 搜索碳酸锂期货夜盘、锂电板块资金动向、重要数据发布 |
| 每日 16:00 | **收盘数据更新** | 更新碳酸锂/六氟/隔膜等价格、锂电板块涨跌、龙头异动 |
| 每周五 20:00 | **周报数据采集** | 汇总本周各环节价格涨跌、库存变化、排产数据 |
| 每周日 10:00 | **周报生成** | 输出锂电池产业链周报草稿 |
| 每月初 | **研报巡检** | 通过 research-gateway search_report 搜索最新锂电/碳酸锂研报 |

### 被动触发

- 研究部说 "查一下锂电"、"碳酸锂怎么样"、"六氟涨了多少"、"宁德时代" 等
- 碳酸锂期货单日波动 > 3%
- 六氟磷酸锂/VC/FEC 价格异动
- 知识星球 / 雪球出现锂电池板块相关热帖
- 固态电池重大技术进展或政策发布
- 核心公司业绩预告/快报/年报发布

---

## 信息源与工具

### 数据源优先级

**锂电池原材料价格数据**：Mysteel（钢联）> SMM（上海有色网）> 百川盈孚 > 鑫椤资讯 > 高工锂电

- **碳酸锂/氢氧化锂**：Mysteel 已成为行业定价基准（天齐锂业 2026 年起采纳 Mysteel 价格结算）
- **正极/负极/电解液/隔膜**：Mysteel 有完整覆盖，SMM 补充
- **行业出货量/排名**：高工锂电（GGII）、鑫椤资讯、EVTank

### 联网搜索

```bash
# 首选 Mysteel（价格/库存）
web_search("mysteel 碳酸锂 价格")
web_search("mysteel 氢氧化锂 价格")
web_search("mysteel 磷酸铁锂 正极材料 价格")
web_search("mysteel 六氟磷酸锂 电解液 价格")
web_search("mysteel 锂电池 隔膜 价格")
web_search("mysteel 负极材料 石墨 价格")

# SMM 补充
web_search("上海有色金属网 碳酸锂 价格")

# 行业动态
web_search("锂电池 产业链 周报 本周")
web_search("碳酸锂 库存 供需 本周")
web_search("固态电池 进展 最新")
web_search("新能源汽车 产销 月度")
web_search("储能 装机 月度 数据")
```

关键词库（轮换使用）：
- 上游锂资源：`碳酸锂 价格`、`氢氧化锂 价格`、`锂矿 锂辉石`、`盐湖提锂`、`锂矿 出口 禁令`
- 正极材料：`磷酸铁锂 价格`、`三元材料 NCM`、`磷酸锰铁锂 LMFP`、`钴酸锂`
- 负极材料：`人造石墨 负极`、`天然石墨 负极`、`硅基负极 硅碳`、`石墨化 加工费`
- 电解液：`六氟磷酸锂 价格`、`电解液 价格`、`VC 碳酸亚乙烯酯`、`FEC`、`LiFSI`
- 隔膜：`湿法隔膜 价格`、`干法隔膜 价格`、`涂覆隔膜`
- 电池：`动力电池 装机`、`储能电池 出货`、`固态电池`、`宁德时代`、`比亚迪`
- 终端：`新能源汽车 产销`、`储能 装机`、`低空经济 电池`、`AI数据中心 储能`

### 研报搜索（research-gateway）

通过 research-gateway 的 `search_report` 工具搜索专业研报，关键词：
- `锂电池`、`碳酸锂`、`锂电 产业链`、`新能源电池`
- `六氟磷酸锂`、`正极材料`、`隔膜`、`电解液`
- `固态电池`、`储能电池`
- 具体公司名：`宁德时代`、`天齐锂业`、`恩捷股份`、`天赐材料`

### 浏览器信息源（用 bot11 profile）

| 平台 | 用法 | 关注内容 |
|------|------|---------|
| **Mysteel（钢联）** | `browser navigate "https://xny.mysteel.com/" --browser-profile bot11` | **首选价格源**。碳酸锂/氢氧化锂/四大材料现货价格、库存 |
| **SMM（上海有色网）** | `browser navigate "https://hq.smm.cn/h5/Li2CO3" --browser-profile bot11` | 碳酸锂实时报价、均价走势 |
| **雪球** | `browser navigate "https://xueqiu.com/k?q=锂电池+碳酸锂" --browser-profile bot11` | 锂电个股讨论、券商观点、板块异动 |
| **知识星球** | 通过 zsxq-reader skill 读取 | 黑马调研中锂电/新能源相关研报纪要 |
| **高工锂电** | web_search("site:gg-lb.com 锂电池 出货") | 月度出货量数据、行业排名 |
| **广期所** | web_search("广州期货交易所 碳酸锂 期货") | 碳酸锂期货行情、持仓数据 |

### 数据接口

```python
# 碳酸锂期货（akshare）
import akshare as ak

# 广期所碳酸锂期货主力合约
df = ak.futures_main_sina(symbol="lc0")  # 碳酸锂主力

# 锂电池概念板块股票
df = ak.stock_board_concept_cons_em(symbol="锂电池")
df = ak.stock_board_concept_cons_em(symbol="固态电池")
df = ak.stock_board_concept_cons_em(symbol="储能")

# 板块行情
df = ak.stock_board_concept_hist_em(symbol="锂电池", period="日k")
```

---

## Memory 路径

运行时数据存放在 `memory/lithium-battery/` 目录，详见「知识库维护」subSkill。

---

## 配套技能

| 技能 | 何时使用 |
|------|---------|
| `research-gateway` (search_report) | 搜索锂电池/碳酸锂专业研报 |
| `zsxq-reader` | 从知识星球获取锂电相关研报纪要 |
| `xhs-op/内容策划` | 将锂电内容纳入小红书选题 |
| `mp-content-writer` | 输出公众号长文（周报/品种深度） |
| `xhs-browser-publish` | 发布小红书笔记 |
