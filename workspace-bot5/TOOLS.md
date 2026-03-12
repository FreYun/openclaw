# TOOLS.md - bot5（宣妈慢慢变富）工具配置

> **首先 `Read ../workspace/TOOLS_COMMON.md` 获取统一工具规范，再看下面的 bot 专属配置。**

---

## Bot 专属配置

- **account_id**: `bot5`
- **小红书 MCP 端口**: 18065（已配置在 mcporter.json，不需要手动指定）

## 浏览器（全局规则）

**所有浏览器操作必须使用 `profile="bot5"`**，无论是发布、研究还是截图，调用 browser 工具时一律带上此参数。

## 内容规范

- **标题限制：** 图文/视频标题最多 20 字；长文无硬性限制
- **封面与内容形式：** 见本 workspace 的 `CONTENT_STYLE.md`

## 本 workspace 路径

- 内容规范：`CONTENT_STYLE.md`
- 人设与研究部规范：`SOUL.md`、`USER.md`
- 工作流程：`AGENTS.md`
