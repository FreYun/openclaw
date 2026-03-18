# TOOLS.md - bot2 工具配置

> **首先 `Read ../workspace/TOOLS_COMMON.md` 获取统一工具规范，再看下面的 bot 专属配置。**

---

## Bot 专属配置

- **account_id**: `bot2`
- **小红书 MCP 端口**: 18062（共享实例，已配置在 mcporter.json）

---

## 工具使用

**完整工具优先级和使用方式见 `memory/research/产业链研究流程.md` 的"工具优先级速查"章节。**

Browser 工具必须传 `profile: "bot2"`，不要省略。

---

## TMT 专业信息源

### 半导体

| 站点 | URL | 关注内容 |
|------|-----|---------|
| 集微网 | jiwei.com | 芯片产业链新闻、国产替代进度、晶圆厂扩产 |
| 芯智讯 | icsmart.cn | 半导体行业深度分析、设备材料动态 |
| 半导体行业观察 | semiinsights.com | 行业趋势、技术路线、制程演进 |
| DIGITIMES | digitimes.com | 亚太半导体供应链数据、产能追踪 |

### AI/算力

| 站点 | URL | 关注内容 |
|------|-----|---------|
| 量子位 | qbitai.com | AI 芯片、大模型、算力基础设施 |
| 机器之心 | jiqizhixin.com | AI 技术趋势、行业应用 |
| The Information | theinformation.com | 硅谷大厂 AI 战略、算力采购 |

### 消费电子 & 通信

| 站点 | URL | 关注内容 |
|------|-----|---------|
| 电子工程专辑 | eet-china.com | 消费电子零部件、新品拆解 |
| C114 通信网 | c114.com.cn | 5G/光通信/运营商资本开支 |
| 36氪 | 36kr.com | TMT 公司动态、产业趋势 |

### 综合（雪球/东方财富优先）

| 站点 | URL | 关注内容 |
|------|-----|---------|
| 雪球 | xueqiu.com | TMT 板块讨论、机构观点、市场情绪 |
| 东方财富 | eastmoney.com | 行业研报、板块资金流向 |
| 同花顺 | 10jqka.com.cn | TMT 板块新闻、概念股梳理 |

---

## 内容制作

- 产业链图/技术路线图 → 大模型生图，prompt 规范见 `CONTENT_STYLE.md`
- 结构化数据（竞争格局/财务对比/国产替代进度） → `text_to_image` 文字卡片
- 发帖 → `skills/submit-to-publisher/SKILL.md`
