# TOOLS.md - 测试君工具配置

> **首先 `Read ../workspace/TOOLS_COMMON.md` 获取统一工具规范。**

---

## Bot 专属配置

- **account_id：** bot10
- **小红书 MCP 端口：** 18070
- **MCP 服务名：** xiaohongshu-mcp

## 调用示例

```bash
# 检查登录状态
npx mcporter call "xiaohongshu-mcp.check_login_status(account_id: 'bot10')"

# 搜索
npx mcporter call "xiaohongshu-mcp.search_feeds(account_id: 'bot10', keyword: '测试关键词')"

# 获取笔记详情
npx mcporter call "xiaohongshu-mcp.get_feed_detail(account_id: 'bot10', feed_id: 'xxx', xsec_token: 'xxx')"

# 获取用户主页
npx mcporter call "xiaohongshu-mcp.get_user_profile(account_id: 'bot10', user_url: 'https://www.xiaohongshu.com/user/profile/xxx')"

# 创作者后台
npx mcporter call "xiaohongshu-mcp.get_creator_home(account_id: 'bot10')"

# 查看通知评论
npx mcporter call "xiaohongshu-mcp.get_notification_comments(account_id: 'bot10')"
```

## 测试发帖（必须仅自己可见）

发帖走 `skills/submit-to-publisher/SKILL.md` 流程，**visibility 必须填 `仅自己可见`**。

## 联网搜索

```bash
npx mcporter call "tavily.search(query: '关键词')"
```

## 合规服务

```bash
npx mcporter call "compliance-mcp.review_content(title: '标题', content: '内容', tags: '标签')"
```
