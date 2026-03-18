# Skill 网关

你的 mcporter.json 中已配置 `skill-gateway`，连接到技能部维护的 MCP 聚合网关。

## 你能用什么

网关根据你的角色分配工具，连接后 `tools/list` 只返回你有权限的工具。直接调用即可，无需额外配置。

## 申请新工具

如果你需要的工具不在你的权限范围内，向**技能部**发送以下模板：

```
【权限申请】
申请 bot: （你的 bot ID）
申请工具: tool_name_1, tool_name_2
申请理由: 一句话说明用途
```

技能部配置完成后会回复确认，下一次网关重启时生效。

## 网关工具一览

| 工具 | 说明 |
|------|------|
| market_snapshot | A股/港股/美股大盘快照 |
| fund_analysis | 基金综合分析 |
| fund_screen | 基金筛选 |
| stock_research | 个股研究（基本面/K线/估值/资金） |
| bond_monitor | 债券监测（利率债/信用债/可转债） |
| macro_overview | 宏观经济数据 |
| commodity_quote | 大宗商品行情 |
| search_news | 财经新闻搜索 |
| search_report | 研报搜索 |
| index_valuation | 指数估值 |

> 不是所有工具都对你开放，具体取决于技能部分配的角色。
