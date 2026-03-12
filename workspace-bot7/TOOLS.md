# TOOLS.md - bot7（老k）工具配置

> **首先 `Read ../workspace/TOOLS_COMMON.md` 获取统一工具规范，再看下面的 bot 专属配置。**

---

## Bot 专属配置

- **account_id**: `bot7`
- **小红书 MCP 端口**: 18067（已配置在 mcporter.json，不需要手动指定）

## 联网搜索

**必须使用：智谱（zhipu）MCP 提供的搜索工具**

- 内置 `web_search` 已禁用，调用会失败
- 所有联网搜索统一走 zhipu MCP

## 网页浏览

### 投研必访站点（每次行业研究必须覆盖至少2个）

**雪球 xueqiu.com** — 投资者讨论、机构观点、实时情绪
- 行业/股票搜索：`https://xueqiu.com/search?q={关键词}`
- 个股主页：`https://xueqiu.com/S/SH{6位代码}` 或 `SZ{6位代码}`

**东方财富 eastmoney.com** — 研报、新闻、股吧
- 行业研报：`https://data.eastmoney.com/report/industry.jshtml`
- 个股研报：`https://data.eastmoney.com/report/stock.jshtml?code={ts_code}`

**同花顺 10jqka.com.cn** — 新闻聚合、行业动态
- 行业新闻：`https://news.10jqka.com.cn/`

### browser 使用原则

- 每次行业研究（sector-pulse）：**必须**访问东方财富研报 + 雪球相关讨论
- 每次个股研究（research-stock）：访问个股雪球主页 + 东方财富个股研报

## 投研技能地图

| 技能 | 触发场景 |
|------|---------|
| `/sector-pulse` | 行业深度研究（旗舰） |
| `/industry-earnings` | 财报季行业横向比较 |
| `/flow-watch` | 北向资金行业轮动 |
| `/market-environment-analysis` | 全球宏观环境 |
| `/research-stock` | 个股快速数据查询 |
| `/technical-analyst` | 技术面分析 |
| `/news-factcheck` | 核查资讯真实性 |
| `/stock-watcher` | 管理自选股列表 |
| `/record` | 保存研究结论到记忆 |
| `/self-review` | 定期复盘 + 自我进化 |

## 投研常用信息源

- 行业研报：东方财富 `data.eastmoney.com/report/`、同花顺研报
- 投资者讨论：雪球 `xueqiu.com`
- 公司公告：巨潮资讯 `cninfo.com.cn`
- 深度报道：36kr、晚点 LatePost、路透中文、财新
