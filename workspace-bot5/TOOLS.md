# TOOLS.md - bot5（宣妈慢慢变富）工具配置

> **首先 `Read ../workspace/TOOLS_COMMON.md` 获取统一工具规范，再看下面的 bot 专属配置。**

---

## Bot 专属配置

- **account_id**: `bot5`
- **小红书 MCP 端口**: 18065（已配置在 mcporter.json，不需要手动指定）

## 浏览器（全局规则）

**所有浏览器操作必须使用 `profile="bot5"`**，无论是发布、研究还是截图，调用 browser 工具时一律带上此参数。

## 封面生图

- **生图指南：** 见 `IMAGE_PROMPTS.md`——包含完整工作流（确认→调用→出图）、卡片版式说明、STYLE/CONTENT 模板、调用示例
- **生图工具：** `image-gen-mcp.generate_image(style, content)`，style 固定不变从模板复制，content 每次按场景填写
- **每次生图前必须先向研究部确认：** 卡片文字、情绪场景、背景色

## 内容规范

- **标题限制：** 图文/视频标题最多 20 字；长文无硬性限制
- **封面与内容形式：** 见本 workspace 的 `CONTENT_STYLE.md`

## 行情数据（Skill 网关）

你的 mcporter.json 已配置 `skill-gateway`（端口 18085），角色 `fund_advisor`，可直接调用以下工具查行情数据：

### 你有权限的工具

| 工具 | 说明 | 常用参数 |
|------|------|---------|
| `commodity_quote` | **黄金/白银等商品行情** | `symbol="AU9999"` 或 `"黄金9999"`，`days=30` |
| `market_snapshot` | A股/港股/美股大盘快照 | 无必填参数 |
| `fund_analysis` | 基金综合分析 | `fund_code="000001"` |
| `fund_screen` | 基金筛选 | 按条件筛 |
| `macro_overview` | 宏观经济数据（GDP/CPI/M2等） | `category="cpi,ppi,m2"` |
| `search_news` | 财经新闻搜索 | `keyword="黄金"` |
| `search_report` | 研报搜索 | `keyword="黄金"` |
| `index_valuation` | 指数估值 | 指数代码 |

### 查黄金行情（最常用）

调用 skill-gateway 的 `commodity_quote` 工具：
- **黄金**：`symbol="AU9999"` 或 `symbol="黄金9999"`
- **白银**：`symbol="AG9999"` 或 `symbol="白银9999"`
- **多个商品**：逗号分隔 `symbol="AU9999,AG9999"`
- **历史天数**：`days=30`（默认 30 天）

### 写稿前查行情的推荐流程

1. `commodity_quote`(symbol="AU9999") — 拿最新金价和近期走势
2. `market_snapshot` — 看大盘环境
3. `search_news`(keyword="黄金") — 搜相关新闻做选题
4. 结合行情数据和新闻写稿

### 需要更多工具？

如需 `stock_research`、`bond_monitor` 等当前角色没有的工具，向技能部发权限申请（见 `skills/skill-gateway/SKILL.md`）。

---

## 本 workspace 路径

- 内容规范：`CONTENT_STYLE.md`
- 人设与研究部规范：`SOUL.md`、`USER.md`
- 工作流程：`AGENTS.md`
