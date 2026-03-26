# 市场数据工具箱

盘中/盘后按需使用的市场分析工具集，用于补充复盘数据或独立分析。

---

## 触发条件

- 需要查特定板块/个股行情时
- 写文章需要补充细节数据时
- 盘中实时监控异动时

---

## 工具列表

### 1. 板块涨跌排名

```bash
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/market/board_ranking.py
```

行业板块和概念板块的涨跌幅排名（TOP涨 + TOP跌），数据来源 akshare/tushare。

**适用场景：** 日复盘补充板块细节、盘后快速看今天哪些板块领涨领跌。

### 2. 个股行情查询

```bash
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/market/stock_query.py
```

查询预定义关注列表的实时行情（按行业分组：银行、芯片、半导体、油气、航运等），显示日涨跌和3日涨跌。

**适用场景：** 跟踪重点个股表现、写文章时引用具体个股数据。

### 3. 跌停扫描

```bash
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/market/limit_down_scan.py
```

扫描连续跌停股票，统计连续跌停天数和累计跌幅。

**适用场景：** 情绪恶化时扫描风险股、写跌停分析段落。

### 4. V型反转板块识别

```bash
cd /home/rooot/.openclaw/workspace-bot11 && python3 scripts/market/v_shape_scan.py
```

识别日内振幅大但收盘微涨的概念板块（V型反转特征），按振幅和涨幅阈值过滤。

**适用场景：** 发现盘中有资金护盘/抄底的板块，作为主题段素材。
