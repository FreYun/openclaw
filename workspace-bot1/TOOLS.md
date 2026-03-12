# TOOLS.md - bot1（来财妹妹）工具配置

> **首先 `Read ../workspace/TOOLS_COMMON.md` 获取统一工具规范，再看下面的 bot 专属配置。**

---

## Bot 专属配置

- **account_id**: `bot1`
- **小红书 MCP 端口**: 18061（已配置在 mcporter.json，不需要手动指定）

## 联网搜索

**必须使用：智谱（zhipu）MCP 提供的搜索工具**

- 内置 `web_search` 已禁用，调用会失败
- 所有联网搜索统一走 zhipu MCP
