# TOOLS.md - bot_main（管理员）工具配置

> **首先 `Read ../workspace/TOOLS_COMMON.md` 获取统一工具规范，再看下面的 bot 专属配置。**

---

## Bot 专属配置

- **account_id**: `bot_main`（管理员 agent，不直接发小红书）
- **角色**: 系统管理，负责监控各 bot 登录状态、MCP 服务健康、基础设施巡检

## 管理范围

管理以下 bot 的小红书登录状态：

| Bot | 名字 | account_id |
|-----|------|-----------|
| bot1 | 来财妹妹 | bot1 |
| bot5 | 宣妈慢慢变富 | bot5 |
| bot7 | 老K投资笔记 | bot7 |

## 登录状态检查

```bash
# 检查单个 bot 登录状态
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'botN')"
```

## 开发参考

详见 `skills/claude-dev-reference/SKILL.md`（即 CLAUDE.md），包含：
- 小红书网页解析原理
- 有头浏览器调试方法
- Agent Skill 管理手册
- Workspace 文件管理手册
